"""Juniper Junos syslog generator — structured syslog (RFC 5424).

Generates Junos-specific structured data elements.
Covers FR-206.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor


@register_vendor
class JuniperVendor(BaseVendor):
    vendor_type = VendorType.JUNIPER

    def supported_event_types(self) -> list[str]:
        return [
            "interface_down", "interface_up", "ospf_neighbor_down", "ospf_neighbor_up",
            "bgp_peer_down", "bgp_peer_up", "rpd_bgp_neighbor",
            "chassis_alarm", "config_change", "login_failed", "flow_session",
            "idp_attack", "screen_attack",
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

    def _gen_interface_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "ge-0/0/0")
        content = (f"{self._ts(ts)} {device.hostname} rpd[{self.rng.randint(1000,9999)}]: "
                   f"SNMP_TRAP_LINK_DOWN: ifIndex {self.rng.randint(500,600)}, "
                   f"ifAdminStatus up(1), ifOperStatus down(2), ifName {iface}")
        return [self._make_event(device, ts, Severity.WARNING, content, "SNMP_TRAP_LINK_DOWN",
                                 log_source="juniper.rpd",
                                 attributes={"network.interface.name": iface})]

    def _gen_interface_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "ge-0/0/0")
        content = (f"{self._ts(ts)} {device.hostname} rpd[{self.rng.randint(1000,9999)}]: "
                   f"SNMP_TRAP_LINK_UP: ifIndex {self.rng.randint(500,600)}, "
                   f"ifAdminStatus up(1), ifOperStatus up(1), ifName {iface}")
        return [self._make_event(device, ts, Severity.NOTICE, content, "SNMP_TRAP_LINK_UP",
                                 log_source="juniper.rpd")]

    def _gen_ospf_neighbor_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        nbr = params.get("neighbor_id", "10.0.0.2")
        iface = params.get("interface", "ge-0/0/0.0")
        content = (f"{self._ts(ts)} {device.hostname} rpd[{self.rng.randint(1000,9999)}]: "
                   f"RPD_OSPF_NBRDOWN: OSPF neighbor {nbr} ({iface} area 0.0.0.0) state changed from Full to Down due to InactivityTimer")
        return [self._make_event(device, ts, Severity.WARNING, content, "RPD_OSPF_NBRDOWN",
                                 log_source="juniper.rpd",
                                 attributes={"network.ospf.neighbor_id": nbr})]

    def _gen_ospf_neighbor_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        nbr = params.get("neighbor_id", "10.0.0.2")
        iface = params.get("interface", "ge-0/0/0.0")
        content = (f"{self._ts(ts)} {device.hostname} rpd[{self.rng.randint(1000,9999)}]: "
                   f"RPD_OSPF_NBRUP: OSPF neighbor {nbr} ({iface} area 0.0.0.0) state changed from Init to Full")
        return [self._make_event(device, ts, Severity.NOTICE, content, "RPD_OSPF_NBRUP",
                                 log_source="juniper.rpd")]

    def _gen_bgp_peer_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", "10.0.0.2")
        peer_as = params.get("peer_as", 65001)
        content = (f"{self._ts(ts)} {device.hostname} rpd[{self.rng.randint(1000,9999)}]: "
                   f"BGP_PREFIX_THRESH_EXCEEDED: {peer} (External AS {peer_as}): "
                   f"Received prefixes threshold exceeded, session reset")
        return [self._make_event(device, ts, Severity.WARNING, content, "BGP_PREFIX_THRESH_EXCEEDED",
                                 log_source="juniper.rpd",
                                 attributes={"network.bgp.peer_ip": peer, "network.bgp.peer_as": str(peer_as)})]

    def _gen_bgp_peer_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", "10.0.0.2")
        peer_as = params.get("peer_as", 65001)
        content = (f"{self._ts(ts)} {device.hostname} rpd[{self.rng.randint(1000,9999)}]: "
                   f"RPD_BGP_NEIGHBOR_STATE_CHANGED: {peer} (External AS {peer_as}): "
                   f"Old state: Active New state: Established")
        return [self._make_event(device, ts, Severity.NOTICE, content, "RPD_BGP_NEIGHBOR_STATE_CHANGED",
                                 log_source="juniper.rpd")]

    def _gen_rpd_bgp_neighbor(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_bgp_peer_down(device, ts, params)

    def _gen_chassis_alarm(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        alarm = params.get("alarm", "FPC 0 Major Errors")
        content = (f"{self._ts(ts)} {device.hostname} alarmd[{self.rng.randint(1000,9999)}]: "
                   f"Alarm set: {alarm}")
        return [self._make_event(device, ts, Severity.ALERT, content, "CHASSISD_ALARM_SET",
                                 log_source="juniper.alarmd")]

    def _gen_config_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        content = (f"{self._ts(ts)} {device.hostname} mgd[{self.rng.randint(1000,9999)}]: "
                   f"UI_COMMIT_COMPLETED: commit complete, user '{user}'")
        return [self._make_event(device, ts, Severity.INFO, content, "UI_COMMIT_COMPLETED",
                                 log_source="juniper.mgd")]

    def _gen_login_failed(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "root")
        src = params.get("src_ip", self.rng.random_ip("10.0.0.0/8"))
        content = (f"{self._ts(ts)} {device.hostname} sshd[{self.rng.randint(10000,65000)}]: "
                   f"Failed password for {user} from {src} port {self.rng.random_port()}")
        return [self._make_event(device, ts, Severity.WARNING, content, "SSHD_LOGIN_FAILED",
                                 log_source="juniper.sshd")]

    def _gen_flow_session(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        action = params.get("action", "OPEN")
        src = self.rng.random_ip("10.0.0.0/8")
        dst = self.rng.random_ip("203.0.113.0/24")
        proto = self.rng.choice(["TCP", "UDP"])
        content = (f"{self._ts(ts)} {device.hostname} RT_FLOW - RT_FLOW_SESSION_{action} "
                   f"[junos@2636.1.1.1.2.40 source-address=\"{src}\" "
                   f"destination-address=\"{dst}\" "
                   f"service-name=\"junos-https\" nat-source-address=\"{src}\" "
                   f"protocol-id=\"{6 if proto == 'TCP' else 17}\" "
                   f"source-port=\"{self.rng.random_port()}\" "
                   f"destination-port=\"{self.rng.choice([80,443,22,53])}\" "
                   f"policy-name=\"permit-all\"]")
        return [self._make_event(device, ts, Severity.INFO, content, f"RT_FLOW_SESSION_{action}",
                                 log_source="juniper.flow")]

    def _gen_idp_attack(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        attack = params.get("attack", self.rng.choice([
            "HTTP:OVERFLOW:CHUNKED-OVERFLOW", "DNS:OVERFLOW:BIND-NXT-OVERFLOW",
            "SMTP:EXPLOIT:MIME-TOO-MANY-HDRS", "SSL:AUDIT:WEAK-CIPHER",
        ]))
        src = self.rng.random_ip("198.51.100.0/24")
        dst = self.rng.random_ip("10.0.0.0/8")
        content = (f"{self._ts(ts)} {device.hostname} RT_IDP - IDP_ATTACK_LOG_EVENT: "
                   f"IDP: Attack log <{src}/{self.rng.random_port()}->{dst}/{self.rng.choice([80,443,8080])}> "
                   f"attack: {attack} action: DROP")
        return [self._make_event(device, ts, Severity.WARNING, content, "IDP_ATTACK_LOG_EVENT",
                                 log_source="juniper.idp",
                                 attributes={"network.threat.name": attack})]

    def _gen_screen_attack(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        attack = self.rng.choice(["SYN flood", "ICMP flood", "UDP flood", "land attack", "port scan"])
        src = self.rng.random_ip("198.51.100.0/24")
        content = (f"{self._ts(ts)} {device.hostname} RT_SCREEN - RT_SCREEN_TCP: "
                   f"{attack}! source: {src}, zone: untrust, interface: ge-0/0/0.0")
        return [self._make_event(device, ts, Severity.ERROR, content, "RT_SCREEN_TCP",
                                 log_source="juniper.screen")]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        choices = [
            ("flow_session", {"action": "OPEN"}),
            ("flow_session", {"action": "CLOSE"}),
            ("lldp_neighbor", {}),
            ("config_change", {"user": "automation"}),
        ]
        evt_type, evt_params = self.rng.weighted_choice(
            choices, [0.35, 0.35, 0.2, 0.1]
        )
        # For lldp_neighbor, use a simple syslog line
        if evt_type == "lldp_neighbor":
            iface = f"ge-0/0/{self.rng.randint(0,11)}"
            content = (f"{self._ts(ts)} {device.hostname} lldpd[{self.rng.randint(1000,9999)}]: "
                       f"LLDP_NEIGHBOR_UP: lldp neighbor {self.rng.choice(['switch','router'])}-"
                       f"{self.rng.randint(1,20)} up on {iface}")
            return [self._make_event(device, ts, Severity.INFO, content, "LLDP_NEIGHBOR_UP",
                                     log_source="juniper.lldpd")]
        return getattr(self, f"_gen_{evt_type}")(device, ts, evt_params)
