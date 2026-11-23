"""Bounded deterministic GIS operations. All layers use one explicit metric CRS."""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pyproj import CRS, Transformer
from shapely import transform
from shapely.geometry import shape
from shapely.ops import unary_union

ANALYSIS_CRS = "EPSG:32650"
MAX_FEATURES = 10000


def safe_path(root: Path, relative: str) -> Path:
    """Reject absolute paths, traversal, and escaping symlinks."""
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or ":" in relative or "\\" in relative:
        raise ValueError("UNSAFE_PATH")
    resolved = (root / p).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("UNSAFE_PATH")
    return resolved


def metric_crs(crs: str) -> CRS:
    result = CRS.from_user_input(crs)
    if not result.is_projected or any(abs(a.unit_conversion_factor - 1) > 1e-12 for a in result.axis_info):
        raise ValueError("METRIC_CRS_REQUIRED")
    return result


@dataclass
class Layer:
    geometries: list
    crs: str | None

    def aligned(self, target: str = ANALYSIS_CRS):
        """Validate before projection; never invent missing CRS or repair silently."""
        metric_crs(target)
        if not self.crs:
            raise ValueError("MISSING_CRS")
        if not self.geometries:
            raise ValueError("EMPTY_LAYER")
        if len(self.geometries) > MAX_FEATURES:
            raise ValueError("FEATURE_BUDGET_EXCEEDED")
        for g in self.geometries:
            if g is None or g.is_empty or not g.is_valid:
                raise ValueError("INVALID_GEOMETRY")
        converter = Transformer.from_crs(self.crs, target, always_xy=True)
        projected = [transform(g, converter.transform, interleaved=False) for g in self.geometries]
        if any(not g.is_valid or not np.isfinite(g.bounds).all() for g in projected):
            raise ValueError("PROJECTION_FAILED")
        return Layer(list({g.wkb: g for g in projected}.values()), target)


class DatasetRegistry:
    """Only application-registered IDs can resolve input paths and CRS."""

    def __init__(self, root: Path, entries: dict):
        self.root, self.entries = root, entries

    def load(self, dataset_id: str) -> Layer:
        if dataset_id not in self.entries:
            raise ValueError("UNKNOWN_DATASET")
        entry = self.entries[dataset_id]
        p = safe_path(self.root, entry["path"])
        if not p.is_file():
            raise ValueError("DATASET_NOT_FOUND")
        if p.stat().st_size > 10_000_000:
            raise ValueError("FILE_BUDGET_EXCEEDED")
        data = json.loads(p.read_text(encoding="utf-8"))
        features = data["features"]
        for f in features:
            if any(k not in f.get("properties", {}) for k in entry.get("required_fields", [])):
                raise ValueError("MISSING_FIELD")
        return Layer(
            [shape(f["geometry"]) if f.get("geometry") else None for f in features], entry.get("crs")
        ).aligned()


def buffer(layer: Layer, distance_m: float, *, target: str = ANALYSIS_CRS):
    if not 0 < distance_m <= 10000:
        raise ValueError("DISTANCE_OUT_OF_RANGE")
    return unary_union(layer.aligned(target).geometries).buffer(distance_m, quad_segs=64)


def overlay(left: Layer, right: Layer, operation: str, *, target: str = ANALYSIS_CRS):
    a, b = (unary_union(x.aligned(target).geometries) for x in (left, right))
    if operation not in ("intersection", "union", "difference"):
        raise ValueError("UNKNOWN_OPERATION")
    return getattr(a, operation)(b)


def raster_sum(left: Path, right: Path):
    """Strict grid equality; reject misalignment rather than implicit resampling.

    Invalid/NoData pixels propagate through a masked result. No expressions accepted.
    """
    import rasterio

    with rasterio.open(left) as a, rasterio.open(right) as b:
        if not a.crs or not b.crs:
            raise ValueError("MISSING_CRS")
        if max(a.width * a.height, b.width * b.height) > 1_000_000:
            raise ValueError("RASTER_BUDGET_EXCEEDED")
        if (a.crs, a.transform, a.width, a.height) != (b.crs, b.transform, b.width, b.height):
            raise ValueError("RASTER_ALIGNMENT_REQUIRED: explicit resampling required")
        return a.read(1, masked=True).astype("float64") + b.read(1, masked=True).astype("float64")
