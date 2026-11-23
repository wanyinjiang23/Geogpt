"""Adapters retain the original BaseTool/ToolResult contract."""
from typing import Any
from pydantic import Field
from app.tool.base import BaseTool, ToolResult
from .schema import AnalysisRequest, Strategy
from .analytics import analyze
from .spatial import select_sites


class RetailAnalysisTool(BaseTool):
    name: str = "retail_analysis"
    description: str = "确定性经营汇总、排名、分组和关联分析"
    parameters: dict = Field(default_factory=AnalysisRequest.model_json_schema)
    bundle: Any = Field(exclude=True)

    async def execute(self, **kwargs):
        try:
            return ToolResult(output=analyze(self.bundle, AnalysisRequest.model_validate(kwargs)))
        except Exception:
            return ToolResult(error="经营分析失败：请检查数据完整性和参数")


class RetailGISTool(BaseTool):
    name: str = "retail_gis"
    description: str = "基于已确认策略进行米制GIS候选初筛"
    parameters: dict = Field(default_factory=Strategy.model_json_schema)
    bundle: Any = Field(exclude=True)

    async def execute(self, **kwargs):
        try:
            frame, rejected = select_sites(self.bundle, Strategy.model_validate(kwargs))
            return ToolResult(output={"candidates": frame, "rejected": rejected})
        except Exception:
            return ToolResult(error="GIS工具失败：检查坐标系、空间数据和策略参数")
