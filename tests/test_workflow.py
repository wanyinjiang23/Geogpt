import json

from geosite.datasets import demo_layers
from geosite.gis import Layer
from geosite.parser import EXAMPLE
from geosite.workflow import STATES, run


def test_confirmation_and_isolation(tmp_path):
    first = run(EXAMPLE, tmp_path)
    assert first["state"] == "NEEDS_CLARIFICATION"
    assert not (tmp_path / first["run_id"] / "map.html").exists()
    second = run(EXAMPLE, tmp_path, confirmed=True)
    assert second["state"] == "COMPLETED"
    assert [e["state"] for e in second["trace"]] == STATES
    assert first["run_id"] != second["run_id"]
    for artifact in second["result"]["artifacts"]:
        assert (tmp_path / artifact["relative_path"]).is_file()
    features = json.loads((tmp_path / second["run_id"] / "map.geojson").read_text())["features"]
    points = [f for f in features if f["properties"]["role"] == "candidate"]
    assert len(points) == second["result"]["metrics"]["output_feature_count"]
    assert all(115 < p["geometry"]["coordinates"][0] < 119 for p in points)


def test_failure_trace(tmp_path):
    layers = demo_layers()
    layers["hospital"] = Layer(layers["hospital"].geometries, None)
    r = run(EXAMPLE, tmp_path, confirmed=True, layers=layers)
    assert r["state"] == "FAILED"
    assert r["result"]["error"]["code"] == "MISSING_CRS"
    assert r["result"]["artifacts"] == []


def test_empty(tmp_path):
    r = run("距医院不超过1米", tmp_path, confirmed=True)
    assert r["state"] == "COMPLETED"
    assert r["result"]["status"] == "empty"
    assert r["top_k"] == []
