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
from shared.generator_manager import GeneratorManager

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

output_dir = os.environ.get("OUTPUT_DIR", str(_PROJECT_ROOT / "output"))
manager = GeneratorManager(output_dir=output_dir)


# ── HTML page ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ── Generator control API ──────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    """Overall system status."""
    return {
        "generators": manager.status(),
        "scenarios": coordinator.list_scenarios(),
    }


@app.post("/api/generators/epic/start")
async def start_epic():
    return manager.start_epic().__dict__


@app.post("/api/generators/epic/stop")
async def stop_epic():
    return manager.stop_epic().__dict__


@app.post("/api/generators/network/start")
async def start_network():
    return manager.start_network().__dict__


@app.post("/api/generators/network/stop")
async def stop_network():
    return manager.stop_network().__dict__


@app.post("/api/generators/start-all")
async def start_all():
    return manager.start_all()


@app.post("/api/generators/stop-all")
async def stop_all():
    return manager.stop_all()


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


# ── Generator configuration API ───────────────────────────────────

@app.get("/api/config/epic")
async def get_epic_config():
    return manager.epic_config


@app.put("/api/config/epic")
async def update_epic_config(request: Request):
    body = await request.json()
    for key in ("generators_enabled", "tick_interval", "environment"):
        if key in body:
            manager.epic_config[key] = body[key]
    return manager.epic_config


@app.get("/api/config/network")
async def get_network_config():
    return manager.network_config


@app.put("/api/config/network")
async def update_network_config(request: Request):
    body = await request.json()
    for key in ("scenarios", "tick_interval", "mode", "duration"):
        if key in body:
            manager.network_config[key] = body[key]
    return manager.network_config


# ── Health check ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
