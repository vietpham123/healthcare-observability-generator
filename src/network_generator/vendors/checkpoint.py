"""Check Point syslog generator — LEA-compatible format.

Generates Check Point firewall logs in the SmartConsole / LEA syslog format:
  time=EPOCH|action=...|orig=...|...
Covers FR-208.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor


_BLADE_MAP = {
    "Firewall": "fw",
    "Application Control": "appi",
    "URL Filtering": "urlf",
    "IPS": "ips",
    "Anti-Bot": "abot",
    "Threat Emulation": "te",
    "VPN": "vpn",
}


@register_vendor
class CheckPointVendor(BaseVendor):
    vendor_type = VendorType.CHECKPOINT

    def __init__(self, rng: SeededRandom | None = None) -> None:
        super().__init__(rng)
        self._log_uid = 100000

    def supported_event_types(self) -> list[str]:
        return [
            "fw_accept", "fw_drop", "fw_reject",
            "ips_detect", "urlf_block", "appi_block",
            "vpn_tunnel_up", "vpn_tunnel_down",
            "login_failed", "config_change",
            "ha_failover",
            "baseline_info",
        ]

    def generate_event(
        self, event_type: str, params: dict[str, Any], device: Device, timestamp: datetime
    ) -> list[LogEvent]:
        method = getattr(self, f"_gen_{event_type}", None)
        if method is None:
            return []
        return method(device, timestamp, params)

    def _uid(self) -> str:
        self._log_uid += 1
        return f"{{0x{self._log_uid:08x},0x0,0x{self.rng.randint(0,0xFFFFFF):06x}}}"

    def _kv(self, **kwargs: Any) -> str:
        return "|".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)

    def _ts_epoch(self, ts: datetime) -> int:
        return int(ts.timestamp())

    # ── Firewall blade ─────────────────────────────────────────────────

    def _gen_fw_accept(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_fw(device, ts, params, "Accept")

    def _gen_fw_drop(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_fw(device, ts, params, "Drop")

    def _gen_fw_reject(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_fw(device, ts, params, "Reject")

    def _gen_fw(self, device: Device, ts: datetime, params: dict, action: str) -> list[LogEvent]:
        src = params.get("src_ip", self.rng.random_ip("10.0.0.0/8"))
        dst = params.get("dst_ip", self.rng.random_ip("203.0.113.0/24"))
        svc = params.get("service", self.rng.choice(["https", "http", "ssh", "dns", "smtp"]))
        proto = params.get("protocol", "tcp")
        rule = params.get("rule", self.rng.randint(1, 50))
        iface_in = params.get("ifdir_in", "eth1")
        iface_out = params.get("ifdir_out", "eth0")
        s_port = self.rng.random_port()
        d_port = params.get("dst_port", self.rng.choice([80, 443, 22, 53, 25]))

        content = self._kv(
            time=self._ts_epoch(ts), action=action, orig=device.management_ip,
            i_f=iface_in, o_f=iface_out,
            src=src, dst=dst, proto=proto, service=svc,
            s_port=s_port, d_port=d_port,
            rule=rule, rule_name=f"rule_{rule}",
            loguid=self._uid(), product="VPN-1 & FireWall-1",
            blade="Firewall",
        )
        sev = Severity.INFO if action == "Accept" else Severity.WARNING
        return [self._make_event(device, ts, sev, content, f"FW_{action.upper()}",
                                 log_source="checkpoint.fw",
                                 attributes={"network.rule.id": str(rule)})]

    # ── IPS blade ──────────────────────────────────────────────────────

    def _gen_ips_detect(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        attack = params.get("attack", self.rng.choice([
            "Apache Struts2 Code Execution", "SQL Injection",
            "Cross-Site Scripting", "DNS Zone Transfer",
            "SMB Buffer Overflow",
        ]))
        src = self.rng.random_ip("198.51.100.0/24")
        dst = self.rng.random_ip("10.0.0.0/8")
        confidence = self.rng.choice(["High", "Medium", "Low"])
        severity_str = self.rng.choice(["Critical", "High", "Medium"])
        content = self._kv(
            time=self._ts_epoch(ts), action="Detect", orig=device.management_ip,
            src=src, dst=dst,
            attack=attack, attack_info=f"CVE-{self.rng.randint(2018,2024)}-{self.rng.randint(1000,9999)}",
            confidence_level=confidence, severity=severity_str,
            blade="IPS", product="SmartDefense", loguid=self._uid(),
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "IPS_DETECT",
                                 log_source="checkpoint.ips",
                                 attributes={"network.threat.name": attack})]

    # ── URL Filtering ──────────────────────────────────────────────────

    def _gen_urlf_block(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        url = params.get("url", self.rng.choice([
            "http://malware-site.example.com/payload",
            "http://phishing.example.net/login",
            "http://gambling.example.org/bet",
        ]))
        category = self.rng.choice(["Malware", "Phishing", "Gambling", "Hacking"])
        src = self.rng.random_ip("10.0.0.0/8")
        content = self._kv(
            time=self._ts_epoch(ts), action="Block", orig=device.management_ip,
            src=src, resource=url, category=category,
            blade="URL Filtering", product="URL Filtering", loguid=self._uid(),
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "URLF_BLOCK",
                                 log_source="checkpoint.urlf")]

    # ── Application Control ────────────────────────────────────────────

    def _gen_appi_block(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        app = params.get("app", self.rng.choice([
            "BitTorrent", "Tor", "Skype", "TeamViewer", "Dropbox",
        ]))
        src = self.rng.random_ip("10.0.0.0/8")
        content = self._kv(
            time=self._ts_epoch(ts), action="Block", orig=device.management_ip,
            src=src, appi_name=app, risk="5",
            blade="Application Control", product="Application Control", loguid=self._uid(),
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "APPI_BLOCK",
                                 log_source="checkpoint.appi")]

    # ── VPN ────────────────────────────────────────────────────────────

    def _gen_vpn_tunnel_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", self.rng.random_ip("203.0.113.0/24"))
        content = self._kv(
            time=self._ts_epoch(ts), action="Key Install",
            orig=device.management_ip, peer_gateway=peer,
            ike="IKEv2", methods="AES-256 + SHA256",
            blade="VPN", product="VPN-1", loguid=self._uid(),
        )
        return [self._make_event(device, ts, Severity.INFO, content, "VPN_KEY_INSTALL",
                                 log_source="checkpoint.vpn")]

    def _gen_vpn_tunnel_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", self.rng.random_ip("203.0.113.0/24"))
        content = self._kv(
            time=self._ts_epoch(ts), action="Tunnel Down",
            orig=device.management_ip, peer_gateway=peer,
            reason="DPD timeout",
            blade="VPN", product="VPN-1", loguid=self._uid(),
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "VPN_TUNNEL_DOWN",
                                 log_source="checkpoint.vpn")]

    # ── Security events ────────────────────────────────────────────────

    def _gen_login_failed(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", self.rng.choice(["admin", "cpuser", "monitor"]))
        src = params.get("src_ip", self.rng.random_ip("10.0.0.0/8"))
        content = self._kv(
            time=self._ts_epoch(ts), action="Failed Log In",
            orig=device.management_ip, src=src, user=user,
            auth_method="Password",
            product="System Monitor", loguid=self._uid(),
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "LOGIN_FAILED",
                                 log_source="checkpoint.system")]

    def _gen_config_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        content = self._kv(
            time=self._ts_epoch(ts), action="Update",
            orig=device.management_ip,
            administrator=user, operation="Install Policy",
            product="SmartConsole", loguid=self._uid(),
        )
        return [self._make_event(device, ts, Severity.NOTICE, content, "CONFIG_CHANGE",
                                 log_source="checkpoint.system")]

    # ── HA ─────────────────────────────────────────────────────────────

    def _gen_ha_failover(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        new_state = params.get("state", "Active")
        content = self._kv(
            time=self._ts_epoch(ts), action="HA State Change",
            orig=device.management_ip,
            old_state="Standby", new_state=new_state,
            reason="Peer heartbeat timeout",
            product="CPHA", loguid=self._uid(),
        )
        return [self._make_event(device, ts, Severity.ALERT, content, "HA_FAILOVER",
                                 log_source="checkpoint.ha")]

    # ── Baseline ───────────────────────────────────────────────────────

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        choices = ["fw_accept", "fw_accept", "fw_accept", "fw_drop", "config_change"]
        weights = [0.4, 0.2, 0.15, 0.15, 0.1]
        evt = self.rng.weighted_choice(choices, weights)
        return getattr(self, f"_gen_{evt}")(device, ts, params)
