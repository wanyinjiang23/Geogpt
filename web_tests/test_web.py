import json
import time
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.web import api


def controlled_worker(connection, prompt, memory, context):
    if prompt == "slow":
        time.sleep(60)
    connection.send({"type": "progress", "text": "执行工具"})
    if prompt == "error":
        connection.send({"type": "error", "text": "测试错误"})
    else:
        connection.send({"type": "done", "text": f"完成：{len(memory)}",
                         "memory": memory + [{"role": "user", "content": prompt}], "context": {}})
    connection.close()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "health", lambda: {"ready": True})
    monkeypatch.setattr(api, "run_agent", controlled_worker)
    with TestClient(api.app) as client:
        yield client


def wait_done(client, sid):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        data = client.get(f"/api/sessions/{sid}").json()
        if data["run"]["status"] != "running":
            return data
        time.sleep(.05)
    pytest.fail("worker did not finish")


def test_api_conversation_and_isolation(client):
    assert client.get("/").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    sid = client.post("/api/sessions").json()["session_id"]
    other = client.post("/api/sessions").json()["session_id"]
    for index in range(2):
        result = client.post(f"/api/sessions/{sid}/messages", json={"message": "你好"})
        assert result.status_code == 202
        data = wait_done(client, sid)
        assert data["messages"][-1]["content"] == f"完成：{index}"
        assert data["run"]["events"] == ["执行工具"]
    assert client.get(f"/api/sessions/{other}").json()["messages"] == []


def test_stop_kills_process_and_allows_next_message(client):
    sid = client.post("/api/sessions").json()["session_id"]
    path = f"/api/sessions/{sid}"
    assert client.post(path + "/messages", json={"message": "slow"}).status_code == 202
    process = api.sessions[sid].process
    pid = process.pid
    assert pid and process.is_alive()
    assert client.post(path + "/messages", json={"message": "duplicate"}).status_code == 409
    assert client.post(path + "/stop").json()["status"] == "stopped"
    assert api.sessions[sid].process is None
    # multiprocessing.Process.close only succeeds after the OS process has exited.
    assert process._closed
    assert client.post(path + "/stop").status_code == 200
    assert client.post(path + "/messages", json={"message": "again"}).status_code == 202
    assert wait_done(client, sid)["run"]["status"] == "done"


def test_validation_and_failure(client, monkeypatch):
    sid = client.post("/api/sessions").json()["session_id"]
    path = f"/api/sessions/{sid}/messages"
    assert client.post(path, json={"message": "   "}).status_code == 422
    assert client.post(path, json={"message": "x" * 20001}).status_code == 422
    assert client.get("/api/sessions/missing").status_code == 404
    assert client.post(path, json={"message": "error"}).status_code == 202
    assert wait_done(client, sid)["run"]["status"] == "error"
    monkeypatch.setattr(api, "health", lambda: {"ready": False, "configured": False})
    assert client.post(path, json={"message": "hi"}).status_code == 503


def test_original_agent_executes_gis_tool_and_restores_memory(monkeypatch, tmp_path):
    """Only provider responses are mocked; agent and buffer analysis are real."""
    import geopandas as gpd
    from shapely.geometry import Point
    from openai.types.chat import ChatCompletionMessage
    import openai
    from app.web.worker import run_agent

    source, target = tmp_path / "input.geojson", tmp_path / "buffer.shp"
    gpd.GeoDataFrame({"name": ["sample"]}, geometry=[Point(113.2, 35.2)], crs="EPSG:4326").to_file(source)
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            message = ChatCompletionMessage(role="assistant", content="开始分析", tool_calls=[{
                "id": "buffer_call", "type": "function", "function": {"name": "creat_buffer", "arguments": json.dumps({
                    "input_file": str(source), "buffer_distance": 100, "output_file": str(target)})}}])
        else:
            message = ChatCompletionMessage(role="assistant", content="缓冲区分析已完成。")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setenv("GEOGPT_API_KEY", "test-placeholder")
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion))))

    class Collector:
        def __init__(self): self.events = []
        def send(self, value): self.events.append(value)
        def close(self): pass

    first = Collector()
    run_agent(first, "创建100米缓冲区", [], {})
    assert first.events[-1]["type"] == "done", first.events
    assert target.exists()
    result = gpd.read_file(target)
    assert len(result) == 1 and result.geometry.iloc[0].area > 30000
    assert len(calls) == 2  # plain answer finishes immediately, no repeated model loop
    assert any(m["role"] == "tool" for m in first.events[-1]["memory"])
    second = Collector()
    run_agent(second, "刚才进行了什么分析？", first.events[-1]["memory"], first.events[-1]["context"])
    assert second.events[-1]["type"] == "done"
    assert any(m.get("tool_call_id") == "buffer_call" for m in calls[-1]["messages"])
