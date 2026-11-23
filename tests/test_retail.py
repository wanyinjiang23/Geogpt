import asyncio
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError
from shapely.geometry import Point
from geosite.gis import Layer, buffer
from georetail.data import generate
from georetail.schema import AnalysisRequest, Strategy
from georetail.analytics import analyze, validate_data
from georetail.parser import parse, DEMO_PROMPT
from georetail.spatial import select_sites
from georetail.tools import RetailAnalysisTool
from georetail.workflow import RetailWorkflow


@pytest.fixture
def bundle():
    return generate()


def test_reproducibility_and_finance(bundle):
    again = generate()
    pd.testing.assert_frame_equal(bundle.monthly, again.monthly)
    assert len(bundle.stores) == 50
    assert bundle.monthly.month.nunique() == 12
    validate_data(bundle)
    np.testing.assert_allclose(bundle.monthly.profit, bundle.monthly.revenue-bundle.monthly.cost, atol=.001)


def test_metrics_ranking_maturity(bundle):
    req = parse(DEMO_PROMPT)
    a = analyze(bundle, req)
    assert a["top"].margin.is_monotonic_decreasing
    assert (a["ranking"].age_at_start >= 12).all()
    s = a["top"].iloc[0]
    m = bundle.monthly[(bundle.monthly.store_id == s.store_id) & (bundle.monthly.month >= "2025-07")]
    assert s.margin == pytest.approx(m.profit.sum()/m.revenue.sum())
    assert s.ticket == pytest.approx(m.revenue.sum()/m.orders.sum())
    prev = bundle.monthly[(bundle.monthly.store_id == s.store_id) & (bundle.monthly.month <= "2025-06")]
    assert s.growth == pytest.approx(m.revenue.sum()/prev.revenue.sum()-1)
    assert a["groups"]["sample"].sum() == len(a["ranking"])
    assert a["comparison"].iloc[0]["优秀样本均值"] == pytest.approx(a["top"].competitors.mean())
    assert a["correlation"].loc["margin", "competitors"] == pytest.approx(a["ranking"].margin.corr(a["ranking"].competitors), abs=.0001)


@pytest.mark.parametrize("prompt", ["分析利润率", "分析最近六个月", "分析最近六个月北京利润率最高的门店", "分析最近六个月利润率最高的门店排除社区店", "分析最近六个月利润率最低的门店"])
def test_missing_or_unsupported(prompt):
    with pytest.raises(ValueError):
        parse(prompt)


def test_schema_and_parser():
    assert parse("分析最近 6 个月经营利润率最高的 10 家成熟门店。").top_n == 10
    with pytest.raises(ValidationError):
        Strategy(demand_weight=0)
    with pytest.raises(ValidationError):
        Strategy(min_store_m=-1)
    with pytest.raises(ValidationError):
        Strategy(radius_m=float("nan"))
    with pytest.raises(ValidationError):
        AnalysisRequest(months=13, metric="margin", mature_only=True)


def test_spatial_constraints_and_score(bundle):
    s = Strategy()
    rows, rejected = select_sites(bundle, s)
    assert len(rows) == 3
    assert rows.score.is_monotonic_decreasing
    for _, r in rows.iterrows():
        point = Point(r.x, r.y)
        nearest = min(point.distance(Point(x, y)) for x, y in zip(bundle.stores.x, bundle.stores.y))
        assert r.nearest_store_m == pytest.approx(nearest)
        assert nearest >= s.min_store_m
        assert r.transit_m <= s.max_transit_m
        assert r.competitors <= s.max_competitors
        assert 0 <= r.overlap_ratio <= 1.00001
        assert r.score == pytest.approx(.5*r.demand_score+.3*r.transit_score+.2*r.competition_score)
    changed, _ = select_sites(bundle, Strategy(demand_weight=0, transit_weight=100, competition_weight=0))
    assert not changed.score.equals(rows.score)
    empty, _ = select_sites(bundle, Strategy(min_store_m=20000))
    assert empty.empty
    northern, _ = select_sites(bundle, Strategy(region="北区"))
    assert (northern.region == "北区").all()


def test_metric_crs_reuse(bundle):
    ring = buffer(Layer([Point(350000, 3455000)], bundle.crs), 1000, target=bundle.crs)
    assert ring.area == pytest.approx(np.pi*1000**2, rel=.001)
    bundle.crs = "EPSG:4326"
    with pytest.raises(ValueError, match="METRIC"):
        select_sites(bundle, Strategy())


def test_failure_empty_missing(bundle):
    bundle.monthly.loc[0, "revenue"] = np.nan
    result = asyncio.run(RetailAnalysisTool(bundle=bundle).execute(**parse(DEMO_PROMPT).model_dump()))
    assert result.error and result.output is None
    flow = RetailWorkflow(bundle).prepare(DEMO_PROMPT).diagnose(confirmed=True)
    assert flow.state == "FAILED"


def test_confirmation_and_full_demo(bundle, tmp_path):
    f = RetailWorkflow(bundle).prepare(DEMO_PROMPT)
    with pytest.raises(ValueError, match="确认"):
        f.diagnose()
    f.diagnose(confirmed=True)
    with pytest.raises(ValueError, match="确认"):
        f.screen(Strategy().model_dump())
    f.screen(Strategy().model_dump(), confirmed=True)
    assert f.state == "COMPLETED" and f.strategy_confirmed
    root = f.save(tmp_path)
    assert (root/"trace.json").is_file()
    assert "模拟" in (root/"report.md").read_text(encoding="utf-8")
    with pytest.raises(ValidationError):
        f.screen({"demand_weight": 0}, confirmed=True)
    assert not f.strategy_confirmed and f.candidates.empty
    f.screen(Strategy(min_store_m=20000).model_dump(), confirmed=True)
    assert f.state == "EMPTY"
    f.prepare("分析利润率")
    assert f.state == "NEEDS_CLARIFICATION" and f.analysis is None and f.candidates.empty


def test_online_failure_and_response(monkeypatch):
    import httpx
    monkeypatch.setenv("GEORETAIL_API_KEY", "dummy-for-test")
    monkeypatch.setenv("GEORETAIL_MODEL", "mock-model")
    def respond(request):
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": parse(DEMO_PROMPT).model_dump_json()}}]})
    req = parse(DEMO_PROMPT, "llm", transport=httpx.MockTransport(respond))
    assert req.months == 6
    def fail(request):
        raise httpx.ReadTimeout("secret provider error")
    with pytest.raises(ValueError, match="模型不可用") as exc:
        parse(DEMO_PROMPT, "llm", transport=httpx.MockTransport(fail))
    assert "secret" not in str(exc.value)


def test_tool_legacy_contract(bundle):
    from app.tool import BaseTool, ToolResult, Terminate
    tool = RetailAnalysisTool(bundle=bundle)
    assert isinstance(tool, BaseTool)
    assert tool.to_param()["function"]["parameters"]["type"] == "object"
    assert isinstance(asyncio.run(tool.execute(**parse(DEMO_PROMPT).model_dump())), ToolResult)
    assert Terminate().name == "terminate"
