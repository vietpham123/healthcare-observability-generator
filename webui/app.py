"""Healthcare Observability Generator — Web UI

FastAPI application providing a toggle-based control panel for managing
both Epic SIEM and Network log generators, along with correlated scenarios.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Ensure src/ is on the path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from shared.coordinator import ScenarioCoordinator
# GeneratorManager removed — generators run as K8s pods

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("webui")

# ── Application setup ──────────────────────────────────────────────

app = FastAPI(
    title="Healthcare Observability Generator",
    description="Control panel for Kansas City Regional Medical Center log generators",
    version="1.0.0",
)

_WEBUI_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_WEBUI_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(_WEBUI_DIR / "templates"))

# ── Shared state ───────────────────────────────────────────────────

_scenarios_dir = _PROJECT_ROOT / "config" / "scenarios"
coordinator = ScenarioCoordinator(scenarios_dir=_scenarios_dir)

# Generator manager removed — generators are managed by K8s


# ── HTML page ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/walkthrough", response_class=HTMLResponse)
async def walkthrough(request: Request):
    return templates.TemplateResponse(request, "walkthrough.html")



@app.get("/api/status")
async def api_status():
    """Overall system status."""
    return {
        "scenarios": coordinator.list_scenarios(),
    }



# ── Scenario control API ──────────────────────────────────────────

@app.get("/api/scenarios")
async def list_scenarios():
    return coordinator.list_scenarios()


@app.post("/api/scenarios/{key}/activate")
async def activate_scenario(key: str):
    if coordinator.activate(key):
        return {"status": "activated", "key": key}
    raise HTTPException(status_code=404, detail=f"Unknown scenario: {key}")


@app.post("/api/scenarios/{key}/deactivate")
async def deactivate_scenario(key: str):
    if coordinator.deactivate(key):
        return {"status": "deactivated", "key": key}
    raise HTTPException(status_code=404, detail=f"Scenario not active: {key}")


@app.post("/api/scenarios/deactivate-all")
async def deactivate_all():
    coordinator.deactivate_all()
    return {"status": "all_deactivated"}


@app.post("/api/scenarios/reload")
async def reload_scenarios():
    coordinator.reload()
    return {"status": "reloaded", "count": len(coordinator.available)}


# ── Health check ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
