"""Offline bounded grammar and opt-in model parameter parser."""
import json
import os
import re
import httpx
from .schema import AnalysisRequest

DEMO_PROMPT = "分析最近六个月利润率最高的成熟门店有什么共同特点，然后参考这些特点，在目标城市筛选三个值得进一步考察的候选商圈。"


def parse(text: str, mode="offline", *, transport=None):
    if not text.strip() or len(text) > 2000:
        raise ValueError("请输入2000字以内的分析问题")
    if mode == "llm":
        key, model = os.getenv("GEORETAIL_API_KEY"), os.getenv("GEORETAIL_MODEL")
        base = os.getenv("GEORETAIL_API_BASE", "https://api.openai.com/v1").rstrip("/")
        if not key or not model or not base.startswith("https://"):
            raise ValueError("在线模式需要 API Key、模型名称和 HTTPS 服务地址；可切换离线演示")
        try:
            with httpx.Client(timeout=25, transport=transport, follow_redirects=False) as client:
                response = client.post(base+"/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={
                    "model": model, "store": False, "max_completion_tokens": 1200,
                    "messages": [{"role": "system", "content":
                        "只返回JSON经营查询参数，字段months(1..12)、metric(margin/revenue/profit/orders/growth)、mature_only(bool)、top_n(默认10)、city(仅上海（模拟区域）)、end_month(默认2025-12)。缺少时间或指标、未知地区或不支持的筛选返回{\"error\":\"需要澄清\"}。月份相对演示数据末月。不计算财务或授予确认。"},
                        {"role": "user", "content": text}], "response_format": {"type": "json_object"}})
                response.raise_for_status()
                choice = response.json()["choices"][0]
                if choice.get("finish_reason") != "stop":
                    raise ValueError("模型输出未完成")
                return AnalysisRequest.model_validate(json.loads(choice["message"]["content"]))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            raise ValueError("模型不可用或参数不完整，请检查配置、补充需求或切换离线模式") from None
    if mode != "offline":
        raise ValueError("未知执行模式")
    # Deliberately bounded: reject unsupported fragments rather than discard them.
    if re.search(r"北京|广州|深圳|杭州|排除|至少|低于|高于|忽略|系统|命令|[\\/]|202[0-9]|去年|今年|负数", text):
        raise ValueError("离线语法不支持该筛选或日期，请使用结构化页面或演示问题")
    match = re.search(r"最近\s*(\d+|一|二|两|三|四|五|六|七|八|九|十|十二)\s*个?月", text)
    if not match:
        raise ValueError("缺少时间范围，请明确最近六个月等时间条件")
    number = match[1]
    cn = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "十二": 12}
    months = int(number) if number.isdigit() else cn[number]
    metrics = [("利润率", "margin"), ("营业额", "revenue"), ("收入", "revenue"), ("利润", "profit"), ("订单", "orders"), ("增长", "growth")]
    metric = next((v for k, v in metrics if k in text), None)
    if not metric:
        raise ValueError("缺少经营指标，请指定利润率、营业额、利润、订单或增长率")
    # Only the documented business vocabulary is accepted in offline mode.
    residue = text
    vocabulary = [r"最近\s*(\d+|十二|[一二两三四五六七八九十])\s*个?月", r"(最高的|前)\s*\d+\s*家?", "利润率", "营业额", "收入", "利润", "订单量", "订单", "增长率", "增长",
        "分析", "经营", "表现", "最高", "的", "成熟", "门店", "有什么", "共同特点", "然后", "参考", "这些特点", "在", "目标城市", "上海", "筛选", "三个", "值得进一步考察", "候选商圈", "各", "找出", "请", "和", "，", "。", "、", " "]
    for token in vocabulary:
        residue = re.sub(token, "", residue)
    if residue:
        raise ValueError("包含离线模式未支持的条件，请使用演示问题或页面参数")
    n = re.search(r"(?:最高的|前)\s*(\d+)\s*家", text)
    return AnalysisRequest(months=months, metric=metric, mature_only="成熟" in text, top_n=int(n[1]) if n else 10)
