"""Sophos XG/XGS Firewall log generator.

Generates Sophos-style key=value syslog format matching the Sophos Central format.
Covers FR-211.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor


@register_vendor
class SophosVendor(BaseVendor):
    vendor_type = VendorType.SOPHOS

    def supported_event_types(self) -> list[str]:
        return [
            "fw_allow", "fw_deny",
            "ips_detect", "web_filter_block",
            "atp_detect", "sandstorm_detect",
            "vpn_connect", "vpn_disconnect",
            "auth_success", "auth_failure",
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

    def _ts(self, ts: datetime) -> str:
        return ts.strftime("%Y-%m-%d %H:%M:%S")

    def _kv(self, **kwargs: Any) -> str:
        parts = []
        for k, v in kwargs.items():
            if v is not None:
                val = str(v)
                if " " in val or "=" in val:
                    val = f'"{val}"'
                parts.append(f"{k}={val}")
        return " ".join(parts)

    # ── Firewall ───────────────────────────────────────────────────────

    def _gen_fw_allow(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_fw(device, ts, params, "Allow")

    def _gen_fw_deny(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_fw(device, ts, params, "Deny")

    def _gen_fw(self, device: Device, ts: datetime, params: dict, action: str) -> list[LogEvent]:
        src = params.get("src_ip", self.rng.random_ip("10.0.0.0/8"))
        dst = params.get("dst_ip", self.rng.random_ip("203.0.113.0/24"))
        proto = params.get("protocol", self.rng.choice(["TCP", "UDP"]))
        service = self.rng.choice(["HTTP", "HTTPS", "DNS", "SSH", "SMTP"])
        content = self._kv(
            device_name=device.hostname,
            timestamp=self._ts(ts),
            log_id=f"{self.rng.randint(10000,99999):05d}",
            log_type="Firewall",
            log_component="Firewall Rule",
            log_subtype=action,
            status=action,
            src_ip=src,
            dst_ip=dst,
            protocol=proto,
            src_port=self.rng.random_port(),
            dst_port=params.get("dst_port", self.rng.choice([80, 443, 22, 53])),
            fw_rule_id=self.rng.randint(1, 50),
            policy_type=1,
            application=service,
            in_interface=params.get("in_iface", "Port1"),
            out_interface=params.get("out_iface", "Port2"),
            sent_bytes=self.rng.randint(100, 50000),
            recv_bytes=self.rng.randint(100, 100000),
        )
        sev = Severity.INFO if action == "Allow" else Severity.WARNING
        return [self._make_event(device, ts, sev, content, f"FW_{action.upper()}",
                                 log_source="sophos.firewall")]

    # ── IPS ────────────────────────────────────────────────────────────

    def _gen_ips_detect(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        sig = params.get("signature", self.rng.choice([
            "ET EXPLOIT Apache Log4j RCE",
            "ET SCAN Nmap SYN Scan",
            "ET TROJAN CobaltStrike Beacon",
            "GPL SHELLCODE x86 NOOP",
        ]))
        src = self.rng.random_ip("198.51.100.0/24")
        dst = self.rng.random_ip("10.0.0.0/8")
        content = self._kv(
            device_name=device.hostname, timestamp=self._ts(ts),
            log_type="IPS", log_component="Signatures",
            log_subtype="Drop",
            src_ip=src, dst_ip=dst,
            signature_id=self.rng.randint(2000000, 2999999),
            signature_msg=sig,
            classification="A Network Trojan was Detected",
            priority=1,
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "IPS_DETECT",
                                 log_source="sophos.ips",
                                 attributes={"network.threat.name": sig})]

    # ── Web Filtering ──────────────────────────────────────────────────

    def _gen_web_filter_block(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        url = self.rng.choice([
            "http://malicious.example.com/payload",
            "http://phishing-site.example.net/login",
            "http://proxy-site.example.org/",
        ])
        category = self.rng.choice(["Malware", "Phishing", "ProxyAvoidance", "Gambling"])
        src = self.rng.random_ip("10.0.0.0/8")
        content = self._kv(
            device_name=device.hostname, timestamp=self._ts(ts),
            log_type="Content Filtering", log_component="HTTP",
            log_subtype="Denied",
            src_ip=src, url=url, category=category,
            category_type="Objectionable",
            user=f"user{self.rng.randint(100,999)}",
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "WEBFILTER_BLOCK",
                                 log_source="sophos.webfilter")]

    # ── ATP / Sandstorm ────────────────────────────────────────────────

    def _gen_atp_detect(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        threat = self.rng.choice(["C2 Communication", "Botnet Activity", "Cryptominer"])
        src = self.rng.random_ip("10.0.0.0/8")
        dst = self.rng.random_ip("198.51.100.0/24")
        content = self._kv(
            device_name=device.hostname, timestamp=self._ts(ts),
            log_type="ATP", log_component="Advanced Threat",
            log_subtype="Drop",
            src_ip=src, dst_ip=dst,
            threat=threat, threatname=f"Mal/Generic-{self.rng.choice('ABCDEF')}-{self.rng.randint(1,99)}",
        )
        return [self._make_event(device, ts, Severity.ALERT, content, "ATP_DETECT",
                                 log_source="sophos.atp")]

    def _gen_sandstorm_detect(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        filename = self.rng.choice(["invoice.pdf", "update.exe", "report.docx"])
        src = self.rng.random_ip("198.51.100.0/24")
        content = self._kv(
            device_name=device.hostname, timestamp=self._ts(ts),
            log_type="Sandbox", log_component="Sandstorm",
            log_subtype="Denied",
            src_ip=src, filename=filename,
            sha256=f"{''.join(self.rng.choice('0123456789abcdef') for _ in range(64))}",
            reason="Malicious behavior detected",
        )
        return [self._make_event(device, ts, Severity.ALERT, content, "SANDSTORM_DETECT",
                                 log_source="sophos.sandstorm")]

    # ── VPN ────────────────────────────────────────────────────────────

    def _gen_vpn_connect(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", f"user{self.rng.randint(100,999)}")
        src = self.rng.random_ip("203.0.113.0/24")
        content = self._kv(
            device_name=device.hostname, timestamp=self._ts(ts),
            log_type="VPN", log_component="SSL VPN",
            log_subtype="Connected",
            user=user, src_ip=src, tunnel_ip=self.rng.random_ip("172.16.0.0/12"),
        )
        return [self._make_event(device, ts, Severity.INFO, content, "VPN_CONNECT",
                                 log_source="sophos.vpn")]

    def _gen_vpn_disconnect(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", f"user{self.rng.randint(100,999)}")
        content = self._kv(
            device_name=device.hostname, timestamp=self._ts(ts),
            log_type="VPN", log_component="SSL VPN",
            log_subtype="Disconnected",
            user=user, reason="Idle timeout",
            duration=self.rng.randint(300, 36000),
        )
        return [self._make_event(device, ts, Severity.INFO, content, "VPN_DISCONNECT",
                                 log_source="sophos.vpn")]

    # ── Auth ───────────────────────────────────────────────────────────

    def _gen_auth_success(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        content = self._kv(
            device_name=device.hostname, timestamp=self._ts(ts),
            log_type="Event", log_component="Authentication",
            log_subtype="Success",
            user=user, src_ip=self.rng.random_ip("10.0.0.0/8"),
            auth_mechanism="Password",
        )
        return [self._make_event(device, ts, Severity.INFO, content, "AUTH_SUCCESS",
                                 log_source="sophos.auth")]

    def _gen_auth_failure(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        content = self._kv(
            device_name=device.hostname, timestamp=self._ts(ts),
            log_type="Event", log_component="Authentication",
            log_subtype="Failure",
            user=user, src_ip=self.rng.random_ip("198.51.100.0/24"),
            auth_mechanism="Password", message="Invalid credentials",
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "AUTH_FAILURE",
                                 log_source="sophos.auth")]

    # ── HA ─────────────────────────────────────────────────────────────

    def _gen_ha_failover(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        content = self._kv(
            device_name=device.hostname, timestamp=self._ts(ts),
            log_type="Event", log_component="HA",
            log_subtype="Failover",
            message="HA failover: Transitioning from Standby to Active",
            reason="Primary heartbeat lost",
        )
        return [self._make_event(device, ts, Severity.ALERT, content, "HA_FAILOVER",
                                 log_source="sophos.ha")]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        choices = ["fw_allow", "fw_allow", "fw_deny", "auth_success", "vpn_connect"]
        weights = [0.4, 0.2, 0.15, 0.15, 0.1]
        evt = self.rng.weighted_choice(choices, weights)
        return getattr(self, f"_gen_{evt}")(device, ts, params)
