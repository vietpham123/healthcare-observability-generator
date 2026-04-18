"""Scenario coordinator — loads cross-generator scenario configs and dispatches
timed events to both the Epic SIEM generator and the Network log generator in a
temporally-correlated fashion.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("shared.coordinator")


@dataclass
class ScenarioState:
    """Runtime state for an active scenario."""
    name: str
    config: dict[str, Any]
    started_at: float = field(default_factory=time.monotonic)
    phase_index: int = 0
    active: bool = True


class ScenarioCoordinator:
    """Coordinates correlated scenarios across Epic + Network generators.

    Loads JSON scenario files from ``config/scenarios/`` and exposes methods
    for the web UI to activate/deactivate them at runtime.
    """

    def __init__(self, scenarios_dir: str | Path):
        self.scenarios_dir = Path(scenarios_dir)
        self.available: dict[str, dict] = {}
        self.active: dict[str, ScenarioState] = {}
        self._load_available()

    # ── Scenario loading ──────────────────────────────────────────

    def _load_available(self) -> None:
        if not self.scenarios_dir.is_dir():
            logger.warning("Scenarios directory not found: %s", self.scenarios_dir)
            return
        for fp in sorted(self.scenarios_dir.glob("*.json")):
            try:
                with open(fp) as f:
                    data = json.load(f)
                key = fp.stem  # e.g. "ransomware-attack"
                self.available[key] = data
                logger.info("Loaded scenario: %s (%s)", key, data.get("name", key))
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Failed to load scenario %s: %s", fp, exc)

    def reload(self) -> None:
        """Reload scenario definitions from disk."""
        self.available.clear()
        self._load_available()

    # ── Activation / deactivation ─────────────────────────────────

    def activate(self, scenario_key: str) -> bool:
        """Activate a scenario by key. Returns True on success."""
        if scenario_key not in self.available:
            logger.warning("Unknown scenario: %s", scenario_key)
            return False
        if scenario_key in self.active:
            logger.info("Scenario already active: %s", scenario_key)
            return True
        cfg = self.available[scenario_key]
        self.active[scenario_key] = ScenarioState(name=cfg.get("name", scenario_key), config=cfg)
        logger.info("Activated scenario: %s", scenario_key)
        return True

    def deactivate(self, scenario_key: str) -> bool:
        """Deactivate a running scenario. Returns True if it was active."""
        state = self.active.pop(scenario_key, None)
        if state:
            logger.info("Deactivated scenario: %s", scenario_key)
            return True
        return False

    def deactivate_all(self) -> None:
        self.active.clear()
        logger.info("All scenarios deactivated")

    # ── Query ─────────────────────────────────────────────────────

    def list_scenarios(self) -> list[dict]:
        """Return list of all scenarios with their activation state."""
        result = []
        for key, cfg in self.available.items():
            result.append({
                "key": key,
                "name": cfg.get("name", key),
                "description": cfg.get("description", ""),
                "active": key in self.active,
                "has_network_correlation": cfg.get("network_correlation", {}).get("enabled", False),
                "indicators": cfg.get("indicators", []),
            })
        return result

    def get_active_epic_overrides(self) -> dict[str, Any]:
        """Return merged Epic generator overrides from all active scenarios.

        Combines volume_multiplier (max wins), mychart_multiplier, and
        max_sessions across all active scenarios.
        """
        if not self.active:
            return {}
        volume_mult = 1.0
        mychart_mult = 1.0
        max_sessions = 20
        curve_overrides: dict[str, float] = {}

        for state in self.active.values():
            cfg = state.config
            volume_mult = max(volume_mult, cfg.get("volume_multiplier", 1.0))
            mychart_mult = max(mychart_mult, cfg.get("mychart_multiplier", 1.0))
            max_sessions = max(max_sessions, cfg.get("max_sessions", 20))
            curve_overrides.update(cfg.get("curve_overrides", {}))

        return {
            "volume_multiplier": volume_mult,
            "mychart_multiplier": mychart_mult,
            "max_sessions": max_sessions,
            "curve_overrides": curve_overrides,
        }

    def get_active_network_events(self, elapsed_seconds: float) -> list[dict]:
        """Return network events that should fire at the given elapsed time.

        Checks all active scenarios for ``network_correlation.events`` whose
        ``offset_seconds`` falls within the current tick window.
        """
        events = []
        for state in self.active.values():
            net = state.config.get("network_correlation", {})
            if not net.get("enabled"):
                continue
            scenario_elapsed = time.monotonic() - state.started_at
            for evt in net.get("events", []):
                offset = evt.get("offset_seconds", 0)
                # Fire events within a 60-second window of their offset
                if offset <= scenario_elapsed < offset + 60:
                    events.append({
                        "scenario": state.name,
                        "device": evt.get("device"),
                        "event_type": evt.get("event_type"),
                        "params": evt.get("params", {}),
                        "description": evt.get("description", ""),
                    })
        return events

    def get_active_flow_anomalies(self) -> list[dict]:
        """Return all flow anomaly definitions from active scenarios."""
        anomalies = []
        for state in self.active.values():
            net = state.config.get("network_correlation", {})
            if not net.get("enabled"):
                continue
            anomalies.extend(net.get("flow_anomalies", []))
        return anomalies
