"""Cisco NX-OS syslog generator — Nexus data center switches.

Generates NX-OS specific facilities: VPC, FEX, LLDP, HSRP, fabric.
Format: TIMESTAMP : %FACILITY-SEVERITY-MNEMONIC: message
Covers FR-202.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor


@register_vendor
class CiscoNXOSVendor(BaseVendor):
    vendor_type = VendorType.CISCO_NXOS

    def supported_event_types(self) -> list[str]:
        return [
            "interface_down", "interface_up", "vpc_peer_down", "vpc_peer_up",
            "vpc_consistency_check", "fex_online", "fex_offline",
            "ospf_neighbor_down", "ospf_neighbor_up", "bgp_peer_down", "bgp_peer_up",
            "lldp_neighbor", "hsrp_state_change", "config_change", "cpu_high",
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
        return ts.strftime("%Y %b %d %H:%M:%S.%f")[:-3]

    def _gen_interface_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", self.rng.choice(device.interfaces).name if device.interfaces else "Ethernet1/1")
        content = f"{self._ts(ts)} {device.hostname} %ETH_PORT_CHANNEL-5-IF_DOWN_NONE: Interface {iface} is down (None)"
        return [self._make_event(device, ts, Severity.NOTICE, content, "%ETH_PORT_CHANNEL-5-IF_DOWN_NONE",
                                 attributes={"network.interface.name": iface})]

    def _gen_interface_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", self.rng.choice(device.interfaces).name if device.interfaces else "Ethernet1/1")
        content = f"{self._ts(ts)} {device.hostname} %ETH_PORT_CHANNEL-5-IF_UP: Interface {iface} is up"
        return [self._make_event(device, ts, Severity.NOTICE, content, "%ETH_PORT_CHANNEL-5-IF_UP",
                                 attributes={"network.interface.name": iface})]

    def _gen_vpc_peer_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        domain = params.get("domain", 1)
        peer_ip = params.get("peer_ip", "10.0.0.2")
        content = (f"{self._ts(ts)} {device.hostname} %VPC-2-PEER_KEEP_ALIVE_RECV_FAIL: "
                   f"vPC keep-alive receive failed for peer {peer_ip} in domain {domain}")
        return [self._make_event(device, ts, Severity.CRITICAL, content, "%VPC-2-PEER_KEEP_ALIVE_RECV_FAIL",
                                 attributes={"network.vpc.domain": str(domain), "network.vpc.peer_ip": peer_ip})]

    def _gen_vpc_peer_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        domain = params.get("domain", 1)
        content = (f"{self._ts(ts)} {device.hostname} %VPC-2-PEER_KEEP_ALIVE_RECV_SUCCESS: "
                   f"vPC keep-alive for domain {domain} - peer is alive")
        return [self._make_event(device, ts, Severity.CRITICAL, content, "%VPC-2-PEER_KEEP_ALIVE_RECV_SUCCESS")]

    def _gen_vpc_consistency_check(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        vpc_id = params.get("vpc_id", 10)
        status = params.get("status", "failed")
        reason = params.get("reason", "STP Mode inconsistency")
        content = (f"{self._ts(ts)} {device.hostname} %VPC-2-CONSISTENCY_CHECK_FAILURE: "
                   f"vPC {vpc_id} consistency check {status}: {reason}")
        return [self._make_event(device, ts, Severity.CRITICAL, content, "%VPC-2-CONSISTENCY_CHECK_FAILURE")]

    def _gen_fex_online(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        fex_id = params.get("fex_id", self.rng.randint(100, 199))
        content = (f"{self._ts(ts)} {device.hostname} %FEX-5-FEX_ONLINE: "
                   f"Fex-{fex_id} is online")
        return [self._make_event(device, ts, Severity.NOTICE, content, "%FEX-5-FEX_ONLINE")]

    def _gen_fex_offline(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        fex_id = params.get("fex_id", self.rng.randint(100, 199))
        content = (f"{self._ts(ts)} {device.hostname} %FEX-2-FEX_OFFLINE: "
                   f"Fex-{fex_id} is offline")
        return [self._make_event(device, ts, Severity.CRITICAL, content, "%FEX-2-FEX_OFFLINE")]

    def _gen_ospf_neighbor_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        nbr = params.get("neighbor_id", "10.0.0.2")
        iface = params.get("interface", "Ethernet1/1")
        reason = params.get("reason", "Dead timer expired")
        content = (f"{self._ts(ts)} {device.hostname} %OSPF-5-ADJCHANGE: "
                   f"ospf-1 [1234] Area 0.0.0.0: adj with {nbr} on {iface} went down ({reason})")
        return [self._make_event(device, ts, Severity.NOTICE, content, "%OSPF-5-ADJCHANGE",
                                 attributes={"network.ospf.neighbor_id": nbr, "network.interface.name": iface})]

    def _gen_ospf_neighbor_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        nbr = params.get("neighbor_id", "10.0.0.2")
        iface = params.get("interface", "Ethernet1/1")
        content = (f"{self._ts(ts)} {device.hostname} %OSPF-5-ADJCHANGE: "
                   f"ospf-1 [1234] Area 0.0.0.0: adj with {nbr} on {iface} is FULL")
        return [self._make_event(device, ts, Severity.NOTICE, content, "%OSPF-5-ADJCHANGE")]

    def _gen_bgp_peer_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", "10.0.0.2")
        reason = params.get("reason", "Hold Timer Expired")
        content = (f"{self._ts(ts)} {device.hostname} %BGP-5-ADJCHANGE: "
                   f"neighbor {peer} Down - {reason}")
        return [self._make_event(device, ts, Severity.NOTICE, content, "%BGP-5-ADJCHANGE",
                                 attributes={"network.bgp.peer_ip": peer})]

    def _gen_bgp_peer_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", "10.0.0.2")
        content = (f"{self._ts(ts)} {device.hostname} %BGP-5-ADJCHANGE: "
                   f"neighbor {peer} Up")
        return [self._make_event(device, ts, Severity.NOTICE, content, "%BGP-5-ADJCHANGE")]

    def _gen_lldp_neighbor(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = self.rng.choice(device.interfaces).name if device.interfaces else "Ethernet1/1"
        peer = f"peer-{self.rng.randint(1, 50)}"
        content = (f"{self._ts(ts)} {device.hostname} %LLDP-5-LLDP_NEIGHBOR_ADDED: "
                   f"LLDP neighbor {peer} added on interface {iface}")
        return [self._make_event(device, ts, Severity.NOTICE, content, "%LLDP-5-LLDP_NEIGHBOR_ADDED")]

    def _gen_hsrp_state_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        grp = params.get("group", 1)
        old_state = params.get("old_state", "Standby")
        new_state = params.get("new_state", "Active")
        content = (f"{self._ts(ts)} {device.hostname} %HSRP-5-STATECHANGE: "
                   f"HSRP group {grp} state change from {old_state} to {new_state}")
        return [self._make_event(device, ts, Severity.NOTICE, content, "%HSRP-5-STATECHANGE")]

    def _gen_config_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        content = (f"{self._ts(ts)} {device.hostname} %VSHD-5-VSHD_SYSLOG_CONFIG_I: "
                   f"Configured from vty by {user} on console0")
        return [self._make_event(device, ts, Severity.NOTICE, content, "%VSHD-5-VSHD_SYSLOG_CONFIG_I")]

    def _gen_cpu_high(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        cpu = params.get("cpu_percent", self.rng.randint(80, 99))
        content = (f"{self._ts(ts)} {device.hostname} %SYSMGR-3-CPUHOG: "
                   f"Module 1 CPU utilization at {cpu}% — threshold 75%")
        return [self._make_event(device, ts, Severity.ERROR, content, "%SYSMGR-3-CPUHOG")]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        choices = [
            (f"%LLDP-5-LLDP_NEIGHBOR_ADDED: LLDP neighbor dev-{self.rng.randint(1,50)} "
             f"added on interface Ethernet1/{self.rng.randint(1,48)}", Severity.NOTICE),
            (f"%ETHPORT-5-IF_UP: Interface Ethernet1/{self.rng.randint(1,48)} is up", Severity.NOTICE),
            (f"%VPC-5-VPC_PEER_ALIVE: vPC peer-alive for domain 1", Severity.NOTICE),
            (f"%ACLLOG-5-ACLLOG_FLOW_INTERVAL: Src 10.{self.rng.randint(0,255)}.{self.rng.randint(1,254)}.{self.rng.randint(1,254)} "
             f"Dst 10.{self.rng.randint(0,255)}.{self.rng.randint(1,254)}.{self.rng.randint(1,254)}", Severity.NOTICE),
        ]
        msg, sev = self.rng.choice(choices)
        content = f"{self._ts(ts)} {device.hostname} {msg}"
        return [self._make_event(device, ts, sev, content, msg.split(":")[0].strip())]
