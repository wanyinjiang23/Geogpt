"""Financial and descriptive calculations; never delegate numbers to an LLM."""
import numpy as np
import pandas as pd
from .schema import AnalysisRequest


def validate_data(b):
    for frame in (b.stores, b.monthly, b.features, b.candidates, b.pois):
        if frame.empty or frame.isna().any().any():
            raise ValueError("数据为空或有缺失值，请修复数据后重试")
    m = b.monthly
    if m.duplicated(["store_id", "month"]).any() or b.stores.store_id.duplicated().any():
        raise ValueError("重复主键")
    if b.features.store_id.duplicated().any() or set(b.features.store_id) != set(b.stores.store_id):
        raise ValueError("空间特征关联不完整")
    if not set(m.store_id).issubset(set(b.stores.store_id)):
        raise ValueError("经营记录关联错误")
    columns = ["revenue", "orders", "cost", "profit", "materials", "labor", "rent", "other_cost"]
    if not np.isfinite(m[columns].to_numpy(dtype=float)).all():
        raise ValueError("非有限财务数据")
    if (m[["revenue", "orders", "cost"]] < 0).any().any():
        raise ValueError("非法财务数据")
    if not np.allclose(m.revenue-m.cost, m.profit, atol=.011, rtol=0):
        raise ValueError("收入成本利润不一致")
    if not np.allclose(m[["materials", "labor", "rent", "other_cost"]].sum(axis=1), m.cost, atol=.011, rtol=0):
        raise ValueError("成本分项不一致")


def analyze(b, request: AnalysisRequest):
    validate_data(b)
    end = pd.Period(request.end_month, freq="M")
    start = end-request.months+1
    monthly = b.monthly[b.monthly.month.between(str(start), str(end))].copy()
    stores = b.stores[b.stores.city == request.city].copy()
    # Maturity >=12 months at start of analysis window, not at its end.
    stores["age_at_start"] = stores.age_months - (12-start.month)
    if request.mature_only:
        stores = stores[stores.age_at_start >= 12]
    monthly = monthly[monthly.store_id.isin(stores.store_id)]
    counts = monthly.groupby("store_id").month.nunique()
    eligible = counts[counts == request.months].index
    monthly = monthly[monthly.store_id.isin(eligible)]
    if monthly.empty:
        raise ValueError("没有具有完整时间窗口的可比门店")
    sums = monthly.groupby("store_id")[["revenue", "orders", "cost", "profit"]].sum()
    sums["margin"] = sums.profit.div(sums.revenue.where(sums.revenue != 0))
    sums["ticket"] = sums.revenue.div(sums.orders.where(sums.orders != 0))
    previous = b.monthly[b.monthly.month.between(str(start-request.months), str(start-1))]
    pc = previous.groupby("store_id").month.nunique()
    prev = previous[previous.store_id.isin(pc[pc == request.months].index)].groupby("store_id").revenue.sum()
    sums["growth"] = sums.revenue.div(prev.where(prev != 0))-1
    ranking = sums.reset_index().merge(stores, on="store_id").merge(b.features, on="store_id", suffixes=("", "_feature"))
    ranking = ranking.sort_values([request.metric, "store_id"], ascending=[False, True], na_position="last")
    if request.metric == "growth":
        ranking = ranking[ranking.growth.notna()]
    if ranking.empty:
        raise ValueError("缺少等长前期数据，无法计算增长率")
    top = ranking.head(request.top_n)
    groups = ranking.groupby(["store_type", "area_type"]).agg(sample=("store_id", "size"), revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index()
    groups["margin"] = groups.profit.div(groups.revenue.where(groups.revenue != 0))
    comparison = pd.DataFrame({"特征": ["竞品数量", "交通距离（米）"],
        "优秀样本均值": [top.competitors.mean(), top.transit_m.mean()],
        "其余样本均值": [ranking.iloc[len(top):].competitors.mean(), ranking.iloc[len(top):].transit_m.mean()]})
    corr = ranking[["margin", "competitors", "transit_m"]].corr().round(4)
    observation = f"可比门店 {len(ranking)} 家，优秀样本 {len(top)} 家；优秀样本中{top.area_type.mode().iloc[0]}商圈占比 {(top.area_type == top.area_type.mode().iloc[0]).mean():.0%}。仅为模拟样本描述与关联，不能推断因果或新店收益。"
    return {"ranking": ranking, "top": top, "groups": groups, "comparison": comparison,
        "correlation": corr, "monthly": monthly, "summary": observation,
        "period": f"{start} 至 {end}", "excluded_count": len(stores)-len(ranking)}
