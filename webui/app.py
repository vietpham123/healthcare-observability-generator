"""Healthcare Observability Generator — Web UI

FastAPI application providing a toggle-based control panel for managing
both Epic SIEM and Network log generators, along with correlated scenarios.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Ensure src/ is on the path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from shared.coordinator import ScenarioCoordinator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("webui")

# ── Kubernetes API helper ──────────────────────────────────────────

K8S_HOST = os.environ.get("KUBERNETES_SERVICE_HOST", "")
K8S_PORT = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
K8S_NAMESPACE = "healthcare-gen"
_SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
_SA_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

# Map from shared-config scenario keys (hyphenated) to epic generator keys (underscored)
SCENARIO_KEY_MAP = {
    # Shared-config keys (hyphenated) → epic generator keys (underscored)
    "ransomware-attack": "ransomware",
    "insider-threat-snooping": "insider_threat",
    "hl7-interface-failure": "hl7_interface_failure",
    "core-switch-failure": "core_switch_failure",
    "normal-day-shift": "normal_shift",
    # Epic-native keys map to themselves
    "ransomware": "ransomware",
    "insider_threat": "insider_threat",
    "hl7_interface_failure": "hl7_interface_failure",
    "core_switch_failure": "core_switch_failure",
    "normal_shift": "normal_shift",
}


def _k8s_available() -> bool:
    return bool(K8S_HOST) and os.path.isfile(_SA_TOKEN_PATH)


def _k8s_token() -> str:
    with open(_SA_TOKEN_PATH) as f:
        return f.read().strip()


def _k8s_ssl() -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=_SA_CA_PATH)
    return ctx


async def _k8s_patch_configmap(data: dict) -> bool:
    """Patch the generator-config ConfigMap via the K8s API."""
    if not _k8s_available():
        logger.warning("Kubernetes API not available (not running in-cluster)")
        return False
    url = (
        f"https://{K8S_HOST}:{K8S_PORT}"
        f"/api/v1/namespaces/{K8S_NAMESPACE}/configmaps/generator-config"
    )
    payload = {"data": data}
    headers = {
        "Authorization": f"Bearer {_k8s_token()}",
        "Content-Type": "application/strategic-merge-patch+json",
    }
    ssl_ctx = _k8s_ssl()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=payload, headers=headers, ssl=ssl_ctx) as resp:
                if resp.status == 200:
                    logger.info("ConfigMap patched: %s", data)
                    return True
                body = await resp.text()
                logger.error("ConfigMap patch failed %d: %s", resp.status, body[:200])
                return False
    except Exception as exc:
        logger.error("ConfigMap patch error: %s", exc)
        return False


async def _k8s_restart_deployment(name: str) -> bool:
    """Trigger a rollout restart of a deployment via the K8s API."""
    if not _k8s_available():
        logger.warning("Kubernetes API not available (not running in-cluster)")
        return False
    url = (
        f"https://{K8S_HOST}:{K8S_PORT}"
        f"/apis/apps/v1/namespaces/{K8S_NAMESPACE}/deployments/{name}"
    )
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": now
                    }
                }
            }
        }
    }
    headers = {
        "Authorization": f"Bearer {_k8s_token()}",
        "Content-Type": "application/strategic-merge-patch+json",
    }
    ssl_ctx = _k8s_ssl()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=payload, headers=headers, ssl=ssl_ctx) as resp:
                if resp.status == 200:
                    logger.info("Deployment %s restarted", name)
                    return True
                body = await resp.text()
                logger.error("Restart %s failed %d: %s", name, resp.status, body[:200])
                return False
    except Exception as exc:
        logger.error("Restart %s error: %s", name, exc)
        return False


# ── Application setup ──────────────────────────────────────────────

app = FastAPI(
    title="Healthcare Observability Generator",
    description="Control panel for Kansas City Regional Medical Center log generators",
    version="2.0.0",
)

_WEBUI_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_WEBUI_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(_WEBUI_DIR / "templates"))

# ── Shared state ───────────────────────────────────────────────────

_scenarios_dir = _PROJECT_ROOT / "config" / "scenarios"
coordinator = ScenarioCoordinator(scenarios_dir=_scenarios_dir)

# Also load epic-native scenarios so they appear in the UI
_epic_scenarios_dir = _PROJECT_ROOT / "src" / "epic_generator" / "config" / "scenarios"
if _epic_scenarios_dir.is_dir():
    for fp in sorted(_epic_scenarios_dir.glob("*.json")):
        key = fp.stem
        if key not in coordinator.available:
            try:
                with open(fp) as f:
                    data = json.load(f)
                coordinator.available[key] = data
                logger.info("Loaded epic scenario: %s", key)
            except Exception:
                pass


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
        "k8s_connected": _k8s_available(),
    }


# ── Scenario control API ──────────────────────────────────────────

@app.get("/api/scenarios")
async def list_scenarios():
    return coordinator.list_scenarios()


@app.post("/api/scenarios/{key}/activate")
async def activate_scenario(key: str):
    if key not in coordinator.available:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {key}")

    # Exclusive selection: deactivate any currently active scenario first
    previously_active = list(coordinator.active.keys())
    coordinator.deactivate_all()
    coordinator.activate(key)

    # Map to epic generator scenario key
    epic_key = SCENARIO_KEY_MAP.get(key, key)

    # Single ConfigMap patch + single restart (no race condition)
    cm_ok = await _k8s_patch_configmap({"EPIC_SCENARIO": epic_key})
    restart_ok = await _k8s_restart_deployment("epic-generator")

    return {
        "status": "activated",
        "key": key,
        "epic_scenario": epic_key,
        "previously_active": previously_active,
        "configmap_patched": cm_ok,
        "generator_restarted": restart_ok,
    }


@app.post("/api/scenarios/{key}/deactivate")
async def deactivate_scenario(key: str):
    if not coordinator.deactivate(key):
        raise HTTPException(status_code=404, detail=f"Scenario not active: {key}")

    # Always fall back to normal_shift when deactivating
    cm_ok = await _k8s_patch_configmap({"EPIC_SCENARIO": "normal_shift"})
    restart_ok = await _k8s_restart_deployment("epic-generator")

    return {
        "status": "deactivated",
        "key": key,
        "configmap_patched": cm_ok,
        "generator_restarted": restart_ok,
    }


@app.post("/api/scenarios/deactivate-all")
async def deactivate_all():
    coordinator.deactivate_all()
    cm_ok = await _k8s_patch_configmap({"EPIC_SCENARIO": "normal_shift"})
    restart_ok = await _k8s_restart_deployment("epic-generator")
    return {
        "status": "all_deactivated",
        "configmap_patched": cm_ok,
        "generator_restarted": restart_ok,
    }


@app.post("/api/scenarios/reload")
async def reload_scenarios():
    coordinator.reload()
    return {"status": "reloaded", "count": len(coordinator.available)}


# ── Health check ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "k8s": _k8s_available()}
