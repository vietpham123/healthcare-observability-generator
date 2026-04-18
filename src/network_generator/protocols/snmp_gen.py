"""SNMP metric and trap event generator.

Generates SNMP-derived metrics (interface counters, CPU, memory) and trap events
as structured data ready for Dynatrace ingestion — NOT raw SNMP PDUs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import (
    Device,
    MetricEvent,
    Severity,
    TrapEvent,
)
from netloggen.core.random_utils import SeededRandom

# Standard SNMP trap OIDs
TRAP_LINK_DOWN = "1.3.6.1.6.3.1.1.5.3"
TRAP_LINK_UP = "1.3.6.1.6.3.1.1.5.4"
TRAP_COLD_START = "1.3.6.1.6.3.1.1.5.1"
TRAP_WARM_START = "1.3.6.1.6.3.1.1.5.2"
TRAP_AUTH_FAILURE = "1.3.6.1.6.3.1.1.5.5"
TRAP_BGP_BACKWARD = "1.3.6.1.2.1.15.3.1.14.2"
TRAP_OSPF_NBR_STATE = "1.3.6.1.2.1.14.16.2.2"
TRAP_ENT_CONFIG_CHANGE = "1.3.6.1.4.1.9.9.43.2.0.1"

_TRAP_NAMES = {
    TRAP_LINK_DOWN: "linkDown",
    TRAP_LINK_UP: "linkUp",
    TRAP_COLD_START: "coldStart",
    TRAP_WARM_START: "warmStart",
    TRAP_AUTH_FAILURE: "authenticationFailure",
    TRAP_BGP_BACKWARD: "bgpBackwardTransition",
    TRAP_OSPF_NBR_STATE: "ospfNbrStateChange",
    TRAP_ENT_CONFIG_CHANGE: "entConfigChange",
}


class SNMPGenerator:
    def __init__(self, rng: SeededRandom):
        self.rng = rng
        # Per-device, per-interface cumulative counters
        self._counters: dict[str, dict[str, int]] = {}

    def _get_counter(self, device_iface_key: str, metric: str, increment: int) -> int:
        key = f"{device_iface_key}.{metric}"
        if key not in self._counters:
            self._counters[key] = {"value": self.rng.randint(1_000_000, 100_000_000)}
        self._counters[key]["value"] += increment
        return self._counters[key]["value"]

    def generate_interface_metrics(
        self, device: Device, timestamp: datetime, diurnal_factor: float = 1.0
    ) -> list[MetricEvent]:
        metrics = []
        for iface in device.interfaces:
            if iface.status.value == "admin-down":
                continue

            base_dims = {
                "device": device.hostname,
                "interface": iface.name,
                "site": device.site,
                "vendor": device.vendor.value,
                "if_index": str(iface.if_index),
            }

            speed_bps = _parse_speed(iface.speed)
            is_up = iface.status.value == "up"

            if is_up:
                # Traffic proportional to speed and diurnal factor
                max_bytes_per_interval = int(speed_bps / 8 * 60 * 0.4)  # 40% max util per minute
                in_bytes = int(self.rng.uniform(0.01, 0.3) * max_bytes_per_interval * diurnal_factor)
                out_bytes = int(self.rng.uniform(0.01, 0.3) * max_bytes_per_interval * diurnal_factor)
                in_errors = self.rng.randint(0, 2) if self.rng.should_occur(0.1) else 0
                out_errors = self.rng.randint(0, 1) if self.rng.should_occur(0.05) else 0
            else:
                in_bytes = out_bytes = in_errors = out_errors = 0

            iface_key = f"{device.hostname}.{iface.name}"

            metrics.append(MetricEvent(
                timestamp=timestamp, metric_key="network.interface.traffic.in",
                value=float(self._get_counter(iface_key, "bytes_in", in_bytes)),
                value_type="count", dimensions=base_dims,
                device=device.hostname, site=device.site,
            ))
            metrics.append(MetricEvent(
                timestamp=timestamp, metric_key="network.interface.traffic.out",
                value=float(self._get_counter(iface_key, "bytes_out", out_bytes)),
                value_type="count", dimensions=base_dims,
                device=device.hostname, site=device.site,
            ))

            # Utilization as gauge
            if is_up and speed_bps > 0:
                util_in = min(100.0, (in_bytes * 8 / (speed_bps * 60)) * 100)
                util_out = min(100.0, (out_bytes * 8 / (speed_bps * 60)) * 100)
                metrics.append(MetricEvent(
                    timestamp=timestamp, metric_key="network.interface.utilization.in",
                    value=round(util_in, 2), dimensions=base_dims,
                    device=device.hostname, site=device.site,
                ))
                metrics.append(MetricEvent(
                    timestamp=timestamp, metric_key="network.interface.utilization.out",
                    value=round(util_out, 2), dimensions=base_dims,
                    device=device.hostname, site=device.site,
                ))

            if in_errors > 0:
                metrics.append(MetricEvent(
                    timestamp=timestamp, metric_key="network.interface.errors.in",
                    value=float(self._get_counter(iface_key, "errors_in", in_errors)),
                    value_type="count", dimensions=base_dims,
                    device=device.hostname, site=device.site,
                ))
            if out_errors > 0:
                metrics.append(MetricEvent(
                    timestamp=timestamp, metric_key="network.interface.errors.out",
                    value=float(self._get_counter(iface_key, "errors_out", out_errors)),
                    value_type="count", dimensions=base_dims,
                    device=device.hostname, site=device.site,
                ))

            # Interface oper status
            metrics.append(MetricEvent(
                timestamp=timestamp, metric_key="network.interface.status",
                value=1.0 if is_up else 2.0,  # 1=up, 2=down per IF-MIB
                dimensions=base_dims,
                device=device.hostname, site=device.site,
            ))

        return metrics

    def generate_device_metrics(
        self, device: Device, timestamp: datetime, diurnal_factor: float = 1.0
    ) -> list[MetricEvent]:
        base_dims = {
            "device": device.hostname,
            "site": device.site,
            "vendor": device.vendor.value,
            "model": device.model,
            "role": device.role.value,
        }

        base_cpu = 10 + diurnal_factor * 25
        cpu = min(99.0, max(1.0, self.rng.gauss(base_cpu, 5)))
        device.cpu_utilization = cpu

        base_mem = 40 + diurnal_factor * 15
        mem = min(95.0, max(10.0, self.rng.gauss(base_mem, 3)))
        device.memory_utilization = mem

        device.uptime_seconds += 60  # increment by poll interval

        metrics = [
            MetricEvent(
                timestamp=timestamp, metric_key="network.device.cpu.utilization",
                value=round(cpu, 1), dimensions=base_dims,
                device=device.hostname, site=device.site,
            ),
            MetricEvent(
                timestamp=timestamp, metric_key="network.device.memory.utilization",
                value=round(mem, 1), dimensions=base_dims,
                device=device.hostname, site=device.site,
            ),
            MetricEvent(
                timestamp=timestamp, metric_key="network.device.uptime",
                value=float(device.uptime_seconds), dimensions=base_dims,
                device=device.hostname, site=device.site,
            ),
        ]

        # Firewall-specific metrics
        if device.role.value == "firewall":
            base_sessions = int(5000 * diurnal_factor)
            sessions = max(0, int(self.rng.gauss(base_sessions, base_sessions * 0.1)))
            device.session_count = sessions
            metrics.append(MetricEvent(
                timestamp=timestamp, metric_key="network.firewall.sessions.active",
                value=float(sessions), dimensions=base_dims,
                device=device.hostname, site=device.site,
            ))
            metrics.append(MetricEvent(
                timestamp=timestamp, metric_key="network.firewall.sessions.rate",
                value=float(self.rng.randint(50, int(500 * diurnal_factor + 50))),
                dimensions=base_dims,
                device=device.hostname, site=device.site,
            ))

        return metrics

    def generate_trap(
        self, device: Device, timestamp: datetime, trap_oid: str, params: dict[str, Any] | None = None
    ) -> TrapEvent:
        params = params or {}
        trap_name = _TRAP_NAMES.get(trap_oid, "enterpriseSpecific")

        varbinds: dict[str, Any] = {}
        if trap_oid in (TRAP_LINK_DOWN, TRAP_LINK_UP):
            varbinds["ifIndex"] = params.get("if_index", 10101)
            varbinds["ifDescr"] = params.get("if_descr", "GigabitEthernet0/1")
            varbinds["ifOperStatus"] = 2 if trap_oid == TRAP_LINK_DOWN else 1
        elif trap_oid == TRAP_BGP_BACKWARD:
            varbinds["bgpPeerRemoteAddr"] = params.get("peer_ip", "10.0.0.2")
            varbinds["bgpPeerState"] = params.get("state", 1)  # idle
        elif trap_oid == TRAP_OSPF_NBR_STATE:
            varbinds["ospfNbrIpAddr"] = params.get("neighbor_ip", "10.0.0.2")
            varbinds["ospfNbrState"] = params.get("state", 1)  # down
        elif trap_oid == TRAP_AUTH_FAILURE:
            varbinds["snmpInBadCommunityNames"] = self.rng.randint(1, 100)

        severity = Severity.WARNING
        if trap_oid in (TRAP_LINK_DOWN, TRAP_COLD_START):
            severity = Severity.ERROR
        elif trap_oid in (TRAP_LINK_UP, TRAP_WARM_START):
            severity = Severity.NOTICE
        elif trap_oid == TRAP_AUTH_FAILURE:
            severity = Severity.WARNING

        return TrapEvent(
            timestamp=self.rng.jitter_timestamp(timestamp, max_ms=200),
            device=device.hostname,
            trap_oid=trap_oid,
            trap_name=trap_name,
            severity=severity,
            varbinds=varbinds,
            attributes={
                "network.device.vendor": device.vendor.value,
                "network.device.hostname": device.hostname,
                "network.device.role": device.role.value,
                "network.device.site": device.site,
                "network.trap.oid": trap_oid,
                "network.trap.name": trap_name,
            },
            site=device.site,
        )


def _parse_speed(speed_str: str) -> int:
    speed_str = speed_str.strip().upper()
    if speed_str.endswith("G"):
        return int(float(speed_str[:-1]) * 1_000_000_000)
    elif speed_str.endswith("M"):
        return int(float(speed_str[:-1]) * 1_000_000)
    elif speed_str.endswith("K"):
        return int(float(speed_str[:-1]) * 1_000)
    try:
        return int(speed_str)
    except ValueError:
        return 1_000_000_000  # default 1G
