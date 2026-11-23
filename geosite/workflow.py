"""Finite, no-retry workflow with isolated artifacts and sanitized failure traces."""

import time
import uuid
from pathlib import Path

from pydantic import ValidationError

from .artifacts import export, write_json
from .datasets import demo_layers
from .parser import Clarification, parse_request
from .schema import SiteSelectionRequest, ToolResult
from .selection import select, validate_results

STATES = [
    "RECEIVED",
    "PARSED",
    "CONFIRMED",
    "DATA_VALIDATED",
    "PLANNED",
    "EXECUTING",
    "RESULT_VALIDATED",
    "COMPLETED",
]


def run(
    value: str | dict | SiteSelectionRequest,
    output_root: Path = Path("outputs"),
    *,
    confirmed=False,
    layers=None,
    mode="offline",
    model_parser=None,
) -> dict:
    """Run bounded demo; unconfirmed requests cannot execute spatial tools.

    Input text and arbitrary exception messages are never stored in traces.
    Callers control the trusted output root; model/user parameters cannot supply paths.
    """
    run_id = uuid.uuid4().hex
    directory = output_root.resolve() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    trace = []

    def state(name, **detail):
        if name in STATES and trace:
            previous = trace[-1]["state"]
            if previous not in STATES or STATES.index(name) != STATES.index(previous) + 1:
                raise RuntimeError("ILLEGAL_STATE_TRANSITION")
        trace.append({"state": name, "elapsed_ms": round((time.perf_counter() - start) * 1000, 3), **detail})
        write_json(directory / "trace.json", {"run_id": run_id, "events": trace})

    state("RECEIVED", input_kind="text" if isinstance(value, str) else "structured", mode=mode)
    request = None
    try:
        if mode not in ("offline", "llm"):
            raise ValueError("UNKNOWN_MODE")
        if isinstance(value, str) and mode == "llm":
            from .model import parse_llm

            request = (model_parser or parse_llm)(value)
        else:
            request = (
                parse_request(value) if isinstance(value, str) else SiteSelectionRequest.model_validate(value)
            )
        state("PARSED", request=request.model_dump())
        if not (confirmed or request.confirmed):
            state("NEEDS_CLARIFICATION", reason="CONFIRM_PARAMETERS")
            return {
                "run_id": run_id,
                "state": "NEEDS_CLARIFICATION",
                "request": request.model_dump(),
                "message": "请确认距离、单位、图层和权重后执行",
                "trace": trace,
            }
        state("CONFIRMED", preconfirmed=confirmed)
        layers = demo_layers() if layers is None else layers
        required = (
            {request.region_id}
            | {c.feature_layer for c in request.hard_constraints}
            | {p.feature_layer for p in request.soft_preferences}
        )
        if not required.issubset(layers):
            raise ValueError("MISSING_LAYER")
        layers = {k: v.aligned() for k, v in layers.items()}
        state("DATA_VALIDATED", feature_counts={k: len(v.geometries) for k, v in layers.items()})
        state("PLANNED", tools=["site_selection"], max_tool_calls=1)
        state("EXECUTING", tool="site_selection", parameters=request.model_dump())
        rows, feasible, excluded, metadata = select(request, layers)
        validate_results(rows, request, layers)
        names = export(directory, rows, feasible, excluded, layers, request, metadata)
        # Existence and JSON readability are required before accepting an output.
        import json

        for name in names:
            if not (directory / name).is_file() or not (directory / name).stat().st_size:
                raise ValueError("ARTIFACT_VALIDATION_FAILED")
        exported = json.loads((directory / "candidates.json").read_text(encoding="utf-8"))
        validate_results(exported, request, layers)
        if exported != rows:
            raise ValueError("ARTIFACT_VALIDATION_FAILED")
        state("RESULT_VALIDATED", checked_candidates=len(rows), constraint_violations=0)
        result = ToolResult(
            status="success" if rows else "empty",
            tool_name="site_selection",
            run_id=run_id,
            artifacts=[
                {"artifact_id": f"{run_id}/{n}", "relative_path": f"{run_id}/{n}", "type": n.split(".")[-1]}
                for n in names
            ],
            metrics={"output_feature_count": len(rows), "top_k_count": min(len(rows), request.top_k)},
            metadata=metadata,
            warnings=["SYNTHETIC_DATA", "250M_GRID_SAMPLING"],
        )
        write_json(directory / "result.json", result.model_dump())
        state("COMPLETED", status=result.status, artifacts=names)
        return {
            "run_id": run_id,
            "state": "COMPLETED",
            "request": request.model_dump(),
            "result": result.model_dump(),
            "top_k": rows[: request.top_k],
            "trace": trace,
        }
    except (Clarification, ValidationError) as exc:
        code = str(exc).split(":")[0] if isinstance(exc, Clarification) else "SCHEMA_VALIDATION_ERROR"
        state("NEEDS_CLARIFICATION", error_code=code)
        messages = {
            "AMBIGUOUS_DISTANCE": "请用米或公里提供明确距离，并说明不超过或至少。",
            "MISSING_CONSTRAINT": "缺少可计算条件，例如：距医院不超过500米。",
            "UNSUPPORTED_CLAUSE": "包含未支持的地名、图层或条件，请只使用演示区域和已列出的图层。",
            "UNSUPPORTED_INPUT": "只接受选址需求，请移除命令、文件路径或修改系统规则的指令。",
            "SCHEMA_VALIDATION_ERROR": "参数不合法或约束冲突，请检查距离范围、权重、Top-K和图层。",
            "MODEL_CONFIG_REQUIRED": "请配置模型名称和API密钥；离线模式无需配置。",
            "MODEL_TIMEOUT": "模型服务超时；请重试或使用离线模式。",
        }
        return {
            "run_id": run_id,
            "state": "NEEDS_CLARIFICATION",
            "message": messages.get(code, "无法可靠解析，请检查参数后重试。"),
            "error_code": code,
            "request": request.model_dump() if request else None,
            "trace": trace,
        }
    except Exception as exc:
        # Exception type is safe; details/absolute paths/provider responses are not.
        code = str(exc).split(":")[0]
        if not code.replace("_", "").isalnum() or len(code) > 60:
            code = "EXECUTION_FAILED"
        result = ToolResult(
            status="validation_error" if isinstance(exc, ValueError) else "execution_error",
            tool_name="site_selection",
            run_id=run_id,
            error={"code": code, "type": type(exc).__name__},
        )
        write_json(directory / "result.json", result.model_dump())
        state("FAILED", error=result.error)
        return {"run_id": run_id, "state": "FAILED", "result": result.model_dump(), "trace": trace}
