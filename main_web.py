from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.Agent.gis_agent import GISAgent
import asyncio
import sys
import io
import subprocess
import os

app = FastAPI()

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    if not prompt.strip():
        return JSONResponse({"error": "Empty prompt provided."}, status_code=400)
    gis_agent = GISAgent()
    # 捕获所有print输出
    old_stdout = sys.stdout
    sys.stdout = mystdout = io.StringIO()
    try:
        result = await gis_agent.run(prompt)
    finally:
        sys.stdout = old_stdout
    output = mystdout.getvalue()
    # 合并print内容和gis_agent的返回值
    full_output = output + (result if result else "")
    # 按行分割，去除空行
    lines = [line for line in full_output.splitlines() if line.strip()]
    return {"response": lines}

@app.get("/open-folder")
async def open_folder(path: str = Query(...)):
    try:
        subprocess.Popen(f'explorer "{path}"')
        return {"message": "Folder opened successfully"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/list_data_files")
async def list_data_files():
    try:
        files = os.listdir("data")
        # 只返回文件（不含子目录）
        files = [f for f in files if os.path.isfile(os.path.join("data", f))]
        return {"files": files}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)