from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class AnalysisRequest(Strict):
    months: int = Field(ge=1, le=12)
    metric: Literal["margin", "revenue", "profit", "orders", "growth"]
    mature_only: bool
    top_n: int = Field(default=10, ge=1, le=50)
    city: Literal["上海（模拟区域）"] = "上海（模拟区域）"
    end_month: str = Field(default="2025-12", pattern=r"^2025-(0[1-9]|1[0-2])$")


class Strategy(Strict):
    city: Literal["上海（模拟区域）"] = "上海（模拟区域）"
    region: Literal["全部", "北区", "南区"] = "全部"
    min_store_m: float = Field(default=400, ge=0, le=20000)
    max_transit_m: float = Field(default=2500, gt=0, le=20000)
    max_competitors: int = Field(default=10, ge=0, le=100)
    radius_m: float = Field(default=1000, ge=100, le=5000)
    demand_weight: float = Field(default=50, ge=0, le=100)
    transit_weight: float = Field(default=30, ge=0, le=100)
    competition_weight: float = Field(default=20, ge=0, le=100)
    top_n: int = Field(default=3, ge=1, le=24)

    @model_validator(mode="after")
    def weights(self):
        if abs(self.demand_weight+self.transit_weight+self.competition_weight-100) > 1e-6:
            raise ValueError("权重合计必须为100")
        return self
