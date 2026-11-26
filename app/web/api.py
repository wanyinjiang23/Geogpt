import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import importlib.util
import multiprocessing as mp
import os
from pathlib import Path
import time
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.web.worker import run_agent

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
TERMINAL = {"done", "error", "stopped"}


@dataclass
class Session:
    messages: list = field(default_factory=list)
    memory: list = field(default_factory=list)
    context: dict = field(default_factory=dict)
    run: dict | None = None
    process: object = None
    connection: object = None
    task: asyncio.Task | None = None
    touched: float = field(default_factory=time.monotonic)


sessions: dict[str, Session] = {}


def close_worker(session):
    if session.process:
        if session.process.is_alive():
            session.process.terminate()
        session.process.join(timeout=1)
        session.process.close()
        session.process = None
    if session.connection:
        session.connection.close()
        session.connection = None


@asynccontextmanager
async def lifespan(app):
    yield
    for session in sessions.values():
        if session.task:
            session.task.cancel()
        close_worker(session)
    sessions.clear()


app = FastAPI(title="GeoGPT", lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=Path(__file__).parent / "static"), name="assets")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/health")
def health():
    modules = ["openai", "geopandas", "rasterio", "scipy", "matplotlib", "folium",
               "langchain", "langchain_community", "langchain_openai", "faiss"]
    missing = [name for name in modules if importlib.util.find_spec(name) is None]
    configured = bool(os.getenv("GEOGPT_API_KEY") or os.getenv("OPENAI_API_KEY"))
    return {"ready": configured and not missing, "configured": configured,
            "missing_dependencies": missing, "backend": "app.Agent.gis_agent.GISAgent"}


def get_session(session_id):
    if session_id not in sessions:
        raise HTTPException(404, "会话不存在或服务已重启，请新建对话。")
    session = sessions[session_id]
    session.touched = time.monotonic()
    return session


@app.post("/api/sessions", status_code=201)
def create_session():
    for key, session in list(sessions.items()):
        if time.monotonic() - session.touched > 3600 and not session.process:
            del sessions[key]
    if len(sessions) >= 100:
        raise HTTPException(503, "会话数量已达上限，请稍后重试。")
    session_id = uuid4().hex
    sessions[session_id] = Session()
    return {"session_id": session_id}


@app.get("/api/sessions/{session_id}")
def read_session(session_id: str):
    session = get_session(session_id)
    return {"messages": session.messages, "run": session.run}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)


def finish(session, status, text):
    session.run["status"] = status
    session.messages.append({"role": "assistant", "content": text, "status": status})


async def monitor(session):
    try:
        started = time.monotonic()
        while session.run["status"] == "running":
            if session.connection.poll():
                try:
                    event = session.connection.recv()
                except EOFError:
                    finish(session, "error", "后端进程意外退出，请检查依赖和配置。")
                    break
                if event["type"] == "progress":
                    session.run["events"].append(event["text"])
                    session.run["events"] = session.run["events"][-60:]
                elif event["type"] == "done":
                    session.memory = event["memory"]
                    session.context = event["context"]
                    finish(session, "done", event["text"])
                else:
                    finish(session, "error", event["text"])
            elif not session.process.is_alive():
                finish(session, "error", "后端进程意外退出，请检查依赖和配置。")
            elif time.monotonic() - started > 900:
                finish(session, "error", "执行超时，已终止本次任务。")
            await asyncio.sleep(0.1)
    finally:
        close_worker(session)


@app.post("/api/sessions/{session_id}/messages", status_code=202)
async def send_message(session_id: str, body: ChatRequest):
    session = get_session(session_id)
    if session.run and session.run["status"] not in TERMINAL:
        raise HTTPException(409, "当前对话正在执行，请先停止或等待完成。")
    if session.task and not session.task.done():
        await session.task
    message = body.message.strip()
    if not message:
        raise HTTPException(422, "消息不能为空。")
    state = health()
    if not state["ready"]:
        detail = "请先在项目 .env 中配置 GEOGPT_API_KEY。" if not state["configured"] else "请安装 requirements-web.txt 中的后端依赖。"
        raise HTTPException(503, detail)
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    process = ctx.Process(target=run_agent, args=(child, message, session.memory, session.context), daemon=True)
    try:
        process.start()
    except Exception:
        parent.close()
        child.close()
        raise HTTPException(503, "无法启动后端任务。")
    child.close()
    session.process, session.connection = process, parent
    session.messages.append({"role": "user", "content": message})
    session.run = {"id": uuid4().hex, "status": "running", "events": []}
    session.task = asyncio.create_task(monitor(session))
    return session.run


@app.post("/api/sessions/{session_id}/stop")
async def stop(session_id: str):
    session = get_session(session_id)
    if session.run and session.run["status"] == "running":
        finish(session, "stopped", "已停止本次任务。你可以继续发送消息。")
        session.task.cancel()
        try:
            await session.task
        except asyncio.CancelledError:
            pass
        close_worker(session)
    return {"status": session.run["status"] if session.run else "idle"}
