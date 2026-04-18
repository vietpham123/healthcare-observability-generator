"""Arista EOS syslog generator.

Generates EOS-style structured syslog messages with agent-based format:
  %AGENT-SEVERITY-MNEMONIC: message
Covers FR-207.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor


@register_vendor
class AristaVendor(BaseVendor):
    vendor_type = VendorType.ARISTA

    def supported_event_types(self) -> list[str]:
        return [
            "interface_down", "interface_up", "mlag_state_change",
            "bgp_peer_down", "bgp_peer_up", "ospf_neighbor_down", "ospf_neighbor_up",
            "stp_topology_change", "lldp_neighbor_change",
            "config_change", "acl_deny",
            "cpu_high", "memory_alert", "power_supply_alert",
            "baseline_info",
        ]

    def generate_event(
        self, event_type: str, params: dict[str, Any], device: Device, timestamp: datetime
    ) -> list[LogEvent]:
        method = getattr(self, f"_gen_{event_type}", None)
        if method is None:
            return []
        return method(device, timestamp, params)

    def _ts(self, ts: datetime) -> str:
        return ts.strftime("%b %d %H:%M:%S")

    # ── Interfaces ─────────────────────────────────────────────────────

    def _gen_interface_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "Ethernet1")
        content = (f"{self._ts(ts)} {device.hostname} Phy: "
                   f"%PHY-3-LINK_DOWN: Interface {iface}, changed state to down")
        return [self._make_event(device, ts, Severity.ERROR, content, "PHY-3-LINK_DOWN",
                                 log_source="arista.phy",
                                 attributes={"network.interface.name": iface})]

    def _gen_interface_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "Ethernet1")
        content = (f"{self._ts(ts)} {device.hostname} Phy: "
                   f"%PHY-5-LINK_UP: Interface {iface}, changed state to up")
        return [self._make_event(device, ts, Severity.NOTICE, content, "PHY-5-LINK_UP",
                                 log_source="arista.phy")]

    # ── MLAG ───────────────────────────────────────────────────────────

    def _gen_mlag_state_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        state = params.get("state", "inactive")
        peer = params.get("peer_ip", "10.0.0.2")
        content = (f"{self._ts(ts)} {device.hostname} Mlag: "
                   f"%MLAG-4-STATE_CHANGE: MLAG state changed to {state}, peer {peer}")
        return [self._make_event(device, ts, Severity.WARNING, content, "MLAG-4-STATE_CHANGE",
                                 log_source="arista.mlag",
                                 attributes={"network.mlag.state": state})]

    # ── BGP ────────────────────────────────────────────────────────────

    def _gen_bgp_peer_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", "10.0.0.2")
        peer_as = params.get("peer_as", 65001)
        content = (f"{self._ts(ts)} {device.hostname} Bgp: "
                   f"%BGP-3-NOTIFICATION: sent to neighbor {peer} (AS {peer_as}) "
                   f"6/6 (Cease/Other Configuration Change) 0 bytes")
        return [self._make_event(device, ts, Severity.ERROR, content, "BGP-3-NOTIFICATION",
                                 log_source="arista.bgp",
                                 attributes={"network.bgp.peer_ip": peer})]

    def _gen_bgp_peer_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", "10.0.0.2")
        peer_as = params.get("peer_as", 65001)
        content = (f"{self._ts(ts)} {device.hostname} Bgp: "
                   f"%BGP-5-ADJCHANGE: peer {peer} (AS {peer_as}) "
                   f"Up")
        return [self._make_event(device, ts, Severity.NOTICE, content, "BGP-5-ADJCHANGE",
                                 log_source="arista.bgp")]

    # ── OSPF ───────────────────────────────────────────────────────────

    def _gen_ospf_neighbor_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        nbr = params.get("neighbor_id", "10.0.0.2")
        iface = params.get("interface", "Ethernet1")
        content = (f"{self._ts(ts)} {device.hostname} Ospf: "
                   f"%OSPF-4-ADJCHANGE: Process 1, Nbr {nbr} on {iface} from Full to Down, "
                   f"NeighborDown")
        return [self._make_event(device, ts, Severity.WARNING, content, "OSPF-4-ADJCHANGE",
                                 log_source="arista.ospf")]

    def _gen_ospf_neighbor_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        nbr = params.get("neighbor_id", "10.0.0.2")
        iface = params.get("interface", "Ethernet1")
        content = (f"{self._ts(ts)} {device.hostname} Ospf: "
                   f"%OSPF-5-ADJCHANGE: Process 1, Nbr {nbr} on {iface} from Init to Full")
        return [self._make_event(device, ts, Severity.NOTICE, content, "OSPF-5-ADJCHANGE",
                                 log_source="arista.ospf")]

    # ── STP ────────────────────────────────────────────────────────────

    def _gen_stp_topology_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        vlan = params.get("vlan", 100)
        iface = params.get("interface", "Ethernet1")
        content = (f"{self._ts(ts)} {device.hostname} Stp: "
                   f"%SPANTREE-5-TOPOTRAP: Topology change, VLAN {vlan}, "
                   f"interface {iface}")
        return [self._make_event(device, ts, Severity.NOTICE, content, "SPANTREE-5-TOPOTRAP",
                                 log_source="arista.stp")]

    # ── LLDP ───────────────────────────────────────────────────────────

    def _gen_lldp_neighbor_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "Ethernet1")
        remote = params.get("remote_host", f"peer-sw-{self.rng.randint(1,20)}")
        content = (f"{self._ts(ts)} {device.hostname} Lldp: "
                   f"%LLDP-5-NEIGHBOR_NEW: LLDP neighbor with chassisId {self.rng.random_mac()} "
                   f"and target portId {iface} added on interface {iface}")
        return [self._make_event(device, ts, Severity.NOTICE, content, "LLDP-5-NEIGHBOR_NEW",
                                 log_source="arista.lldp")]

    # ── Config ─────────────────────────────────────────────────────────

    def _gen_config_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        content = (f"{self._ts(ts)} {device.hostname} ConfigAgent: "
                   f"%SYS-5-CONFIG_E: Enter configuration mode from console by {user} on console")
        return [self._make_event(device, ts, Severity.NOTICE, content, "SYS-5-CONFIG_E",
                                 log_source="arista.configagent")]

    # ── Security ───────────────────────────────────────────────────────

    def _gen_acl_deny(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src = self.rng.random_ip("198.51.100.0/24")
        dst = self.rng.random_ip("10.0.0.0/8")
        proto = self.rng.choice(["TCP", "UDP"])
        content = (f"{self._ts(ts)} {device.hostname} Acl: "
                   f"%ACL-6-IPDENIED: Packet denied {proto} "
                   f"{src}({self.rng.random_port()}) -> "
                   f"{dst}({self.rng.choice([22, 80, 443, 3389])}) "
                   f"by access-list DENY-ALL")
        return [self._make_event(device, ts, Severity.INFO, content, "ACL-6-IPDENIED",
                                 log_source="arista.acl")]

    # ── Health ─────────────────────────────────────────────────────────

    def _gen_cpu_high(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        cpu = params.get("cpu_pct", self.rng.randint(85, 99))
        content = (f"{self._ts(ts)} {device.hostname} SupervisorCpuMon: "
                   f"%AGENT-4-CPU_THRESHOLD: Supervisor CPU utilization at {cpu}%")
        return [self._make_event(device, ts, Severity.WARNING, content, "AGENT-4-CPU_THRESHOLD",
                                 log_source="arista.agent")]

    def _gen_memory_alert(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        pct = params.get("mem_pct", self.rng.randint(90, 99))
        content = (f"{self._ts(ts)} {device.hostname} KernelMonitor: "
                   f"%AGENT-3-MEMORY_ALERT: Memory utilization at {pct}%, threshold exceeded")
        return [self._make_event(device, ts, Severity.ERROR, content, "AGENT-3-MEMORY_ALERT",
                                 log_source="arista.agent")]

    def _gen_power_supply_alert(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        psu = params.get("psu", self.rng.randint(1, 2))
        content = (f"{self._ts(ts)} {device.hostname} Ebra: "
                   f"%HARDWARE-3-PSU_FAULT: Power supply {psu} input lost")
        return [self._make_event(device, ts, Severity.ERROR, content, "HARDWARE-3-PSU_FAULT",
                                 log_source="arista.hardware")]

    # ── Baseline ───────────────────────────────────────────────────────

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        choices = [
            "lldp_neighbor_change", "config_change", "stp_topology_change",
            "interface_up", "acl_deny",
        ]
        weights = [0.25, 0.15, 0.15, 0.3, 0.15]
        evt_type = self.rng.weighted_choice(choices, weights)
        return getattr(self, f"_gen_{evt_type}")(device, ts, params)
