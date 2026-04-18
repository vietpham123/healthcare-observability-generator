"""Cisco IOS / IOS-XE syslog generator.

Generates logs matching the Cisco IOS format:
  *timestamp: %FACILITY-SEVERITY-MNEMONIC: message

Examples from real devices:
  *Apr 14 10:23:45.123: %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down
  *Apr 14 10:23:45.123: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/1, changed state to down
  *Apr 14 10:24:25.456: %OSPF-5-ADJCHG: Process 1, Nbr 10.0.0.2 on GigabitEthernet0/1 from FULL to DOWN, Neighbor Down: Dead timer expired
  *Apr 14 10:23:00.000: %SYS-5-CONFIG_I: Configured from console by admin on vty0 (10.1.1.100)
  *Apr 14 10:23:45.123: %BGP-5-NBR_RESET: Neighbor 10.0.0.2 reset (peer not configured)
  *Apr 14 10:23:45.123: %STP-6-PORT_STATE: Port GigabitEthernet0/1 instance 1 moving from forwarding to blocking
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor

# Cisco IOS severity mapping: 0=emergencies, ..., 7=debugging
_SEVERITY_MAP = {
    Severity.EMERGENCY: 0,
    Severity.ALERT: 1,
    Severity.CRITICAL: 2,
    Severity.ERROR: 3,
    Severity.WARNING: 4,
    Severity.NOTICE: 5,
    Severity.INFO: 6,
    Severity.DEBUG: 7,
}

_OSPF_STATES = ["DOWN", "ATTEMPT", "INIT", "2WAY", "EXSTART", "EXCHANGE", "LOADING", "FULL"]

_STP_STATES = ["disabled", "blocking", "listening", "learning", "forwarding"]

_HSRP_STATES = ["Init", "Learn", "Listen", "Speak", "Standby", "Active"]

_CDP_CAPABILITIES = ["Router", "Switch", "Host", "IGMP", "Repeater"]

_COMMON_PROTOCOLS = ["tcp", "udp", "icmp", "gre", "eigrp", "ospf"]


@register_vendor
class CiscoIOSVendor(BaseVendor):
    vendor_type = VendorType.CISCO_IOS

    def __init__(self, rng: SeededRandom):
        super().__init__(rng)

    def supported_event_types(self) -> list[str]:
        return [
            "interface_down", "interface_up",
            "lineproto_down", "lineproto_up",
            "ospf_neighbor_down", "ospf_neighbor_up",
            "bgp_peer_down", "bgp_peer_up",
            "hsrp_state_change",
            "stp_topology_change", "stp_port_state",
            "config_change",
            "cpu_high", "memory_low",
            "duplex_mismatch", "err_disable",
            "power_supply", "fan_failure",
            "cdp_neighbor",
            "acl_deny",
            "reload",
            "baseline_info",
        ]

    def generate_event(
        self, event_type: str, params: dict[str, Any], device: Device, timestamp: datetime
    ) -> list[LogEvent]:
        method = getattr(self, f"_gen_{event_type}", None)
        if method is None:
            return []
        return method(device, timestamp, params)

    def _cisco_ts(self, ts: datetime) -> str:
        return ts.strftime("*%b %d %H:%M:%S.") + f"{ts.microsecond // 1000:03d}"

    def _fmt(self, ts: datetime, facility: str, sev: int, mnemonic: str, msg: str) -> str:
        return f"{self._cisco_ts(ts)}: %{facility}-{sev}-{mnemonic}: {msg}"

    # --- Interface events ---

    def _gen_interface_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "GigabitEthernet0/1")
        reason = params.get("reason", "administratively down")
        content = self._fmt(ts, "LINK", 3, "UPDOWN", f"Interface {iface}, changed state to down")
        events = [self._make_event(
            device, ts, Severity.ERROR, content, "%LINK-3-UPDOWN",
            log_source="cisco_ios",
            attributes={
                "network.interface.name": iface,
                "network.interface.state": "down",
                "network.event.reason": reason,
            },
            scenario_id=params.get("scenario_id", ""),
        )]
        # Cisco IOS also generates LINEPROTO message
        events.extend(self._gen_lineproto_down(device, ts, params))
        return events

    def _gen_interface_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "GigabitEthernet0/1")
        content = self._fmt(ts, "LINK", 3, "UPDOWN", f"Interface {iface}, changed state to up")
        events = [self._make_event(
            device, ts, Severity.ERROR, content, "%LINK-3-UPDOWN",
            log_source="cisco_ios",
            attributes={
                "network.interface.name": iface,
                "network.interface.state": "up",
            },
            scenario_id=params.get("scenario_id", ""),
        )]
        events.extend(self._gen_lineproto_up(device, ts, params))
        return events

    def _gen_lineproto_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "GigabitEthernet0/1")
        content = self._fmt(
            ts, "LINEPROTO", 5, "UPDOWN",
            f"Line protocol on Interface {iface}, changed state to down"
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "%LINEPROTO-5-UPDOWN",
            log_source="cisco_ios",
            attributes={"network.interface.name": iface, "network.lineproto.state": "down"},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_lineproto_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "GigabitEthernet0/1")
        content = self._fmt(
            ts, "LINEPROTO", 5, "UPDOWN",
            f"Line protocol on Interface {iface}, changed state to up"
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "%LINEPROTO-5-UPDOWN",
            log_source="cisco_ios",
            attributes={"network.interface.name": iface, "network.lineproto.state": "up"},
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- OSPF events ---

    def _gen_ospf_neighbor_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        neighbor_id = params.get("neighbor_id", "10.0.0.2")
        iface = params.get("interface", "GigabitEthernet0/1")
        reason = params.get("reason", "Dead timer expired")
        process_id = params.get("process_id", 1)
        content = self._fmt(
            ts, "OSPF", 5, "ADJCHG",
            f"Process {process_id}, Nbr {neighbor_id} on {iface} from FULL to DOWN, Neighbor Down: {reason}"
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "%OSPF-5-ADJCHG",
            log_source="cisco_ios",
            attributes={
                "network.ospf.neighbor_id": neighbor_id,
                "network.ospf.interface": iface,
                "network.ospf.state": "DOWN",
                "network.ospf.reason": reason,
                "network.ospf.process_id": str(process_id),
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_ospf_neighbor_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        neighbor_id = params.get("neighbor_id", "10.0.0.2")
        iface = params.get("interface", "GigabitEthernet0/1")
        process_id = params.get("process_id", 1)
        state = params.get("state", "FULL")
        content = self._fmt(
            ts, "OSPF", 5, "ADJCHG",
            f"Process {process_id}, Nbr {neighbor_id} on {iface} from LOADING to {state}, Loading Done"
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "%OSPF-5-ADJCHG",
            log_source="cisco_ios",
            attributes={
                "network.ospf.neighbor_id": neighbor_id,
                "network.ospf.interface": iface,
                "network.ospf.state": state,
                "network.ospf.process_id": str(process_id),
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- BGP events ---

    def _gen_bgp_peer_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer_ip = params.get("peer_ip", "10.0.0.2")
        reason = params.get("reason", "Hold timer expired")
        peer_as = params.get("peer_as", "65001")
        content = self._fmt(
            ts, "BGP", 5, "NBR_RESET",
            f"Neighbor {peer_ip} reset ({reason})"
        )
        events = [self._make_event(
            device, ts, Severity.NOTICE, content, "%BGP-5-NBR_RESET",
            log_source="cisco_ios",
            attributes={
                "network.bgp.peer_ip": peer_ip,
                "network.bgp.peer_as": str(peer_as),
                "network.bgp.state": "IDLE",
                "network.bgp.reason": reason,
            },
            scenario_id=params.get("scenario_id", ""),
        )]
        # Also generate ADJCHANGE
        adj_content = self._fmt(
            ts, "BGP", 3, "NOTIFICATION",
            f"sent to neighbor {peer_ip} 4/0 (hold time expired) 0 bytes"
        )
        events.append(self._make_event(
            device, ts, Severity.ERROR, adj_content, "%BGP-3-NOTIFICATION",
            log_source="cisco_ios",
            attributes={"network.bgp.peer_ip": peer_ip, "network.bgp.notification": "hold_timer_expired"},
            scenario_id=params.get("scenario_id", ""),
        ))
        return events

    def _gen_bgp_peer_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer_ip = params.get("peer_ip", "10.0.0.2")
        peer_as = params.get("peer_as", "65001")
        content = self._fmt(
            ts, "BGP", 5, "ADJCHANGE",
            f"neighbor {peer_ip} Up"
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "%BGP-5-ADJCHANGE",
            log_source="cisco_ios",
            attributes={
                "network.bgp.peer_ip": peer_ip,
                "network.bgp.peer_as": str(peer_as),
                "network.bgp.state": "ESTABLISHED",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- HSRP ---

    def _gen_hsrp_state_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "GigabitEthernet0/1")
        group = params.get("group", 1)
        old_state = params.get("old_state", "Standby")
        new_state = params.get("new_state", "Active")
        content = self._fmt(
            ts, "HSRP", 5, "STATECHANGE",
            f"GigabitEthernet0/1 Grp {group} state {old_state} -> {new_state}"
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "%HSRP-5-STATECHANGE",
            log_source="cisco_ios",
            attributes={
                "network.hsrp.group": str(group),
                "network.hsrp.old_state": old_state,
                "network.hsrp.new_state": new_state,
                "network.interface.name": iface,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- STP ---

    def _gen_stp_topology_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        vlan = params.get("vlan", 1)
        iface = params.get("interface", "GigabitEthernet0/1")
        content = self._fmt(
            ts, "SPANTREE", 5, "TOPOTRAP",
            f"Topology Change Trap for vlan {vlan}"
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "%SPANTREE-5-TOPOTRAP",
            log_source="cisco_ios",
            attributes={"network.stp.vlan": str(vlan), "network.interface.name": iface},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_stp_port_state(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "GigabitEthernet0/1")
        instance = params.get("instance", 1)
        from_state = params.get("from_state", "forwarding")
        to_state = params.get("to_state", "blocking")
        content = self._fmt(
            ts, "STP", 6, "PORT_STATE",
            f"Port {iface} instance {instance} moving from {from_state} to {to_state}"
        )
        return [self._make_event(
            device, ts, Severity.INFO, content, "%STP-6-PORT_STATE",
            log_source="cisco_ios",
            attributes={
                "network.stp.port": iface,
                "network.stp.instance": str(instance),
                "network.stp.from_state": from_state,
                "network.stp.to_state": to_state,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- System events ---

    def _gen_config_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        source = params.get("source", "console")
        vty = params.get("vty", "vty0")
        src_ip = params.get("src_ip", "10.1.1.100")
        content = self._fmt(
            ts, "SYS", 5, "CONFIG_I",
            f"Configured from {source} by {user} on {vty} ({src_ip})"
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "%SYS-5-CONFIG_I",
            log_source="cisco_ios",
            attributes={
                "network.config.user": user,
                "network.config.source": source,
                "network.config.src_ip": src_ip,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_cpu_high(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        cpu_pct = params.get("cpu_pct", self.rng.randint(85, 99))
        process = params.get("process", "IP Input")
        content = self._fmt(
            ts, "CPU", 4, "THRESHOLD",
            f"CPU utilization has exceeded {cpu_pct}% (Process: {process})"
        )
        return [self._make_event(
            device, ts, Severity.WARNING, content, "%CPU-4-THRESHOLD",
            log_source="cisco_ios",
            attributes={"network.device.cpu_pct": str(cpu_pct), "network.device.process": process},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_memory_low(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        pool = params.get("pool", "Processor")
        free = params.get("free_bytes", self.rng.randint(1000, 50000))
        content = self._fmt(
            ts, "SYS", 2, "MALLOCFAIL",
            f"Memory allocation of 65536 bytes failed from 0x12345678, pool {pool}, free {free}"
        )
        return [self._make_event(
            device, ts, Severity.CRITICAL, content, "%SYS-2-MALLOCFAIL",
            log_source="cisco_ios",
            attributes={"network.device.memory_pool": pool, "network.device.memory_free": str(free)},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_duplex_mismatch(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "GigabitEthernet0/1")
        content = self._fmt(
            ts, "CDP", 4, "DUPLEX_MISMATCH",
            f"duplex mismatch discovered on {iface} (not half duplex), with {device.hostname} {iface} (half duplex)"
        )
        return [self._make_event(
            device, ts, Severity.WARNING, content, "%CDP-4-DUPLEX_MISMATCH",
            log_source="cisco_ios",
            attributes={"network.interface.name": iface, "network.cdp.issue": "duplex_mismatch"},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_err_disable(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "GigabitEthernet0/1")
        reason = params.get("reason", "bpduguard")
        content = self._fmt(
            ts, "PM", 4, "ERR_DISABLE",
            f"error-disable on {iface}, reason: {reason}"
        )
        return [self._make_event(
            device, ts, Severity.WARNING, content, "%PM-4-ERR_DISABLE",
            log_source="cisco_ios",
            attributes={"network.interface.name": iface, "network.err_disable.reason": reason},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_power_supply(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ps_id = params.get("ps_id", 1)
        status = params.get("status", "failed")
        content = self._fmt(
            ts, "PLATFORM_ENV", 1, "FAN",
            f"Power supply {ps_id} has {status}"
        )
        sev = Severity.ALERT if status == "failed" else Severity.NOTICE
        return [self._make_event(
            device, ts, sev, content, "%PLATFORM_ENV-1-FAN",
            log_source="cisco_ios",
            attributes={"network.device.power_supply": str(ps_id), "network.device.ps_status": status},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_fan_failure(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        fan_id = params.get("fan_id", 1)
        content = self._fmt(
            ts, "PLATFORM_ENV", 1, "FAN",
            f"Fan {fan_id} has failed"
        )
        return [self._make_event(
            device, ts, Severity.ALERT, content, "%PLATFORM_ENV-1-FAN",
            log_source="cisco_ios",
            attributes={"network.device.fan_id": str(fan_id), "network.device.fan_status": "failed"},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_cdp_neighbor(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        neighbor = params.get("neighbor", "switch-02")
        iface = params.get("interface", "GigabitEthernet0/1")
        remote_iface = params.get("remote_interface", "GigabitEthernet0/2")
        content = self._fmt(
            ts, "CDP", 6, "NBRINFO",
            f"Device {neighbor} discovered on interface {iface}, remote interface {remote_iface}"
        )
        return [self._make_event(
            device, ts, Severity.INFO, content, "%CDP-6-NBRINFO",
            log_source="cisco_ios",
            attributes={
                "network.cdp.neighbor": neighbor,
                "network.interface.name": iface,
                "network.cdp.remote_interface": remote_iface,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_acl_deny(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("198.51.100.0/24"))
        protocol = params.get("protocol", self.rng.choice(_COMMON_PROTOCOLS))
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))
        acl_name = params.get("acl_name", "OUTSIDE_IN")
        iface = params.get("interface", "GigabitEthernet0/1")
        content = self._fmt(
            ts, "SEC", 6, "IPACCESSLOGP",
            f"list {acl_name} denied {protocol} {src_ip}({src_port}) -> {dst_ip}({dst_port}), 1 packet"
        )
        return [self._make_event(
            device, ts, Severity.INFO, content, "%SEC-6-IPACCESSLOGP",
            log_source="cisco_ios",
            attributes={
                "network.acl.name": acl_name,
                "network.acl.action": "denied",
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": str(src_port),
                "dst_port": str(dst_port),
                "protocol": protocol,
                "network.interface.name": iface,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_reload(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        reason = params.get("reason", "Reload command")
        content = self._fmt(ts, "SYS", 5, "RESTART", f"System restarted -- {reason}")
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "%SYS-5-RESTART",
            log_source="cisco_ios",
            attributes={"network.device.reload_reason": reason},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        """Generate routine baseline messages that appear in normal operations."""
        msg_type = self.rng.weighted_choice(
            ["cdp", "stp_stable", "keepalive", "ntp_sync", "auth_success"],
            [0.2, 0.2, 0.3, 0.15, 0.15],
        )
        if msg_type == "cdp":
            iface = self.rng.choice([i.name for i in device.interfaces]) if device.interfaces else "GigabitEthernet0/1"
            return self._gen_cdp_neighbor(device, ts, {"interface": iface, "neighbor": f"peer-{self.rng.randint(1, 20)}"})
        elif msg_type == "stp_stable":
            content = self._fmt(ts, "STP", 6, "PORT_STATE",
                                f"Port {self.rng.choice([i.name for i in device.interfaces] or ['Gi0/1'])} instance 1 moving from listening to forwarding")
            return [self._make_event(device, ts, Severity.INFO, content, "%STP-6-PORT_STATE", log_source="cisco_ios")]
        elif msg_type == "keepalive":
            content = self._fmt(ts, "SYS", 6, "LOGGINGHOST_STARTSTOP", "Logging to host 10.1.1.10 port 514 started - CLI initiated")
            return [self._make_event(device, ts, Severity.INFO, content, "%SYS-6-LOGGINGHOST_STARTSTOP", log_source="cisco_ios")]
        elif msg_type == "ntp_sync":
            content = self._fmt(ts, "NTP", 5, "PEERSYNC", f"NTP peer {self.rng.random_ip('10.0.0.0/24')} is synchronized")
            return [self._make_event(device, ts, Severity.NOTICE, content, "%NTP-5-PEERSYNC", log_source="cisco_ios")]
        else:
            content = self._fmt(ts, "SEC_LOGIN", 5, "LOGIN_SUCCESS", f"Login Success [user: admin] [Source: 10.1.1.{self.rng.randint(1, 254)}] [localport: 22] at {self._format_iso_timestamp(ts)}")
            return [self._make_event(device, ts, Severity.NOTICE, content, "%SEC_LOGIN-5-LOGIN_SUCCESS", log_source="cisco_ios")]
