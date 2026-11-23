from fastapi.testclient import TestClient

from geosite import web
from geosite.parser import EXAMPLE


def test_ui_confirmation_downloads_and_safe_routes(tmp_path, monkeypatch):
    monkeypatch.setattr(web, "OUTPUT_ROOT", tmp_path)
    client = TestClient(web.app)
    assert client.get("/").status_code == 200
    r = client.post("/api/parse", json={"prompt": EXAMPLE}).json()
    assert r["state"] == "NEEDS_CLARIFICATION"
    request = r["request"]
    request["confirmed"] = True
    done = client.post("/api/run", json=request).json()
    assert done["state"] == "COMPLETED"
    assert client.get(f"/api/artifacts/{done['run_id']}/map.html").status_code == 200
    assert client.get(f"/api/artifacts/{done['run_id']}/secret.txt").status_code == 404
    assert client.get("/api/artifacts/invalid/map.html").status_code == 404
    assert client.get("/open-folder?path=C:/").status_code == 404
    assert client.post("/api/run", json={"output_path": "../secret"}).status_code == 422
