"""Baseline traffic generator — produces normal-state logs, metrics, traps,
and flow records each tick based on the loaded topology."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("netloggen.scenarios.baseline")


@dataclass
class LogEvent:
    timestamp: datetime
    device: str
    vendor: str
    severity: str
    facility: str
    message: str
    site: str = ""
    raw: str = ""


@dataclass
class MetricPoint:
    timestamp: datetime
    device: str
    metric: str
    value: float
    labels: dict = field(default_factory=dict)


@dataclass
class TrapEvent:
    timestamp: datetime
    device: str
    oid: str
    value: Any = None
    community: str = "public"


@dataclass
class FlowRecord:
    timestamp: datetime
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    bytes: int
    packets: int
    device: str = ""


class BaselineGenerator:
    """Generate steady-state network telemetry for every device in the topology."""

    def __init__(self, topology, rng=None):
        self.topology = topology
        self.rng = rng or random
        self._tick_count = 0

    def generate_tick(self, current_time: datetime | None = None) -> dict:
        now = current_time or datetime.now(timezone.utc)
        logs, metrics, traps, flows = [], [], [], []

        for device in self.topology.devices:
            # Syslog-style log per device
            logs.append(LogEvent(
                timestamp=now,
                device=device.hostname,
                vendor=getattr(device, "vendor", "generic"),
                severity="INFO",
                facility="local0",
                message=(
                    f"{device.hostname}: heartbeat tick={self._tick_count} "
                    f"up interfaces={len(getattr(device, 'interfaces', []))}"
                ),
                site=getattr(device, "site", ""),
            ))

            # Interface metrics
            for iface in getattr(device, "interfaces", []):
                base_bps = getattr(iface, "bandwidth_mbps", 1000) * 1e6
                util = self.rng.uniform(0.05, 0.35)
                metrics.append(MetricPoint(
                    timestamp=now,
                    device=device.hostname,
                    metric="ifHCInOctets",
                    value=base_bps * util / 8,
                    labels={
                        "interface": getattr(iface, "name", "eth0"),
                        "site": getattr(device, "site", ""),
                    },
                ))
                metrics.append(MetricPoint(
                    timestamp=now,
                    device=device.hostname,
                    metric="ifHCOutOctets",
                    value=base_bps * util * self.rng.uniform(0.6, 0.9) / 8,
                    labels={
                        "interface": getattr(iface, "name", "eth0"),
                        "site": getattr(device, "site", ""),
                    },
                ))

            # CPU / memory metrics
            metrics.append(MetricPoint(
                timestamp=now, device=device.hostname, metric="cpuUtilization",
                value=self.rng.uniform(10, 45),
                labels={"site": getattr(device, "site", "")},
            ))
            metrics.append(MetricPoint(
                timestamp=now, device=device.hostname, metric="memoryUtilization",
                value=self.rng.uniform(30, 65),
                labels={"site": getattr(device, "site", "")},
            ))

        self._tick_count += 1
        return {"logs": logs, "metrics": metrics, "traps": traps, "flows": flows}
