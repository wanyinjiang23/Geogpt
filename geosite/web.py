"""Local synthetic demo; no shell or arbitrary file access."""

import os
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from .gis import safe_path
from .schema import SiteSelectionRequest
from .workflow import run

app = FastAPI(title="GeoSite v2 · synthetic offline demo")
OUTPUT_ROOT = Path(os.getenv("GEOSITE_OUTPUT_DIR", "outputs")).resolve()
ARTIFACT_NAMES = {
    "map.html",
    "map.geojson",
    "ranking.csv",
    "candidates.json",
    "report.md",
    "result.json",
    "trace.json",
}


class TextInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


@app.get("/", response_class=HTMLResponse)
def index():
    return Path(__file__).with_name("ui.html").read_text(encoding="utf-8")


@app.post("/api/parse")
def parse(body: TextInput):
    return run(body.prompt, OUTPUT_ROOT)


@app.post("/api/run")
def execute(body: SiteSelectionRequest):
    return run(body, OUTPUT_ROOT)


@app.get("/api/artifacts/{run_id}/{name}")
def artifact(run_id: str, name: str):
    try:
        if UUID(run_id).hex != run_id or name not in ARTIFACT_NAMES:
            raise ValueError("INVALID_ARTIFACT")
        path = safe_path(OUTPUT_ROOT, f"{run_id}/{name}")
        if not path.is_file():
            raise ValueError("ARTIFACT_NOT_FOUND")
    except ValueError:
        raise HTTPException(404, "工件不存在") from None
    return FileResponse(path)


@app.post("/chat")
def chat(body: TextInput):
    outcome = run(body.prompt, OUTPUT_ROOT)
    return {"response": [outcome.get("message", outcome["state"])], "workflow": outcome}


@app.get("/list_data_files")
def list_data_files():
    return {"files": ["demo_region", "hospital", "industrial_risk", "major_road"], "synthetic": True}
