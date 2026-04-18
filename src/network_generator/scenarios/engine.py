"""Scenario engine — loads YAML scenario playbooks and executes them
against the topology, producing timed log/metric/trap/flow events."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from netloggen.core.models import (
    FlowRecord,
    LogEvent,
    MetricEvent,
    Severity,
    TrapEvent,
)

logger = logging.getLogger("netloggen.scenarios.engine")

_SEVERITY_MAP = {
    "emergency": Severity.EMERGENCY,
    "alert": Severity.ALERT,
    "critical": Severity.CRITICAL,
    "error": Severity.ERROR,
    "warning": Severity.WARNING,
    "notice": Severity.NOTICE,
    "info": Severity.INFO,
    "debug": Severity.DEBUG,
}


@dataclass
class ScenarioStep:
    offset_seconds: int
    action: str
    targets: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ScenarioPlaybook:
    name: str
    description: str
    duration_seconds: int
    steps: list[ScenarioStep] = field(default_factory=list)
    severity: str = "warning"


def load_scenario(path: str | Path) -> ScenarioPlaybook:
    """Load a scenario playbook from a YAML file."""
    p = Path(path)
    with open(p) as f:
        data = yaml.safe_load(f)

    steps = []
    for s in data.get("steps", []):
        steps.append(ScenarioStep(
            offset_seconds=s.get("offset_seconds", 0),
            action=s.get("action", "log"),
            targets=s.get("targets", []),
            params=s.get("params", {}),
            description=s.get("description", ""),
        ))

    return ScenarioPlaybook(
        name=data.get("name", p.stem),
        description=data.get("description", ""),
        duration_seconds=data.get("duration_seconds", 3600),
        steps=sorted(steps, key=lambda s: s.offset_seconds),
        severity=data.get("severity", "warning"),
    )


class ScenarioEngine:
    """Execute scenario playbooks against a topology."""

    def __init__(self, topology, rng=None):
        self.topology = topology
        self.rng = rng
        self._device_map = {d.hostname: d for d in topology.devices}

    def execute_scenario(self, playbook: ScenarioPlaybook, start_time: datetime) -> dict:
        """Execute all steps in a playbook and return generated events."""
        logs: list[LogEvent] = []
        metrics: list[MetricEvent] = []
        traps: list[TrapEvent] = []
        flows: list[FlowRecord] = []

        for step in playbook.steps:
            ts = start_time + timedelta(seconds=step.offset_seconds)
            targets = step.targets or [d.hostname for d in self.topology.devices[:1]]

            for target in targets:
                device = self._device_map.get(target)
                if not device:
                    logger.warning("Scenario target %s not found in topology", target)
                    continue

                action = step.action.lower()
                site = device.site
                sev_str = step.params.get("severity", playbook.severity).lower()
                severity = _SEVERITY_MAP.get(sev_str, Severity.WARNING)

                if action in ("log", "alert", "syslog"):
                    msg = step.params.get(
                        "message",
                        f"Scenario [{playbook.name}]: {step.description}",
                    )
                    logs.append(LogEvent(
                        timestamp=ts,
                        device=device.hostname,
                        vendor=device.vendor,
                        severity=severity,
                        content=msg,
                        event_type=step.params.get("event_type", "SCENARIO"),
                        log_source=device.vendor.value,
                        scenario_id=playbook.name,
                        site=site,
                        device_role=device.role.value,
                        device_model=device.model,
                    ))

                elif action in ("metric", "spike", "degrade"):
                    metrics.append(MetricEvent(
                        timestamp=ts,
                        device=device.hostname,
                        metric_key=step.params.get("metric", "device.cpu.utilization"),
                        value=step.params.get("value", 95.0),
                        dimensions={"site": site, "scenario": playbook.name},
                        site=site,
                    ))

                elif action in ("trap", "snmp_trap"):
                    traps.append(TrapEvent(
                        timestamp=ts,
                        device=device.hostname,
                        trap_oid=step.params.get("oid", "1.3.6.1.6.3.1.1.5.3"),
                        trap_name=step.params.get("trap_name", step.description),
                        severity=severity,
                        site=site,
                    ))

                elif action in ("flow", "traffic"):
                    flows.append(FlowRecord(
                        timestamp=ts,
                        device=device.hostname,
                        src_ip=step.params.get("src_ip", "0.0.0.0"),
                        dst_ip=step.params.get("dst_ip", "0.0.0.0"),
                        src_port=step.params.get("src_port", 0),
                        dst_port=step.params.get("dst_port", 0),
                        protocol=step.params.get("protocol", "tcp"),
                        bytes_total=step.params.get("bytes", 0),
                        packets_total=step.params.get("packets", 0),
                        site=site,
                    ))

        logger.info(
            "Scenario '%s' generated %d logs, %d metrics, %d traps, %d flows",
            playbook.name, len(logs), len(metrics), len(traps), len(flows),
        )
        return {"logs": logs, "metrics": metrics, "traps": traps, "flows": flows}
