"""Synthetic local scene, not real city/POI data or planning standards."""

from shapely.geometry import LineString, Point, box

from .gis import ANALYSIS_CRS, Layer


def demo_layers() -> dict[str, Layer]:
    x, y = 500000, 3400000
    return {
        "demo_region": Layer([box(x, y, x + 3000, y + 3000)], ANALYSIS_CRS),
        "hospital": Layer([Point(x + 1000, y + 1500), Point(x + 2400, y + 2200)], ANALYSIS_CRS),
        "industrial_risk": Layer([Point(x + 400, y + 400)], ANALYSIS_CRS),
        "major_road": Layer([LineString([(x, y + 1000), (x + 3000, y + 1000)])], ANALYSIS_CRS),
    }
