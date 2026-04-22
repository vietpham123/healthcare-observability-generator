"""Baseline traffic generator — produces normal-state logs, metrics, traps,
and flow records each tick based on the loaded topology.

Scenario awareness:
  When ``scenario_config`` is supplied (from a JSON scenario definition),
  devices listed in ``network_correlation.events`` with action ``device_down``
  are silenced — no heartbeats, no metrics, no flows.  Devices with
  ``cpu_spike`` get elevated CPU/memory.  This lets the dashboard hex tiles
  turn red for downed devices and keeps the section health honest.
"""

from __future__ import annotations

import json
import logging
import os
import random
from datetime import datetime, timezone

from netloggen.core.models import (
    FlowRecord,
    LogEvent,
    MetricEvent,
    Severity,
    VendorType,
)

from netloggen.protocols.netflow_gen import NetFlowGenerator

logger = logging.getLogger("netloggen.scenarios.baseline")


# ── Vendor-specific syslog templates ─────────────────────────────────

_CISCO_IOS_TEMPLATES = [
    (Severity.NOTICE,  "INTERFACE", "%LINEPROTO-5-UPDOWN: Line protocol on Interface {iface}, changed state to up"),
    (Severity.WARNING, "INTERFACE", "%LINK-3-UPDOWN: Interface {iface}, changed state to up"),
    (Severity.INFO,    "ROUTING",   "%OSPF-5-ADJCHG: Process 1, Nbr {peer_ip} on {iface} from LOADING to FULL, Loading Done"),
    (Severity.INFO,    "SYSTEM",    "%CDP-4-NATIVE_VLAN_MISMATCH: Native VLAN mismatch on {iface}"),
    (Severity.INFO,    "SECURITY",  "%SYS-5-CONFIG_I: Configured from console by admin on vty0 ({src_ip})"),
    (Severity.NOTICE,  "SYSTEM",    "%ENVMON-5-FAN_OK: Fan {fan_id} running at normal speed"),
    (Severity.INFO,    "SECURITY",  "%SEC_LOGIN-5-LOGIN_SUCCESS: Login Success [user: admin] [Source: {src_ip}] [localport: 22]"),
    (Severity.WARNING, "SYSTEM",    "%IP_SLA-3-OPERATION_RTT: RTT={rtt}ms for operation {sla_id} increased"),
]

_PALOALTO_TEMPLATES = [
    (Severity.INFO,    "SYSTEM",    "Commit operation completed by admin@{src_ip} - result: succeeded"),
    (Severity.INFO,    "TRAFFIC",   "TRAFFIC: allow session {sess_id} {src_ip}:{src_port}->{dst_ip}:{dst_port} tcp rule=trust-internal"),
    (Severity.WARNING, "THREAT",    "THREAT: spyware alert session {sess_id} {src_ip}:{src_port}->{dst_ip}:{dst_port} action=alert severity=medium"),
    (Severity.INFO,    "SYSTEM",    "HA: peer state changed to active, local state active-primary"),
    (Severity.INFO,    "INTERFACE", "Interface ethernet1/{port_id} link is up, speed 1000Mbps"),
]

_FORTINET_TEMPLATES = [
    (Severity.INFO,    "TRAFFIC",   'type="traffic" action="accept" srcip={src_ip} dstip={dst_ip} dstport={dst_port} proto=6 policyid={pol_id}'),
    (Severity.WARNING, "SECURITY",  'type="event" subtype="system" action="login" user="admin" srcip={src_ip} status="success"'),
    (Severity.INFO,    "TRAFFIC",   'type="traffic" action="deny" srcip={ext_ip} dstip={dst_ip} dstport={dst_port} proto=6 policyid=0'),
    (Severity.INFO,    "SYSTEM",    'type="event" subtype="vpn" action="tunnel-up" tunnelip={src_ip} remote_ip={ext_ip}'),
]

_ARUBA_TEMPLATES = [
    (Severity.INFO,    "SECURITY",  "Auth success for client {client_mac} on port {iface} method=dot1x vlan={vlan_id}"),
    (Severity.INFO,    "INTERFACE", "Association request from {client_mac} on {iface} SSID EPIC-SECURE"),
    (Severity.NOTICE,  "SYSTEM",    "AP {device}: Channel change {iface} from 36 to 44, reason=radar"),
]

_CITRIX_TEMPLATES = [
    (Severity.INFO,    "TRAFFIC",   "SSLVPN TCPCONN {sess_id}: SPCBId {spid} - Client {src_ip} - vServer {dst_ip}:443 - NatIP {nat_ip}"),
    (Severity.INFO,    "TRAFFIC",   "TCP CONN DELINK {sess_id}: Source {src_ip}:50{src_port} - Destination {dst_ip}:443 - Duration {rtt}ms"),
]

_F5_TEMPLATES = [
    (Severity.INFO,    "SYSTEM",    "Pool /Common/epic-pool member /Common/{dst_ip}:{dst_port} monitor status up"),
    (Severity.INFO,    "TRAFFIC",   "Virtual /Common/epic_https {dst_ip}:443 conn={sess_id} pktsIn={pkt_in} pktsOut={pkt_out}"),
    (Severity.NOTICE,  "TRAFFIC",   "tmm: Rule /Common/epic-irule: {src_ip} -> {dst_ip}:443 HTTP request GET /api/FHIR/R4/Patient"),
]

_CISCO_ASA_TEMPLATES = [
    (Severity.INFO,    "SECURITY",  '%ASA-6-302013: Built outbound TCP connection {sess_id} for outside:{dst_ip}/443 to inside:{src_ip}/{src_port}'),
    (Severity.INFO,    "SECURITY",  "%ASA-6-305011: Built dynamic TCP translation from inside:{src_ip}/{src_port} to outside:{nat_ip}/{src_port}"),
    (Severity.WARNING, "SECURITY",  '%ASA-4-106023: Deny tcp src outside:{ext_ip}/443 dst inside:{dst_ip}/{dst_port} by access-group "outside_in"'),
]

_VENDOR_TEMPLATES = {
    VendorType.CISCO_IOS:  _CISCO_IOS_TEMPLATES,
    VendorType.PALOALTO:   _PALOALTO_TEMPLATES,
    VendorType.FORTINET:   _FORTINET_TEMPLATES,
    VendorType.ARUBA:      _ARUBA_TEMPLATES,
    VendorType.CITRIX:     _CITRIX_TEMPLATES,
    VendorType.F5:         _F5_TEMPLATES,
    VendorType.CISCO_ASA:  _CISCO_ASA_TEMPLATES,
}


class BaselineGenerator:
    """Generate steady-state network telemetry for every device in the topology."""

    def __init__(self, topology, rng=None, scenario_config=None):
        self.topology = topology
        self.rng = rng or random
        self._tick_count = 0
        from netloggen.core.random_utils import SeededRandom
        seed_rng = SeededRandom(seed=42) if rng is None else rng
        if not isinstance(seed_rng, SeededRandom):
            seed_rng = SeededRandom(seed=42)
        self._flow_gen = NetFlowGenerator(rng=seed_rng, topology=topology)

        # Parse scenario-driven device overrides
        self._down_devices: set[str] = set()
        self._cpu_spikes: dict[str, float] = {}  # hostname -> target cpu%
        if scenario_config:
            self._apply_scenario(scenario_config)

    def _apply_scenario(self, cfg: dict) -> None:
        """Extract network_correlation events from a scenario config."""
        net = cfg.get("network_correlation", {})
        if not net.get("enabled"):
            return
        for evt in net.get("events", []):
            device = evt.get("device", "")
            etype = evt.get("event_type", "")
            if etype == "device_down":
                self._down_devices.add(device)
                logger.info("Scenario: device %s marked DOWN", device)
            elif etype == "cpu_spike":
                cpu = evt.get("params", {}).get("cpu_percent", 85)
                self._cpu_spikes[device] = float(cpu)
                logger.info("Scenario: device %s CPU spike to %.0f%%", device, cpu)

    # ── helpers ──────────────────────────────────────────────────────

    def _rand_ip(self, prefix="10.10"):
        return f"{prefix}.{self.rng.randint(1,254)}.{self.rng.randint(1,254)}"

    def _rand_mac(self):
        return ":".join(f"{self.rng.randint(0,255):02x}" for _ in range(6))

    def _format_template(self, tmpl: str, device, iface_name: str) -> str:
        """Fill placeholders in a syslog template."""
        site_prefix = {
            "kcrmc-main": "10.10", "oak-clinic": "10.20",
            "wel-clinic": "10.30", "bel-clinic": "10.40",
            "hq-dc": "10.50", "branch-west": "10.60",
        }.get(device.site, "10.10")
        return tmpl.format(
            iface=iface_name,
            device=device.hostname,
            src_ip=self._rand_ip(site_prefix),
            dst_ip=self._rand_ip(site_prefix),
            peer_ip=self._rand_ip(site_prefix),
            ext_ip=f"{self.rng.randint(1,223)}.{self.rng.randint(0,255)}.{self.rng.randint(0,255)}.{self.rng.randint(1,254)}",
            nat_ip=self._rand_ip(site_prefix),
            client_mac=self._rand_mac(),
            sess_id=self.rng.randint(100000, 999999),
            spid=self.rng.randint(1000, 9999),
            src_port=self.rng.randint(1024, 65535),
            dst_port=self.rng.choice([443, 80, 1433, 3306, 8080, 8443, 2575]),
            pol_id=self.rng.randint(1, 50),
            vlan_id=self.rng.choice([10, 20, 30, 100, 200, 300]),
            fan_id=self.rng.randint(1, 4),
            rtt=self.rng.randint(1, 120),
            sla_id=self.rng.randint(1, 10),
            port_id=self.rng.randint(1, 24),
            pkt_in=self.rng.randint(100, 50000),
            pkt_out=self.rng.randint(100, 50000),
        )

    # ── main tick ────────────────────────────────────────────────────

    def generate_tick(self, current_time: datetime | None = None) -> dict:
        now = current_time or datetime.now(timezone.utc)
        logs: list[LogEvent] = []
        metrics: list[MetricEvent] = []

        for device in self.topology.devices:
            hostname = device.hostname
            vendor = device.vendor
            site = device.site

            # ── Scenario: skip downed devices entirely ──
            if hostname in self._down_devices:
                continue

            # 1) Heartbeat syslog (always)
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

            # 2) Vendor-specific operational events (2-5 per device per tick)
            templates = _VENDOR_TEMPLATES.get(vendor, _CISCO_IOS_TEMPLATES)
            event_count = self.rng.randint(2, 5)
            for _ in range(event_count):
                sev, etype, tmpl = self.rng.choice(templates)
                iface_name = self.rng.choice(device.interfaces).name if device.interfaces else "GigabitEthernet0/0/0"
                try:
                    content = self._format_template(tmpl, device, iface_name)
                except (KeyError, IndexError):
                    content = tmpl  # fallback: raw template
                logs.append(LogEvent(
                    timestamp=now,
                    device=device.hostname,
                    vendor=vendor,
                    severity=sev,
                    facility=23,
                    content=f"{device.hostname}: {content}",
                    event_type=etype,
                    log_source=vendor.value,
                    site=site,
                    device_role=device.role.value,
                    device_model=device.model,
                ))

            # 3) Interface metrics
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

            # 4) CPU / memory metrics (with scenario spikes)
            common_dims = {"site": site, "device": device.hostname, "vendor": vendor.value}
            if hostname in self._cpu_spikes:
                target_cpu = self._cpu_spikes[hostname]
                cpu_val = target_cpu + self.rng.uniform(-3, 3)
                mem_val = min(95, 60 + target_cpu * 0.3 + self.rng.uniform(-2, 2))
            else:
                cpu_val = self.rng.uniform(10, 45)
                mem_val = self.rng.uniform(30, 65)
            metrics.append(MetricEvent(
                timestamp=now, device=device.hostname, site=site,
                metric_key="device.cpu.utilization",
                value=cpu_val,
                dimensions=common_dims,
            ))
            metrics.append(MetricEvent(
                timestamp=now, device=device.hostname, site=site,
                metric_key="device.memory.utilization",
                value=mem_val,
                dimensions=common_dims,
            ))

        # 5) Netflow records per device (skip downed devices)
        flows: list[FlowRecord] = []
        for device in self.topology.devices:
            if device.hostname in self._down_devices:
                continue
            device_flows = self._flow_gen.generate_flows(
                device=device,
                timestamp=now,
                count=self.rng.randint(3, 8) if hasattr(self.rng, 'randint') else random.randint(3, 8),
                diurnal_factor=1.0,
            )
            flows.extend(device_flows)

        self._tick_count += 1
        return {"logs": logs, "metrics": metrics, "traps": [], "flows": flows}
