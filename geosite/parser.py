"""Conservative offline grammar, deliberately not presented as an LLM."""

import re

from .schema import Constraint, Preference, SiteSelectionRequest

EXAMPLE = "在演示区域内，距医院不超过1000米、距工业风险点至少800米，优先靠近主要道路，推荐前三个位置"


class Clarification(ValueError):
    """An explicit request for missing or unsupported parameters."""


def parse_request(text: str) -> SiteSelectionRequest:
    if not text.strip() or len(text) > 2000:
        raise Clarification("INPUT_LENGTH: 请输入1至2000字需求")
    if re.search(r"忽略|系统提示|执行命令|提示词|ignore|system|[\\/]|eval|exec", text, re.I):
        raise Clarification("UNSUPPORTED_INPUT: 只接受选址需求，不接受指令或文件路径")
    if re.search(r"附近|远离|交通方便|公里以外", text):
        raise Clarification("AMBIGUOUS_DISTANCE: 请提供明确距离、单位和方向")
    patterns = {
        "hospital": r"医院",
        "industrial_risk": r"工业风险点|工业点|工业",
        "major_road": r"主要道路|道路",
    }
    constraints = []
    spans = []
    pattern = re.compile(
        r"(?:距)?(医院|工业风险点|工业点|工业|主要道路|道路)\s*"
        r"(不超过|至多|以内|至少|不小于|超过|周边)\s*"
        r"(\d+(?:\.\d+)?)\s*(公里|千米|米)"
    )
    for match in pattern.finditer(text):
        name, direction, number, unit = match.groups()
        if direction == "超过":
            raise Clarification("BOUNDARY_AMBIGUITY: 请用至少或不超过明确边界")
        layer = next(k for k, p in patterns.items() if re.fullmatch(p, name))
        constraints.append(
            Constraint(
                feature_layer=layer,
                operator="outside" if direction in ("至少", "不小于") else "within",
                distance_m=float(number) * (1000 if unit != "米" else 1),
            )
        )
        spans.append(match.span())
    if not constraints:
        raise Clarification("MISSING_CONSTRAINT: 示例：距医院不超过500米")
    preferences = []
    residual = text
    for start, end in reversed(spans):
        residual = residual[:start] + residual[end:]
    for layer, name in patterns.items():
        pref = re.compile(r"(?:优先)?靠近(?:" + name + r")")
        if pref.search(residual):
            preferences.append(Preference(feature_layer=layer, weight=1))
            residual = pref.sub("", residual)
    top = re.search(r"(?:前|top\s*)(\d+|一|二|三|四|五)", residual, re.I)
    top_k = 3
    if top:
        value = top.group(1)
        top_k = int(value) if value.isdigit() else {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}[value]
        residual = residual[: top.start()] + residual[top.end() :]
    # Reject unconsumed business entities/conditions rather than silently dropping them.
    residual = re.sub(
        r"在|演示区域|指定研究区域|研究区域|指定区域|区域|内|且|并且|和|与|请|推荐|查找|寻找|适合|建设|服务站|候选|位置|个|输出|POI|范围|的|满足|选址|进行|[，。、；：\s]",
        "",
        residual,
    )
    if residual:
        raise Clarification("UNSUPPORTED_CLAUSE: 包含未支持的地名、图层或条件，请编辑结构化参数")
    return SiteSelectionRequest(hard_constraints=constraints, soft_preferences=preferences, top_k=top_k)
