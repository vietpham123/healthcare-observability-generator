"""Scenario engine — loads YAML scenario playbooks and executes them
against the topology, producing timed log/metric/trap/flow events."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from netloggen.scenarios.baseline import LogEvent, MetricPoint, TrapEvent, FlowRecord

logger = logging.getLogger("netloggen.scenarios.engine")


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
        metrics: list[MetricPoint] = []
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
                site = getattr(device, "site", "")

                if action in ("log", "alert", "syslog"):
                    severity = step.params.get("severity", playbook.severity).upper()
                    msg = step.params.get(
                        "message",
                        f"Scenario [{playbook.name}]: {step.description}",
                    )
                    logs.append(LogEvent(
                        timestamp=ts,
                        device=device.hostname,
                        vendor=getattr(device, "vendor", "generic"),
                        severity=severity,
                        facility=step.params.get("facility", "local0"),
                        message=msg,
                        site=site,
                    ))

                elif action in ("metric", "spike", "degrade"):
                    metrics.append(MetricPoint(
                        timestamp=ts,
                        device=device.hostname,
                        metric=step.params.get("metric", "cpuUtilization"),
                        value=step.params.get("value", 95.0),
                        labels={"site": site, "scenario": playbook.name},
                    ))

                elif action in ("trap", "snmp_trap"):
                    traps.append(TrapEvent(
                        timestamp=ts,
                        device=device.hostname,
                        oid=step.params.get("oid", "1.3.6.1.6.3.1.1.5.3"),
                        value=step.params.get("value", step.description),
                    ))

                elif action in ("flow", "traffic"):
                    flows.append(FlowRecord(
                        timestamp=ts,
                        src_ip=step.params.get("src_ip", "0.0.0.0"),
                        dst_ip=step.params.get("dst_ip", "0.0.0.0"),
                        src_port=step.params.get("src_port", 0),
                        dst_port=step.params.get("dst_port", 0),
                        protocol=step.params.get("protocol", 6),
                        bytes=step.params.get("bytes", 0),
                        packets=step.params.get("packets", 0),
                        device=device.hostname,
                    ))

        logger.info(
            "Scenario '%s' generated %d logs, %d metrics, %d traps, %d flows",
            playbook.name, len(logs), len(metrics), len(traps), len(flows),
        )
        return {"logs": logs, "metrics": metrics, "traps": traps, "flows": flows}
