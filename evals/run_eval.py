"""Run authored acceptance cases; calculate metrics from assertions and traces."""

import json
import platform
import re
import statistics
import time
from importlib.metadata import version
from pathlib import Path

from shapely.geometry import Point, Polygon

from geosite.artifacts import write_json
from geosite.datasets import demo_layers
from geosite.gis import ANALYSIS_CRS, Layer, buffer
from geosite.schema import SiteSelectionRequest
from geosite.selection import validate_results
from geosite.workflow import run

ROOT = Path(__file__).resolve().parents[1]


def weak_baseline(text):
    """Authored weak baseline: first Arabic number, assume meters and within hospital.

    This is NOT the encrypted original free-text parser or original ReAct agent.
    """
    match = re.search(r"\d+(?:\.\d+)?", text)
    return {
        "hard_constraints": [
            {
                "feature_layer": "hospital",
                "operator": "within",
                "distance_m": float(match.group()) if match else None,
            }
        ],
        "top_k": 3,
    }


def evaluate():
    out = ROOT / "evals" / "results"
    out.mkdir(parents=True, exist_ok=True)
    cases = [
        json.loads(line) for line in (ROOT / "evals/cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    records = []
    correct = fields = baseline_correct = baseline_fields = violations = recommended = 0
    empty_correct = empty_total = valid_calls = all_calls = 0
    for case in cases:
        layers = demo_layers()
        fault = case.get("fault")
        if fault == "missing_crs":
            layers["hospital"].crs = None
        elif fault == "invalid_geometry":
            layers["hospital"] = Layer([Polygon([(0, 0), (1, 1), (0, 1), (1, 0)])], ANALYSIS_CRS)
        elif fault == "empty_layer":
            layers["hospital"].geometries = []
        elif fault == "missing_layer":
            layers.pop("hospital")
        start = time.perf_counter()
        r = run(case["input"], out / "runs", confirmed=True, layers=layers)
        elapsed = time.perf_counter() - start
        checks = {"state": r["state"] == case["expected_state"]}
        if "expected_status" in case:
            checks["status"] = r.get("result", {}).get("status") == case["expected_status"]
        expected = case.get("expected_fields", {})
        parsed = r.get("request") or {}
        for key, value in expected.items():
            equal = parsed.get(key) == value
            checks[key] = equal
            correct += int(equal)
            fields += 1
            if isinstance(case["input"], str):
                baseline_fields += 1
                baseline_correct += int(weak_baseline(case["input"]).get(key) == value)
        if r["state"] == "COMPLETED":
            request = SiteSelectionRequest.model_validate(r["request"])
            rows = json.loads((out / "runs" / r["run_id"] / "candidates.json").read_text(encoding="utf-8"))
            try:
                validate_results(rows, request, layers)
                checks["independent_validation"] = True
            except ValueError:
                checks["independent_validation"] = False
            for row in r["top_k"]:
                recommended += 1
                p = Point(row["x"], row["y"])
                for c in request.hard_constraints:
                    d = min(p.distance(g) for g in layers[c.feature_layer].aligned().geometries)
                    if (c.operator == "within" and d > c.distance_m) or (
                        c.operator == "outside" and d < c.distance_m
                    ):
                        violations += 1
                        break
            checks["artifacts_readable"] = all(
                (out / "runs" / a["relative_path"]).is_file() for a in r["result"]["artifacts"]
            )
        if case.get("expected_status") == "empty":
            empty_total += 1
            empty_correct += int(r.get("result", {}).get("status") == "empty")
        calls = [e for e in r["trace"] if e["state"] == "EXECUTING"]
        all_calls += len(calls)
        valid_calls += sum(
            e["tool"] == "site_selection" and case["expected_state"] == "COMPLETED" for e in calls
        )
        records.append(
            {
                "id": case["id"],
                "run_id": r["run_id"],
                "passed": all(checks.values()),
                "checks": checks,
                "state": r["state"],
                "elapsed_s": elapsed,
            }
        )
    import math

    area_error = abs(buffer(Layer([Point(500000, 3400000)], ANALYSIS_CRS), 500).area - math.pi * 500**2)
    summary = {
        "cases": len(records),
        "passed": sum(r["passed"] for r in records),
        "failed": [r["id"] for r in records if not r["passed"]],
        "field_accuracy": {"correct": correct, "total": fields, "rate": correct / fields if fields else None},
        "weak_baseline_field_accuracy": {
            "correct": baseline_correct,
            "total": baseline_fields,
            "rate": baseline_correct / baseline_fields if baseline_fields else None,
        },
        "task_success_rate": sum(r["passed"] for r in records) / len(records),
        "tool_validity": {
            "valid": valid_calls,
            "total": all_calls,
            "rate": valid_calls / all_calls if all_calls else None,
        },
        "constraint_violation": {
            "violations": violations,
            "recommended": recommended,
            "rate": violations / recommended if recommended else None,
        },
        "empty_recognition": {"correct": empty_correct, "total": empty_total},
        "buffer_500m_area_error_m2": area_error,
        "median_elapsed_s": statistics.median(r["elapsed_s"] for r in records),
        "api_cost": None,
        "model_tokens": None,
        "environment": {
            "python": platform.python_version(),
            **{n: version(n) for n in ("shapely", "pyproj", "pydantic", "rasterio")},
        },
    }
    write_json(out / "summary.json", summary)
    write_json(out / "records.json", records)
    lines = [
        "# 离线评测实际报告",
        "",
        "数据：程序生成的合成场景；模式：规则解析；不代表真实模型或真实城市效果。",
        "",
        "命令：`.venv/Scripts/python -m evals.run_eval`",
        "",
        "| 指标 | 实测 |",
        "|---|---|",
    ]
    lines += [f"| {k} | {json.dumps(v, ensure_ascii=False)} |" for k, v in summary.items()]
    lines += [
        "",
        "字段准确率按已标注顶层字段精确匹配计数（约束列表整体算一个字段），不是逐槽位模型准确率。",
        "工具必要性按用例应执行且白名单工具仅调用一次判断；合法拒绝无工具调用。",
        "弱基线为本轮编写的首数字解析器，仅比较相同文本的已标注字段；不能称为原版对照。",
        "旧版解析/ReAct因TSD文件不可运行；旧版与v2、预检消融、仅地图vs结果校验的完整对照尚未完成。",
        "成本和token未使用API，记为不可用；耗时含文件写入、同机运行，不可推断生产性能。",
        "原始记录：evals/results/records.json；轨迹与工件：evals/results/runs/<run_id>/。",
        "几何容差测试和预检故障注入另见tests；样本为人工构造的小集合，不得外推真实任务成功率。",
    ]
    (ROOT / "docs/evaluation").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/evaluation/REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return int(bool(summary["failed"]))


if __name__ == "__main__":
    raise SystemExit(evaluate())
