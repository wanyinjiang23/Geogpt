import pytest
from pyproj import Transformer
from shapely.geometry import Point, Polygon, box
from shapely import transform

from geosite.gis import ANALYSIS_CRS, Layer, overlay


@pytest.mark.parametrize(
    "layer,code",
    [
        (Layer([Point(0, 0)], None), "MISSING_CRS"),
        (Layer([], ANALYSIS_CRS), "EMPTY_LAYER"),
        (Layer([None], ANALYSIS_CRS), "INVALID_GEOMETRY"),
        (Layer([Point()], ANALYSIS_CRS), "INVALID_GEOMETRY"),
        (Layer([Polygon([(0, 0), (1, 1), (0, 1), (1, 0)])], ANALYSIS_CRS), "INVALID_GEOMETRY"),
    ],
)
def test_invalid(layer, code):
    with pytest.raises(ValueError, match=code):
        layer.aligned()


def test_mixed_crs():
    a = box(500000, 3400000, 501000, 3401000)
    b = box(500500, 3400500, 501500, 3401500)
    converter = Transformer.from_crs(ANALYSIS_CRS, "EPSG:4326", always_xy=True)
    projected = overlay(
        Layer([a], ANALYSIS_CRS),
        Layer([transform(b, converter.transform, interleaved=False)], "EPSG:4326"),
        "intersection",
    )
    assert projected.symmetric_difference(a.intersection(b)).area < 0.01


def test_feet_or_geographic_analysis_rejected():
    for crs in ["EPSG:4326", "EPSG:2263"]:
        with pytest.raises(ValueError, match="METRIC_CRS"):
            Layer([Point(1, 1)], "EPSG:4326").aligned(crs)
