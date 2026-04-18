"""Cisco ASA / FTD syslog generator.

Generates logs matching Cisco ASA format:
  %ASA-level-msgid: message

Real device examples:
  %ASA-6-302013: Built inbound TCP connection 839201 for outside:192.0.2.100/54321 (192.0.2.100/54321) to inside:198.51.100.50/443 (10.0.0.50/443)
  %ASA-6-302014: Teardown TCP connection 839201 for outside:192.0.2.100/54321 to inside:198.51.100.50/443 duration 0:01:30 bytes 15234 reason: TCP FIN
  %ASA-4-106023: Deny tcp src outside:192.0.2.100/54321 dst inside:198.51.100.50/22 by access-group "OUTSIDE_IN" [0x8ed66b60, 0xf8852875]
  %ASA-1-105004: (Primary) Monitoring on interface outside waiting
  %ASA-6-113005: AAA user authentication Successful : server = 10.1.1.5 : user = admin
  %ASA-4-733100: [Scanning] drop rate-1 exceeded. Current burst rate is 200 per second, max configured rate is 100; Current average rate is 150 per second
  %ASA-5-111008: User 'admin' executed the 'write mem' command
  %ASA-2-106006: Deny inbound UDP from 192.0.2.55/53 to 198.51.100.1/1025 on interface outside
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor

# ASA message IDs for common events
_ASA_BUILT_TCP = "302013"
_ASA_BUILT_UDP = "302015"
_ASA_TEARDOWN_TCP = "302014"
_ASA_TEARDOWN_UDP = "302016"
_ASA_DENY_ACL = "106023"
_ASA_DENY_INBOUND = "106006"
_ASA_DENY_NO_CONN = "106015"
_ASA_FAILOVER_PRIMARY = "105004"
_ASA_FAILOVER_SECONDARY = "105003"
_ASA_AAA_SUCCESS = "113005"
_ASA_AAA_FAIL = "113006"
_ASA_THREAT_RATE = "733100"
_ASA_CONFIG_CMD = "111008"
_ASA_VPN_TUNNEL_UP = "752004"
_ASA_VPN_TUNNEL_DOWN = "752003"
_ASA_IKE_ESTABLISHED = "713120"
_ASA_IKE_FAILED = "713903"
_ASA_CONN_LIMIT = "201009"
_ASA_NAT_CREATE = "305011"
_ASA_NAT_TEARDOWN = "305012"
_ASA_NAT_EXHAUSTED = "305006"
_ASA_FAILOVER_ACTIVE = "105032"
_ASA_FAILOVER_STANDBY = "105033"
_ASA_VPN_USER_CONNECT = "722022"
_ASA_VPN_USER_DISCONNECT = "722023"
_ASA_FILE_EVENT = "430003"
_ASA_MALWARE_EVENT = "430004"
_ASA_IOC_EVENT = "338002"
_ASA_IPS_EVENT = "400023"

_TEARDOWN_REASONS = [
    "TCP FIN", "TCP Reset-O", "TCP Reset-I", "Conn timeout", "Idle Timeout",
    "SYN Timeout", "Flow closed by inspection", "Failover primary closed",
]

_THREAT_CATEGORIES = ["Scanning", "SYN flood", "IP fragment", "ICMP flood", "UDP flood"]

_VPN_GROUPS = ["DefaultWEBVPNGroup", "AnyConnect-Users", "Site-to-Site-VPN", "Remote-Users"]

_FILE_TYPES = ["PDF", "EXE", "DOCX", "ZIP", "DLL", "JAR", "XLSX", "JS", "PS1", "MSI"]
_FILE_DISPOSITIONS = ["Malware", "Clean", "Unknown", "Custom Detection", "Pending Analysis"]
_FILE_NAMES = [
    "invoice_Q4_2024.pdf", "setup.exe", "report_final.docx", "archive.zip",
    "vcruntime140.dll", "update.jar", "budget_2025.xlsx", "analytics.js",
    "deploy_script.ps1", "installer_v3.msi", "payload.exe", "readme.pdf",
    "contract_draft.docx", "logs_export.zip", "plugin_update.dll",
]
_MALWARE_NAMES = [
    "Trojan.Win32.Agent.gen", "Ransom.Win32.WannaCry", "Backdoor.Linux.Mirai",
    "Worm.Win32.Conficker", "Spyware.Win32.KeyLogger", "Adware.Win32.BrowserModifier",
    "Trojan.JS.Redirector", "Exploit.PDF.CVE-2024-1234", "PUP.Win32.Toolbar",
    "Rootkit.Win64.ZeroAccess",
]
_MALWARE_FAMILIES = ["Agent", "WannaCry", "Mirai", "Conficker", "KeyLogger", "Emotet", "TrickBot", "Dridex"]
_MALWARE_DISPOSITIONS = ["blocked", "detected", "allowed", "quarantined"]

_IOC_TYPES = ["ip", "domain", "url", "file_hash", "email"]
_IOC_SOURCES = ["Cisco Talos", "Threat Intelligence", "Custom Feed", "STIX/TAXII"]
_IOC_CATEGORIES = ["C2", "Malware", "Phishing", "Exploit Kit", "Botnet", "Ransomware", "Cryptomining"]
_IOC_DOMAINS = [
    "evil-domain.com", "malware-c2.net", "phishing-login.xyz", "exploit-kit.biz",
    "botnet-relay.org", "crypto-miner.ru", "data-exfil.cn",
]

_IPS_SIGNATURES = [
    ("2024001", "A Network Trojan was Detected", "critical"),
    ("2024002", "Attempted Administrator Privilege Gain", "high"),
    ("2024003", "Web Application Attack", "high"),
    ("2024004", "Potential Corporate Privacy Violation", "medium"),
    ("2024005", "Misc Attack", "low"),
    ("2024010", "Attempted Denial of Service", "critical"),
    ("2024011", "Attempted Information Leak", "medium"),
    ("2024012", "Executable Code was Detected", "high"),
    ("2024015", "Protocol Command Decode", "medium"),
    ("2024020", "Suspicious Login Attempt", "high"),
]


@register_vendor
class CiscoASAVendor(BaseVendor):
    vendor_type = VendorType.CISCO_ASA

    def __init__(self, rng: SeededRandom):
        super().__init__(rng)
        self._session_counter = rng.randint(100000, 999999)

    def supported_event_types(self) -> list[str]:
        return [
            "connection_built", "connection_teardown",
            "acl_deny", "deny_inbound",
            "failover", "failover_active", "failover_standby",
            "aaa_success", "aaa_fail",
            "threat_detected",
            "config_change",
            "vpn_tunnel_up", "vpn_tunnel_down",
            "vpn_user_connect", "vpn_user_disconnect",
            "ike_established", "ike_failed",
            "connection_limit",
            "nat_create", "nat_teardown", "nat_exhausted",
            "file_event", "malware_event", "ioc_event", "ips_event",
            "baseline_info",
        ]

    def generate_event(
        self, event_type: str, params: dict[str, Any], device: Device, timestamp: datetime
    ) -> list[LogEvent]:
        method = getattr(self, f"_gen_{event_type}", None)
        if method is None:
            return []
        return method(device, timestamp, params)

    def _next_session_id(self) -> int:
        self._session_counter += 1
        return self._session_counter

    def _asa_fmt(self, sev: int, msgid: str, msg: str) -> str:
        return f"%ASA-{sev}-{msgid}: {msg}"

    def _gen_connection_built(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("198.51.100.0/24"))
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))
        protocol = params.get("protocol", "tcp")
        src_zone = params.get("src_zone", "outside")
        dst_zone = params.get("dst_zone", "inside")
        session_id = self._next_session_id()

        msgid = _ASA_BUILT_TCP if protocol == "tcp" else _ASA_BUILT_UDP
        content = self._asa_fmt(
            6, msgid,
            f"Built inbound {protocol.upper()} connection {session_id} for "
            f"{src_zone}:{src_ip}/{src_port} ({src_ip}/{src_port}) to "
            f"{dst_zone}:{dst_ip}/{dst_port} ({dst_ip}/{dst_port})"
        )
        return [self._make_event(
            device, ts, Severity.INFO, content, f"%ASA-6-{msgid}",
            log_source="cisco_asa",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "src_port": str(src_port), "dst_port": str(dst_port),
                "protocol": protocol,
                "network.firewall.action": "built",
                "network.firewall.session_id": str(session_id),
                "network.firewall.src_zone": src_zone,
                "network.firewall.dst_zone": dst_zone,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_connection_teardown(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("198.51.100.0/24"))
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))
        protocol = params.get("protocol", "tcp")
        src_zone = params.get("src_zone", "outside")
        dst_zone = params.get("dst_zone", "inside")
        session_id = params.get("session_id", self._next_session_id())
        duration = params.get("duration", f"0:{self.rng.randint(0,59):02d}:{self.rng.randint(0,59):02d}")
        bytes_xfer = params.get("bytes", self.rng.random_bytes_count())
        reason = params.get("reason", self.rng.choice(_TEARDOWN_REASONS))

        msgid = _ASA_TEARDOWN_TCP if protocol == "tcp" else _ASA_TEARDOWN_UDP
        content = self._asa_fmt(
            6, msgid,
            f"Teardown {protocol.upper()} connection {session_id} for "
            f"{src_zone}:{src_ip}/{src_port} to {dst_zone}:{dst_ip}/{dst_port} "
            f"duration {duration} bytes {bytes_xfer} reason: {reason}"
        )
        return [self._make_event(
            device, ts, Severity.INFO, content, f"%ASA-6-{msgid}",
            log_source="cisco_asa",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "src_port": str(src_port), "dst_port": str(dst_port),
                "protocol": protocol,
                "network.firewall.action": "teardown",
                "network.firewall.session_id": str(session_id),
                "network.firewall.bytes": str(bytes_xfer),
                "network.firewall.reason": reason,
                "network.firewall.src_zone": src_zone,
                "network.firewall.dst_zone": dst_zone,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_acl_deny(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("198.51.100.0/24"))
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))
        protocol = params.get("protocol", "tcp")
        src_zone = params.get("src_zone", "outside")
        dst_zone = params.get("dst_zone", "inside")
        acl_name = params.get("acl_name", "OUTSIDE_IN")
        content = self._asa_fmt(
            4, _ASA_DENY_ACL,
            f"Deny {protocol} src {src_zone}:{src_ip}/{src_port} dst "
            f"{dst_zone}:{dst_ip}/{dst_port} by access-group \"{acl_name}\" "
            f"[0x{self.rng.randint(0, 0xFFFFFFFF):08x}, 0x{self.rng.randint(0, 0xFFFFFFFF):08x}]"
        )
        return [self._make_event(
            device, ts, Severity.WARNING, content, f"%ASA-4-{_ASA_DENY_ACL}",
            log_source="cisco_asa",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "src_port": str(src_port), "dst_port": str(dst_port),
                "protocol": protocol,
                "network.firewall.action": "deny",
                "network.firewall.acl_name": acl_name,
                "network.firewall.src_zone": src_zone,
                "network.firewall.dst_zone": dst_zone,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_deny_inbound(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("198.51.100.0/24"))
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))
        protocol = params.get("protocol", "UDP")
        iface = params.get("interface", "outside")
        content = self._asa_fmt(
            2, _ASA_DENY_INBOUND,
            f"Deny inbound {protocol} from {src_ip}/{src_port} to {dst_ip}/{dst_port} on interface {iface}"
        )
        return [self._make_event(
            device, ts, Severity.CRITICAL, content, f"%ASA-2-{_ASA_DENY_INBOUND}",
            log_source="cisco_asa",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "src_port": str(src_port), "dst_port": str(dst_port),
                "protocol": protocol,
                "network.firewall.action": "deny",
                "network.firewall.interface": iface,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_failover(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        role = params.get("role", "Primary")
        iface = params.get("interface", "outside")
        state = params.get("state", "waiting")
        msgid = _ASA_FAILOVER_PRIMARY if role == "Primary" else _ASA_FAILOVER_SECONDARY
        content = self._asa_fmt(1, msgid, f"({role}) Monitoring on interface {iface} {state}")
        return [self._make_event(
            device, ts, Severity.ALERT, content, f"%ASA-1-{msgid}",
            log_source="cisco_asa",
            attributes={
                "network.failover.role": role,
                "network.failover.interface": iface,
                "network.failover.state": state,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_aaa_success(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        server = params.get("server", "10.1.1.5")
        content = self._asa_fmt(6, _ASA_AAA_SUCCESS, f"AAA user authentication Successful : server = {server} : user = {user}")
        return [self._make_event(
            device, ts, Severity.INFO, content, f"%ASA-6-{_ASA_AAA_SUCCESS}",
            log_source="cisco_asa",
            attributes={"network.aaa.user": user, "network.aaa.server": server, "network.aaa.result": "success"},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_aaa_fail(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "unknown")
        server = params.get("server", "10.1.1.5")
        content = self._asa_fmt(6, _ASA_AAA_FAIL, f"AAA user authentication Rejected : server = {server} : user = {user}")
        return [self._make_event(
            device, ts, Severity.INFO, content, f"%ASA-6-{_ASA_AAA_FAIL}",
            log_source="cisco_asa",
            attributes={"network.aaa.user": user, "network.aaa.server": server, "network.aaa.result": "rejected"},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_threat_detected(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        category = params.get("category", self.rng.choice(_THREAT_CATEGORIES))
        current_rate = params.get("current_rate", self.rng.randint(100, 5000))
        max_rate = params.get("max_rate", 100)
        avg_rate = params.get("avg_rate", self.rng.randint(50, current_rate))
        content = self._asa_fmt(
            4, _ASA_THREAT_RATE,
            f"[{category}] drop rate-1 exceeded. Current burst rate is {current_rate} per second, "
            f"max configured rate is {max_rate}; Current average rate is {avg_rate} per second"
        )
        return [self._make_event(
            device, ts, Severity.WARNING, content, f"%ASA-4-{_ASA_THREAT_RATE}",
            log_source="cisco_asa",
            attributes={
                "network.threat.category": category,
                "network.threat.current_rate": str(current_rate),
                "network.threat.max_rate": str(max_rate),
                "network.threat.avg_rate": str(avg_rate),
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_config_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        command = params.get("command", "write mem")
        content = self._asa_fmt(5, _ASA_CONFIG_CMD, f"User '{user}' executed the '{command}' command")
        return [self._make_event(
            device, ts, Severity.NOTICE, content, f"%ASA-5-{_ASA_CONFIG_CMD}",
            log_source="cisco_asa",
            attributes={"network.config.user": user, "network.config.command": command},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_vpn_tunnel_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer_ip = params.get("peer_ip", self.rng.random_ip("203.0.113.0/24"))
        group = params.get("group", self.rng.choice(_VPN_GROUPS))
        content = self._asa_fmt(
            6, _ASA_VPN_TUNNEL_UP,
            f"Tunnel Manager dispatching a KEY_ACQUIRE message to IKEv2. Map Tag = {group}. Map Sequence Number = 1. Peer = {peer_ip}"
        )
        return [self._make_event(
            device, ts, Severity.INFO, content, f"%ASA-6-{_ASA_VPN_TUNNEL_UP}",
            log_source="cisco_asa",
            attributes={
                "network.vpn.peer_ip": peer_ip,
                "network.vpn.group": group,
                "network.vpn.state": "up",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_vpn_tunnel_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer_ip = params.get("peer_ip", self.rng.random_ip("203.0.113.0/24"))
        reason = params.get("reason", "peer not responding")
        content = self._asa_fmt(
            4, _ASA_VPN_TUNNEL_DOWN,
            f"Tunnel to {peer_ip} terminated, reason: {reason}"
        )
        return [self._make_event(
            device, ts, Severity.WARNING, content, f"%ASA-4-{_ASA_VPN_TUNNEL_DOWN}",
            log_source="cisco_asa",
            attributes={
                "network.vpn.peer_ip": peer_ip,
                "network.vpn.state": "down",
                "network.vpn.reason": reason,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_ike_established(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer_ip = params.get("peer_ip", self.rng.random_ip("203.0.113.0/24"))
        content = self._asa_fmt(
            5, _ASA_IKE_ESTABLISHED,
            f"PHASE 2 COMPLETED (msgid={self.rng.randint(1, 65535):08x}): "
            f"IPSec SA established (Tunnel) SPI: 0x{self.rng.randint(0, 0xFFFFFFFF):08x}, "
            f"Peer: {peer_ip}"
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, f"%ASA-5-{_ASA_IKE_ESTABLISHED}",
            log_source="cisco_asa",
            attributes={"network.vpn.peer_ip": peer_ip, "network.vpn.ike_phase": "2", "network.vpn.ike_state": "established"},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_ike_failed(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer_ip = params.get("peer_ip", self.rng.random_ip("203.0.113.0/24"))
        reason = params.get("reason", "Proposal failure")
        content = self._asa_fmt(
            3, _ASA_IKE_FAILED,
            f"IKE Receiver: Runt ISAKMP packet discarded on Port 500 from {peer_ip}: {reason}"
        )
        return [self._make_event(
            device, ts, Severity.ERROR, content, f"%ASA-3-{_ASA_IKE_FAILED}",
            log_source="cisco_asa",
            attributes={"network.vpn.peer_ip": peer_ip, "network.vpn.ike_state": "failed", "network.vpn.ike_reason": reason},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_connection_limit(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        current = params.get("current_conns", self.rng.randint(90000, 100000))
        limit = params.get("limit", 100000)
        content = self._asa_fmt(
            4, _ASA_CONN_LIMIT,
            f"Number of connections on the interface has reached the configured maximum "
            f"({current} of {limit} allowed)"
        )
        return [self._make_event(
            device, ts, Severity.WARNING, content, f"%ASA-4-{_ASA_CONN_LIMIT}",
            log_source="cisco_asa",
            attributes={
                "network.firewall.current_conns": str(current),
                "network.firewall.conn_limit": str(limit),
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # ── NAT translation logs (FR-305) ─────────────────────────────────

    def _gen_nat_create(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("10.0.0.0/8"))
        nat_ip = params.get("nat_ip", self.rng.random_ip("203.0.113.0/24"))
        src_port = self.rng.random_port()
        nat_port = self.rng.random_port()
        dst_ip = params.get("dst_ip", self.rng.random_ip("198.51.100.0/24"))
        dst_port = params.get("dst_port", self.rng.choice([80, 443, 22]))
        content = self._asa_fmt(
            6, _ASA_NAT_CREATE,
            f"Built dynamic TCP translation from inside:{src_ip}/{src_port} to "
            f"outside:{nat_ip}/{nat_port} dst outside:{dst_ip}/{dst_port}"
        )
        return [self._make_event(
            device, ts, Severity.INFO, content, f"%ASA-6-{_ASA_NAT_CREATE}",
            log_source="cisco_asa",
            attributes={
                "network.nat.src_ip": src_ip, "network.nat.translated_ip": nat_ip,
                "network.nat.dst_ip": dst_ip, "network.nat.action": "create",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_nat_teardown(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("10.0.0.0/8"))
        nat_ip = params.get("nat_ip", self.rng.random_ip("203.0.113.0/24"))
        duration = f"0:{self.rng.randint(0,59):02d}:{self.rng.randint(0,59):02d}"
        content = self._asa_fmt(
            6, _ASA_NAT_TEARDOWN,
            f"Teardown dynamic TCP translation from inside:{src_ip}/{self.rng.random_port()} to "
            f"outside:{nat_ip}/{self.rng.random_port()} duration {duration}"
        )
        return [self._make_event(
            device, ts, Severity.INFO, content, f"%ASA-6-{_ASA_NAT_TEARDOWN}",
            log_source="cisco_asa",
            attributes={"network.nat.action": "teardown"},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_nat_exhausted(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        pool = params.get("pool", "outside")
        content = self._asa_fmt(
            3, _ASA_NAT_EXHAUSTED,
            f"Regular translation creation failed for protocol TCP "
            f"src inside:10.0.0.0/8 dst outside:0.0.0.0/0 — "
            f"NAT pool on interface {pool} exhausted"
        )
        return [self._make_event(
            device, ts, Severity.ERROR, content, f"%ASA-3-{_ASA_NAT_EXHAUSTED}",
            log_source="cisco_asa",
            attributes={"network.nat.action": "exhausted", "network.nat.pool": pool},
            scenario_id=params.get("scenario_id", ""),
        )]

    # ── Enhanced HA failover (FR-306) ──────────────────────────────────

    def _gen_failover_active(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        reason = params.get("reason", "Other unit wants me Active")
        content = self._asa_fmt(
            1, _ASA_FAILOVER_ACTIVE,
            f"Failover unit is Active. Reason: {reason}"
        )
        return [self._make_event(
            device, ts, Severity.ALERT, content, f"%ASA-1-{_ASA_FAILOVER_ACTIVE}",
            log_source="cisco_asa",
            attributes={"network.failover.state": "active", "network.failover.reason": reason},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_failover_standby(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        reason = params.get("reason", "Other unit wants me Standby")
        content = self._asa_fmt(
            1, _ASA_FAILOVER_STANDBY,
            f"Failover unit is Standby. Reason: {reason}"
        )
        return [self._make_event(
            device, ts, Severity.ALERT, content, f"%ASA-1-{_ASA_FAILOVER_STANDBY}",
            log_source="cisco_asa",
            attributes={"network.failover.state": "standby", "network.failover.reason": reason},
            scenario_id=params.get("scenario_id", ""),
        )]

    # ── Enhanced VPN user sessions (FR-304) ────────────────────────────

    def _gen_vpn_user_connect(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", f"user{self.rng.randint(100,999)}")
        src_ip = params.get("src_ip", self.rng.random_ip("203.0.113.0/24"))
        assigned_ip = params.get("assigned_ip", self.rng.random_ip("172.16.0.0/12"))
        group = params.get("group", self.rng.choice(_VPN_GROUPS))
        content = self._asa_fmt(
            6, _ASA_VPN_USER_CONNECT,
            f"Group <{group}> User <{user}> IP <{src_ip}> "
            f"SVC Message: Session started, assigned IP {assigned_ip}"
        )
        return [self._make_event(
            device, ts, Severity.INFO, content, f"%ASA-6-{_ASA_VPN_USER_CONNECT}",
            log_source="cisco_asa",
            attributes={
                "network.vpn.user": user, "network.vpn.src_ip": src_ip,
                "network.vpn.assigned_ip": assigned_ip, "network.vpn.group": group,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_vpn_user_disconnect(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", f"user{self.rng.randint(100,999)}")
        src_ip = params.get("src_ip", self.rng.random_ip("203.0.113.0/24"))
        group = params.get("group", self.rng.choice(_VPN_GROUPS))
        duration = f"{self.rng.randint(0,23)}h {self.rng.randint(0,59)}m {self.rng.randint(0,59)}s"
        bytes_tx = self.rng.randint(1000000, 500000000)
        bytes_rx = self.rng.randint(500000, 200000000)
        content = self._asa_fmt(
            4, _ASA_VPN_USER_DISCONNECT,
            f"Group <{group}> User <{user}> IP <{src_ip}> "
            f"SVC Message: Session terminated. Duration: {duration} "
            f"Bytes xmt: {bytes_tx} Bytes rcv: {bytes_rx} "
            f"Reason: {self.rng.choice(['User Requested', 'Idle Timeout', 'Max Time Exceeded', 'Admin Reset'])}"
        )
        return [self._make_event(
            device, ts, Severity.WARNING, content, f"%ASA-4-{_ASA_VPN_USER_DISCONNECT}",
            log_source="cisco_asa",
            attributes={"network.vpn.user": user, "network.vpn.group": group},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        msg_type = self.rng.weighted_choice(
            ["conn_built", "conn_teardown", "aaa_success", "ips_event", "file_event", "malware_event", "ioc_event"],
            [0.30, 0.30, 0.15, 0.10, 0.06, 0.05, 0.04],
        )
        if msg_type == "conn_built":
            return self._gen_connection_built(device, ts, params)
        elif msg_type == "conn_teardown":
            return self._gen_connection_teardown(device, ts, params)
        elif msg_type == "aaa_success":
            return self._gen_aaa_success(device, ts, {"user": self.rng.choice(["admin", "netops", "monitor"])})
        elif msg_type == "ips_event":
            return self._gen_ips_event(device, ts, params)
        elif msg_type == "file_event":
            return self._gen_file_event(device, ts, params)
        elif msg_type == "malware_event":
            return self._gen_malware_event(device, ts, params)
        else:
            return self._gen_ioc_event(device, ts, params)

    # ── File Events (FTD File Inspection) ──────────────────────────────

    def _gen_file_event(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        file_name = params.get("file_name", self.rng.choice(_FILE_NAMES))
        file_type = params.get("file_type", file_name.rsplit(".", 1)[-1].upper() if "." in file_name else "BIN")
        file_size = params.get("file_size", self.rng.randint(1024, 52428800))
        file_hash = params.get("file_hash", f"{self.rng.randint(0, 2**128):032x}{self.rng.randint(0, 2**128):032x}")
        disposition = params.get("file_disposition", self.rng.weighted_choice(
            _FILE_DISPOSITIONS, [0.08, 0.65, 0.15, 0.05, 0.07],
        ))
        direction = params.get("direction", self.rng.choice(["download", "upload"]))
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("10.1.0.0/16"))

        content = self._asa_fmt(
            6, _ASA_FILE_EVENT,
            f"FTD File Event: file {file_name} ({file_type}, {file_size} bytes) "
            f"{direction} from {src_ip} to {dst_ip}, disposition {disposition}, SHA256 {file_hash}"
        )
        return [self._make_event(
            device, ts, Severity.WARNING if disposition == "Malware" else Severity.INFO,
            content, f"%ASA-6-{_ASA_FILE_EVENT}",
            log_source="cisco_asa",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "network.file.name": file_name,
                "network.file.type": file_type,
                "network.file.size": str(file_size),
                "network.file.sha256": file_hash,
                "network.file.disposition": disposition,
                "network.file.direction": direction,
                "network.security.event_type": "file_event",
                "network.security.severity": "high" if disposition == "Malware" else "low",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # ── Malware Events (AMP for Networks) ──────────────────────────────

    def _gen_malware_event(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        malware_name = params.get("malware_name", self.rng.choice(_MALWARE_NAMES))
        malware_family = params.get("malware_family", self.rng.choice(_MALWARE_FAMILIES))
        malware_disposition = params.get("malware_disposition", self.rng.weighted_choice(
            _MALWARE_DISPOSITIONS, [0.60, 0.25, 0.05, 0.10],
        ))
        file_name = params.get("file_name", self.rng.choice(_FILE_NAMES))
        file_hash = params.get("file_hash", f"{self.rng.randint(0, 2**128):032x}{self.rng.randint(0, 2**128):032x}")
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("10.1.0.0/16"))

        content = self._asa_fmt(
            2 if malware_disposition == "allowed" else 4, _ASA_MALWARE_EVENT,
            f"AMP Malware Event: {malware_name} ({malware_family}) detected in file {file_name} "
            f"from {src_ip} to {dst_ip}, disposition {malware_disposition}, SHA256 {file_hash}"
        )
        severity_map = {"blocked": "high", "detected": "high", "allowed": "critical", "quarantined": "medium"}
        return [self._make_event(
            device, ts, Severity.CRITICAL if malware_disposition == "allowed" else Severity.WARNING,
            content, f"%ASA-4-{_ASA_MALWARE_EVENT}",
            log_source="cisco_asa",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "network.malware.name": malware_name,
                "network.malware.family": malware_family,
                "network.malware.disposition": malware_disposition,
                "network.malware.file_name": file_name,
                "network.malware.file_hash": file_hash,
                "network.security.event_type": "malware_event",
                "network.security.severity": severity_map.get(malware_disposition, "high"),
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # ── IOC Events (Threat Intelligence) ───────────────────────────────

    def _gen_ioc_event(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ioc_type = params.get("ioc_type", self.rng.choice(_IOC_TYPES))
        if ioc_type == "ip":
            ioc_value = self.rng.random_ip("198.51.100.0/24")
        elif ioc_type == "domain":
            ioc_value = self.rng.choice(_IOC_DOMAINS)
        elif ioc_type == "url":
            ioc_value = f"http://{self.rng.choice(_IOC_DOMAINS)}/malware/{self.rng.randint(1,999)}"
        elif ioc_type == "file_hash":
            ioc_value = f"{self.rng.randint(0, 2**128):032x}{self.rng.randint(0, 2**128):032x}"
        else:
            ioc_value = f"attacker{self.rng.randint(1,99)}@{self.rng.choice(_IOC_DOMAINS)}"
        ioc_source = params.get("ioc_source", self.rng.choice(_IOC_SOURCES))
        ioc_confidence = params.get("ioc_confidence", self.rng.choice(["high", "medium", "low"]))
        ioc_category = params.get("ioc_category", self.rng.choice(_IOC_CATEGORIES))
        src_ip = params.get("src_ip", self.rng.random_ip("10.1.0.0/16"))

        content = self._asa_fmt(
            4, _ASA_IOC_EVENT,
            f"Dynamic Filter {ioc_confidence}-confidence {ioc_type} IOC matched: "
            f"{ioc_value} (source: {ioc_source}, category: {ioc_category}) from host {src_ip}"
        )
        return [self._make_event(
            device, ts, Severity.WARNING,
            content, f"%ASA-4-{_ASA_IOC_EVENT}",
            log_source="cisco_asa",
            attributes={
                "src_ip": src_ip,
                "network.ioc.type": ioc_type,
                "network.ioc.value": ioc_value,
                "network.ioc.source": ioc_source,
                "network.ioc.confidence": ioc_confidence,
                "network.ioc.category": ioc_category,
                "network.security.event_type": "ioc_event",
                "network.security.severity": "critical" if ioc_confidence == "high" else "high" if ioc_confidence == "medium" else "medium",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # ── IPS Events (Snort-based detection) ─────────────────────────────

    def _gen_ips_event(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        sig = self.rng.choice(_IPS_SIGNATURES)
        signature_id = params.get("signature_id", sig[0])
        classification = params.get("classification", sig[1])
        impact_level = params.get("impact_level", sig[2])
        action = params.get("action", self.rng.weighted_choice(["blocked", "alerted"], [0.7, 0.3]))
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("10.1.0.0/16"))
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))

        content = self._asa_fmt(
            2 if impact_level == "critical" else 4, _ASA_IPS_EVENT,
            f"IPS Event: SID {signature_id} {classification} "
            f"{src_ip}:{src_port} -> {dst_ip}:{dst_port} "
            f"Impact {impact_level}, Action {action}"
        )
        return [self._make_event(
            device, ts, Severity.CRITICAL if impact_level == "critical" else Severity.WARNING,
            content, f"%ASA-4-{_ASA_IPS_EVENT}",
            log_source="cisco_asa",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "src_port": str(src_port), "dst_port": str(dst_port),
                "network.ips.signature_id": signature_id,
                "network.ips.classification": classification,
                "network.ips.impact_level": impact_level,
                "network.ips.action": action,
                "network.security.event_type": "ips_event",
                "network.security.severity": impact_level,
                "network.security.classification": classification,
            },
            scenario_id=params.get("scenario_id", ""),
        )]
