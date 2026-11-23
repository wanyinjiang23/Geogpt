"""Hard filtering, deterministic ranking and independent output verification."""

from shapely.geometry import Point
from shapely.ops import unary_union

from .gis import ANALYSIS_CRS
from .schema import SiteSelectionRequest


def distances(point, geometries):
    return min(point.distance(g) for g in geometries)


def rank_candidates(candidates: list[dict], request: SiteSelectionRequest) -> list[dict]:
    """Recompute scores solely from raw exported distances and requested weights.

    Fixed normalization 1/(1+d/1000) avoids candidate-pool-dependent scaling.
    Without preferences all candidates tie; stable candidate ID breaks ties.
    """
    total = sum(p.weight for p in request.soft_preferences)
    ranked = []
    for candidate in candidates:
        row = {**candidate, "components": []}
        score = 0.0
        for p in request.soft_preferences:
            raw = row["distances_m"][p.feature_layer]
            normalized, weight = 1 / (1 + raw / 1000), p.weight / total
            score += normalized * weight
            row["components"].append(
                {
                    "layer": p.feature_layer,
                    "distance_m": raw,
                    "normalized_score": normalized,
                    "weight": weight,
                }
            )
        row["score"] = score
        ranked.append(row)
    ranked.sort(key=lambda r: (-r["score"], r["candidate_id"]))
    return [{**r, "rank": i + 1} for i, r in enumerate(ranked)]


def select(request: SiteSelectionRequest, layers: dict):
    aligned = {k: v.aligned() for k, v in layers.items()}
    region = unary_union(aligned[request.region_id].geometries)
    if region.bounds[2] - region.bounds[0] > 10000 or region.bounds[3] - region.bounds[1] > 10000:
        raise ValueError("REGION_EXTENT_EXCEEDED")
    # Demo scene only: refuse far-away layers and cross-zone/wide-area inputs.
    if not region.buffer(10000).covers(unary_union([g for v in aligned.values() for g in v.geometries])):
        raise ValueError("LAYER_OUTSIDE_LOCAL_ANALYSIS_EXTENT")
    feasible = region
    excluded = region.difference(region)
    for c in request.hard_constraints:
        coverage = unary_union(aligned[c.feature_layer].geometries).buffer(c.distance_m, quad_segs=64)
        if c.operator == "within":
            feasible = feasible.intersection(coverage)
        else:
            excluded = excluded.union(coverage.intersection(region))
            feasible = feasible.difference(coverage)
    minx, miny, maxx, maxy = region.bounds
    rows = []
    tested = 0
    # Fixed 250 m grid centers, at most 1600 for the supported 10 km extent.
    x = minx + 125
    while x < maxx:
        y = miny + 125
        while y < maxy:
            point = Point(x, y)
            tested += 1
            ds = {k: distances(point, v.geometries) for k, v in aligned.items() if k != request.region_id}
            checks = [
                {
                    "layer": c.feature_layer,
                    "operator": c.operator,
                    "limit_m": c.distance_m,
                    "actual_m": ds[c.feature_layer],
                    "passed": ds[c.feature_layer] <= c.distance_m
                    if c.operator == "within"
                    else ds[c.feature_layer] >= c.distance_m,
                }
                for c in request.hard_constraints
            ]
            # Exact distance predicate is authoritative; buffer polygons approximate circles.
            if region.covers(point) and all(c["passed"] for c in checks):
                rows.append(
                    {
                        "candidate_id": f"grid_{tested:04d}",
                        "x": x,
                        "y": y,
                        "distances_m": ds,
                        "constraints": checks,
                    }
                )
            y += 250
        x += 250
    ranked = rank_candidates(rows, request)
    return (
        ranked,
        feasible,
        excluded,
        {
            "grid_tested": tested,
            "feasible_candidates": len(rows),
            "analysis_crs": ANALYSIS_CRS,
            "distance_unit": "m",
            "algorithm": "grid-distance-weighted-v2",
            "grid_spacing_m": 250,
        },
    )


def validate_results(rows: list[dict], request: SiteSelectionRequest, layers: dict) -> None:
    """Recheck exported coordinates, raw metrics, hard predicates and rank scores."""
    aligned = {k: v.aligned() for k, v in layers.items()}
    region = unary_union(aligned[request.region_id].geometries)
    for row in rows:
        p = Point(row["x"], row["y"])
        if not region.covers(p):
            raise ValueError("RESULT_OUTSIDE_REGION")
        for layer, raw in row["distances_m"].items():
            if abs(raw - distances(p, aligned[layer].geometries)) > 1e-7:
                raise ValueError("RESULT_DISTANCE_MISMATCH")
        for c in request.hard_constraints:
            d = distances(p, aligned[c.feature_layer].geometries)
            if (c.operator == "within" and d > c.distance_m) or (
                c.operator == "outside" and d < c.distance_m
            ):
                raise ValueError("HARD_CONSTRAINT_VIOLATION")
    expected = rank_candidates(rows, request)
    if [r["candidate_id"] for r in rows] != [r["candidate_id"] for r in expected]:
        raise ValueError("RESULT_RANK_MISMATCH")
    if any(abs(a["score"] - b["score"]) > 1e-12 for a, b in zip(rows, expected, strict=True)):
        raise ValueError("RESULT_SCORE_MISMATCH")
