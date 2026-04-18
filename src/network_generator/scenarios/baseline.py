"""Baseline traffic generator — produces normal-state logs, metrics, traps,
and flow records each tick based on the loaded topology."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone

from netloggen.core.models import (
    LogEvent,
    MetricEvent,
    Severity,
    VendorType,
)

logger = logging.getLogger("netloggen.scenarios.baseline")


class BaselineGenerator:
    """Generate steady-state network telemetry for every device in the topology."""

    def __init__(self, topology, rng=None):
        self.topology = topology
        self.rng = rng or random
        self._tick_count = 0

    def generate_tick(self, current_time: datetime | None = None) -> dict:
        now = current_time or datetime.now(timezone.utc)
        logs: list[LogEvent] = []
        metrics: list[MetricEvent] = []

        for device in self.topology.devices:
            vendor = device.vendor
            site = device.site

            # Syslog heartbeat log per device
            logs.append(LogEvent(
                timestamp=now,
                device=device.hostname,
                vendor=vendor,
                severity=Severity.INFO,
                facility=23,
                content=(
                    f"{device.hostname}: heartbeat tick={self._tick_count} "
                    f"up interfaces={len(device.interfaces)}"
                ),
                event_type="SYSTEM",
                log_source=vendor.value,
                site=site,
                device_role=device.role.value,
                device_model=device.model,
            ))

            # Interface metrics
            for iface in device.interfaces:
                speed_map = {"100M": 1e8, "1G": 1e9, "10G": 1e10, "40G": 4e10, "100G": 1e11}
                base_bps = speed_map.get(iface.speed, 1e9)
                util = self.rng.uniform(0.05, 0.35)
                dims = {
                    "interface": iface.name,
                    "site": site,
                    "device": device.hostname,
                    "vendor": vendor.value,
                }
                metrics.append(MetricEvent(
                    timestamp=now, device=device.hostname, site=site,
                    metric_key="if.traffic.in.bytes",
                    value=base_bps * util / 8,
                    dimensions=dims,
                ))
                metrics.append(MetricEvent(
                    timestamp=now, device=device.hostname, site=site,
                    metric_key="if.traffic.out.bytes",
                    value=base_bps * util * self.rng.uniform(0.6, 0.9) / 8,
                    dimensions=dims,
                ))

            # CPU / memory metrics
            common_dims = {"site": site, "device": device.hostname, "vendor": vendor.value}
            metrics.append(MetricEvent(
                timestamp=now, device=device.hostname, site=site,
                metric_key="device.cpu.utilization",
                value=self.rng.uniform(10, 45),
                dimensions=common_dims,
            ))
            metrics.append(MetricEvent(
                timestamp=now, device=device.hostname, site=site,
                metric_key="device.memory.utilization",
                value=self.rng.uniform(30, 65),
                dimensions=common_dims,
            ))

        self._tick_count += 1
        return {"logs": logs, "metrics": metrics, "traps": [], "flows": []}
