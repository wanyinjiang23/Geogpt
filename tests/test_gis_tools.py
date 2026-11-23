import math

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point, box

from geosite.gis import ANALYSIS_CRS, Layer, buffer, overlay, raster_sum


def test_buffer_500m():
    result = buffer(Layer([Point(500000, 3400000)], ANALYSIS_CRS), 500)
    assert abs(result.area - math.pi * 500**2) / (math.pi * 500**2) < 0.0002
    assert result.bounds == (499500, 3399500, 500500, 3400500)


@pytest.mark.parametrize("operation", ["intersection", "union", "difference"])
def test_overlay(operation):
    a, b = box(0, 0, 10, 10), box(5, 5, 15, 15)
    assert overlay(Layer([a], ANALYSIS_CRS), Layer([b], ANALYSIS_CRS), operation).equals(
        getattr(a, operation)(b)
    )


def raster(path, transform=None):
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        crs=ANALYSIS_CRS,
        transform=transform or from_origin(500000, 3400000, 10, 10),
        nodata=-9999,
    ) as dst:
        dst.write(np.array([[1, 2], [3, -9999]], dtype="float32"), 1)


def test_raster_nodata(tmp_path):
    a, b = tmp_path / "a.tif", tmp_path / "b.tif"
    raster(a)
    raster(b)
    result = raster_sum(a, b)
    assert result[0, 0] == 2
    assert result.mask[1, 1]


@pytest.mark.parametrize("shift,resolution", [(5, 10), (0, 20)])
def test_raster_alignment(tmp_path, shift, resolution):
    a, b = tmp_path / "a.tif", tmp_path / "b.tif"
    raster(a)
    raster(b, from_origin(500000 + shift, 3400000, resolution, resolution))
    with pytest.raises(ValueError, match="RASTER_ALIGNMENT"):
        raster_sum(a, b)
