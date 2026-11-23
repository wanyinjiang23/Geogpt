"""Controlled workflow with two explicit, server-side confirmation boundaries."""
import asyncio
from dataclasses import dataclass, field
import json
from pathlib import Path
import time
import uuid
import pandas as pd
from .data import SOURCE
from .parser import parse
from .schema import AnalysisRequest, Strategy
from .tools import RetailAnalysisTool, RetailGISTool


@dataclass
class RetailWorkflow:
    bundle: object
    state: str = "READY"
    request: AnalysisRequest | None = None
    analysis: dict | None = None
    strategy: Strategy | None = None
    candidates: pd.DataFrame = field(default_factory=pd.DataFrame)
    rejected: dict = field(default_factory=dict)
    trace: list = field(default_factory=list)
    error: str = ""
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    strategy_confirmed: bool = False

    def event(self, stage, duration=0, status="success", **detail):
        self.trace.append({"step": len(self.trace)+1, "stage": stage, "duration_ms": round(duration*1000, 3), "status": status, **detail})

    def prepare(self, text, mode="offline"):
        # Invalidate all downstream products even if new parsing fails.
        self.analysis, self.strategy = None, None
        self.candidates, self.rejected = pd.DataFrame(), {}
        self.request, self.error, self.strategy_confirmed = None, "", False
        self.run_id, self.trace = uuid.uuid4().hex, []
        started = time.perf_counter()
        try:
            self.request = parse(text, mode)
            self.state = "AWAITING_METRIC_CONFIRMATION"
            self.event("参数解析", time.perf_counter()-started, mode=mode, parameters=self.request.model_dump())
        except ValueError as exc:
            self.state, self.error = "NEEDS_CLARIFICATION", str(exc)
            self.event("参数解析", time.perf_counter()-started, "failed", error=self.error)
        return self

    def diagnose(self, confirmed=False, request=None):
        if self.state not in ("AWAITING_METRIC_CONFIRMATION", "AWAITING_STRATEGY_CONFIRMATION", "COMPLETED", "EMPTY", "FAILED") or self.request is None:
            raise ValueError("请先解析经营需求")
        if not confirmed:
            raise ValueError("需要用户确认经营指标口径")
        if request is not None:
            self.request = AnalysisRequest.model_validate(request)
        self.analysis, self.strategy = None, None
        self.candidates, self.strategy_confirmed, self.error = pd.DataFrame(), False, ""
        start = time.perf_counter()
        self.event("用户确认指标", parameters=self.request.model_dump())
        result = asyncio.run(RetailAnalysisTool(bundle=self.bundle).execute(**self.request.model_dump()))
        if result.error:
            self.state, self.error = "FAILED", result.error
            self.event("retail_analysis", time.perf_counter()-start, "failed", error=self.error)
        else:
            self.analysis = result.output
            self.state = "AWAITING_STRATEGY_CONFIRMATION"
            self.event("retail_analysis", time.perf_counter()-start, sample=len(self.analysis["ranking"]))
        return self

    def screen(self, strategy, confirmed=False):
        if not self.analysis:
            raise ValueError("请先完成经营分析")
        if not confirmed:
            raise ValueError("需要用户确认拓店策略")
        # Never leave previous confirmed results visible after an invalid resubmission.
        self.candidates, self.strategy_confirmed, self.strategy = pd.DataFrame(), False, None
        self.rejected, self.error = {}, ""
        self.state = "AWAITING_STRATEGY_CONFIRMATION"
        validated = Strategy.model_validate(strategy)
        self.strategy = validated
        self.strategy_confirmed = True
        self.event("用户确认策略", parameters=validated.model_dump())
        start = time.perf_counter()
        result = asyncio.run(RetailGISTool(bundle=self.bundle).execute(**validated.model_dump()))
        if result.error:
            self.state, self.error = "FAILED", result.error
            self.event("retail_gis", time.perf_counter()-start, "failed", error=self.error)
        else:
            self.candidates, self.rejected = result.output["candidates"], result.output["rejected"]
            self.state = "EMPTY" if self.candidates.empty else "COMPLETED"
            self.event("retail_gis", time.perf_counter()-start, candidates=len(self.candidates))
            self.event("结果校验", violations=0)
        return self

    def report(self):
        parts = ["# CoffeeLab 经营分析与拓店初筛报告", f"任务：{self.run_id} · 状态：{self.state}",
            f"数据来源：{SOURCE}。经营与全部GIS图层均为模拟；没有真实公开GIS或用户数据。",
            "## 已验证的计算结果"]
        if self.analysis:
            parts.extend([self.analysis["period"], self.analysis["summary"],
                "```csv\n"+self.analysis["top"][["store_id", "revenue", "profit", "margin"]].to_csv(index=False)+"```"])
        else:
            parts.append("尚无已完成的经营分析。")
        parts.extend(["## 统计关联与模拟假设", "办公商圈利润率增加0.06是生成器人为注入的规则。样本存在店型、店龄等混杂因素；相关不等于因果。",
            "## 用户确认的评价规则", json.dumps(self.strategy.model_dump() if self.strategy else {}, ensure_ascii=False, indent=2),
            "## GIS计算结果", "```csv\n"+self.candidates.to_csv(index=False)+"```",
            "## 待人工核查", "需求POI不等于真实客流；核查租金、产权、许可、步行路网和竞争门店营业状态。直线距离与圆形服务区不能替代路网。评分是规则偏好，不是收益预测。",
            "## 数据局限性", "窗口相对2025-12；无2024年记录，同店同比不可用。增长为等长前期环比，完整双窗口门店才参与。缺失值不填零。",
            "## 执行轨迹", "```json\n"+json.dumps(self.trace, ensure_ascii=False, indent=2)+"\n```"])
        if self.error:
            parts.append("异常："+self.error)
        return "\n\n".join(parts)

    def save(self, root: Path):
        directory = root / self.run_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "report.md").write_text(self.report(), encoding="utf-8")
        (directory / "trace.json").write_text(json.dumps(self.trace, ensure_ascii=False, indent=2), encoding="utf-8")
        self.candidates.to_csv(directory / "candidates.csv", index=False, encoding="utf-8-sig")
        return directory
