"""Validated requests and stable serializable tool results."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LayerID = Literal["hospital", "industrial_risk", "major_road"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Constraint(StrictModel):
    feature_layer: LayerID
    operator: Literal["within", "outside"]
    distance_m: float = Field(gt=0, le=10000)


class Preference(StrictModel):
    feature_layer: LayerID
    metric: Literal["proximity"] = "proximity"
    weight: float = Field(ge=0, le=100)


class SiteSelectionRequest(StrictModel):
    region_id: Literal["demo_region"] = "demo_region"
    target_type: Literal["public_service_site"] = "public_service_site"
    hard_constraints: list[Constraint] = Field(min_length=1, max_length=10)
    soft_preferences: list[Preference] = Field(default_factory=list, max_length=3)
    top_k: int = Field(default=3, ge=1, le=20)
    confirmed: bool = False

    @model_validator(mode="after")
    def consistent(self):
        for layer in ("hospital", "industrial_risk", "major_road"):
            inside = [
                c.distance_m
                for c in self.hard_constraints
                if c.feature_layer == layer and c.operator == "within"
            ]
            outside = [
                c.distance_m
                for c in self.hard_constraints
                if c.feature_layer == layer and c.operator == "outside"
            ]
            if inside and outside and max(outside) > min(inside):
                raise ValueError("CONFLICTING_CONSTRAINTS")
        names = [p.feature_layer for p in self.soft_preferences]
        if len(names) != len(set(names)):
            raise ValueError("DUPLICATE_PREFERENCE")
        if names and sum(p.weight for p in self.soft_preferences) <= 0:
            raise ValueError("ZERO_WEIGHT_SUM")
        return self


class ToolResult(StrictModel):
    status: Literal["success", "empty", "validation_error", "execution_error", "cancelled"]
    tool_name: str
    run_id: str
    artifacts: list[dict[str, str]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: dict[str, str] | None = None
