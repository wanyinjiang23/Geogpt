"""Reproducible synthetic data, independent of private inputdata/."""
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
import pandas as pd
from pyproj import Transformer

SOURCE = "模拟数据 / CoffeeLab / seed=42 / v1"
CRS = "EPSG:32651"


@dataclass
class Bundle:
    stores: pd.DataFrame
    monthly: pd.DataFrame
    features: pd.DataFrame
    candidates: pd.DataFrame
    pois: pd.DataFrame
    crs: str = CRS


def generate(seed=42) -> Bundle:
    rng = np.random.default_rng(seed)
    def locations(n):
        x, y = 345000 + rng.uniform(0, 10000, n), 3450000 + rng.uniform(0, 10000, n)
        lon, lat = Transformer.from_crs(CRS, 4326, always_xy=True).transform(x, y)
        return {"x": x, "y": y, "lon": lon, "lat": lat}
    stores = pd.DataFrame({"store_id": [f"S{i:03}" for i in range(50)],
        "name": [f"CoffeeLab 演示店 {i+1:02}" for i in range(50)],
        "brand": "CoffeeLab", "city": "上海（模拟区域）", "region": rng.choice(["北区", "南区"], 50),
        "store_type": rng.choice(["标准店", "快取店"], 50),
        "age_months": rng.integers(4, 60, 50), **locations(50), "source_type": "synthetic"})
    features = pd.DataFrame({"store_id": stores.store_id,
        "area_type": rng.choice(["办公", "社区", "商业"], 50),
        "competitors": rng.integers(0, 16, 50), "transit_m": rng.integers(50, 1500, 50),
        "source_type": "synthetic"})
    records = []
    for i, s in stores.iterrows():
        base = rng.uniform(80000, 240000)
        for m in range(1, 13):
            if s.age_months < 12 - m + 1:
                continue
            revenue = round(base * (1 + m * .012) * rng.uniform(.88, 1.12), 2)
            # Injected association is a teaching device, not an industry finding.
            ratio = .12 + (.06 if features.iloc[i].area_type == "办公" else 0) + rng.uniform(-.07, .07)
            materials = round(revenue * .32, 2)
            labor = round(revenue * .21, 2)
            rent = round(revenue * .19, 2)
            other = round(revenue * (1-ratio) - materials-labor-rent, 2)
            cost = round(materials + labor + rent + other, 2)
            records.append({"store_id": s.store_id, "month": f"2025-{m:02}", "revenue": revenue,
                "orders": int(revenue / rng.uniform(22, 35)), "materials": materials,
                "labor": labor, "rent": rent, "other_cost": other, "cost": cost,
                "profit": round(revenue-cost, 2), "source_type": "synthetic"})
    candidates = pd.DataFrame({"site_id": [f"C{i:02}" for i in range(24)],
        "name": [f"模拟商圈 {i+1:02}" for i in range(24)],
        "city": "上海（模拟区域）", "region": rng.choice(["北区", "南区"], 24),
        **locations(24), "source_type": "synthetic"})
    pois = pd.DataFrame({"poi_id": [f"P{i:03}" for i in range(220)],
        "kind": ["transit"]*40 + ["competitor"]*80 + ["demand"]*100,
        **locations(220), "source_type": "synthetic"})
    return Bundle(stores, pd.DataFrame(records), features, candidates, pois)


def export_data(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    b = generate()
    for name in ("stores", "monthly", "features", "candidates", "pois"):
        getattr(b, name).to_csv(root / f"{name}.csv", index=False, encoding="utf-8-sig")
    (root / "metadata.json").write_text(json.dumps({"source": SOURCE, "crs": b.crs,
        "period": "2025-01..2025-12", "age_as_of": "2025-12-31",
        "note": "全部为模拟；办公商圈利润率增量为人为设定"}, ensure_ascii=False, indent=2), encoding="utf-8")
