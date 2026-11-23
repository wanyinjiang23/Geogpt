"""Reuse GeoSite metric geometry validation, buffer and overlay primitives."""
import math
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.ops import unary_union
from geosite.gis import Layer, metric_crs, buffer, overlay
from .schema import Strategy


def select_sites(b, strategy: Strategy):
    metric_crs(b.crs)
    def points(df):
        if df.empty or not np.isfinite(df[["x", "y"]].to_numpy()).all():
            raise ValueError("空间数据为空或坐标非法")
        return Layer([Point(x, y) for x, y in zip(df.x, df.y)], b.crs).aligned(b.crs)
    stores = points(b.stores)
    candidates = points(b.candidates)
    poi_layers = {k: points(b.pois[b.pois.kind == k]) for k in ("transit", "competitor", "demand")}
    coverage = buffer(stores, strategy.radius_m, target=b.crs)
    rows = []
    rejected = {"区域": 0, "门店间距": 0, "交通距离": 0, "竞品数量": 0}
    for (_, site), point in zip(b.candidates.iterrows(), candidates.geometries):
        if strategy.region != "全部" and site.region != strategy.region:
            rejected["区域"] += 1
            continue
        nearest = point.distance(unary_union(stores.geometries))
        transit = point.distance(unary_union(poi_layers["transit"].geometries))
        ring = buffer(Layer([point], stores.crs), strategy.radius_m, target=b.crs)
        competition = sum(ring.covers(p) for p in poi_layers["competitor"].geometries)
        demand = sum(ring.covers(p) for p in poi_layers["demand"].geometries)
        flags = [nearest >= strategy.min_store_m, transit <= strategy.max_transit_m, competition <= strategy.max_competitors]
        for label, valid in zip(["门店间距", "交通距离", "竞品数量"], flags):
            rejected[label] += int(not valid)
        if not all(flags):
            continue
        overlap = overlay(Layer([ring], stores.crs), Layer([coverage], stores.crs), "intersection", target=b.crs).area/ring.area
        # Fixed anchors allow comparison between different feasible subsets.
        ds = min(demand/10, 1)*100
        ts = max(0, 1-transit/3000)*100
        cs = max(0, 1-competition/20)*100
        score = (ds*strategy.demand_weight+ts*strategy.transit_weight+cs*strategy.competition_weight)/100
        row = site.to_dict()
        row.update(nearest_store_m=nearest, transit_m=transit, competitors=competition,
            demand=demand, demand_density_km2=demand/(math.pi*(strategy.radius_m/1000)**2),
            overlap_ratio=overlap, demand_score=ds, transit_score=ts, competition_score=cs,
            score=score, constraints_satisfied=True)
        rows.append(row)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["score", "site_id"], ascending=[False, True]).head(strategy.top_n).reset_index(drop=True)
        if not (frame.nearest_store_m.ge(strategy.min_store_m).all() and frame.transit_m.le(strategy.max_transit_m).all() and frame.competitors.le(strategy.max_competitors).all()):
            raise ValueError("结果约束校验失败")
    return frame, rejected
