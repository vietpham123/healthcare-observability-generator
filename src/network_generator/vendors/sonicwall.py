"""SonicWall firewall log generator.

Generates SonicWall-style syslog messages with id=category m=msg n=count format.
Covers FR-212.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor


@register_vendor
class SonicWallVendor(BaseVendor):
    vendor_type = VendorType.SONICWALL

    def supported_event_types(self) -> list[str]:
        return [
            "fw_allow", "fw_deny", "fw_drop",
            "ips_detection", "gae_block",
            "vpn_tunnel_status", "vpn_sa_delete",
            "auth_success", "auth_failure",
            "system_alert", "ha_failover",
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

    def _build(self, device: Device, ts: datetime, **kv: Any) -> str:
        parts = [f"id=firewall sn={device.hostname} time=\"{self._ts(ts)}\""]
        for k, v in kv.items():
            if v is not None:
                parts.append(f"{k}={v}")
        return " ".join(parts)

    # ── Firewall ───────────────────────────────────────────────────────

    def _gen_fw_allow(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_fw(device, ts, params, "Allow", 98)

    def _gen_fw_deny(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_fw(device, ts, params, "Deny", 36)

    def _gen_fw_drop(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_fw(device, ts, params, "Drop", 27)

    def _gen_fw(self, device: Device, ts: datetime, params: dict, action: str, msg_id: int) -> list[LogEvent]:
        src = params.get("src_ip", self.rng.random_ip("10.0.0.0/8"))
        dst = params.get("dst_ip", self.rng.random_ip("203.0.113.0/24"))
        sp = self.rng.random_port()
        dp = params.get("dst_port", self.rng.choice([80, 443, 22, 53, 25]))
        proto = params.get("protocol", self.rng.choice(["tcp", "udp"]))

        content = self._build(
            device, ts,
            fw=device.management_ip,
            pri=6 if action == "Allow" else 4,
            c=msg_id, m=self.rng.randint(1, 999),
            msg=f"Connection {action.lower()}ed",
            n=self.rng.randint(1, 100),
            src=src, dst=dst,
            srcPort=sp, dstPort=dp,
            proto=f"{proto}/{dp}",
            rcvd=self.rng.randint(40, 1500),
            sent=self.rng.randint(40, 65000),
            rule=f"policy_{self.rng.randint(1,30)}",
        )
        sev = Severity.INFO if action == "Allow" else Severity.WARNING
        return [self._make_event(device, ts, sev, content, f"FW_{action.upper()}",
                                 log_source="sonicwall.fw")]

    # ── IPS ────────────────────────────────────────────────────────────

    def _gen_ips_detection(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        sig = self.rng.choice([
            "IPS Detection Alert: MALWARE-CNC",
            "IPS Detection Alert: EXPLOIT-KIT",
            "IPS Detection Alert: POLICY-VIOLATION",
        ])
        src = self.rng.random_ip("198.51.100.0/24")
        dst = self.rng.random_ip("10.0.0.0/8")
        content = self._build(
            device, ts, fw=device.management_ip, pri=2,
            c=82, m=self.rng.randint(1, 999),
            msg=sig, cat=self.rng.randint(1, 10),
            src=src, dst=dst,
            sid=self.rng.randint(1000, 9999),
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "IPS_DETECTION",
                                 log_source="sonicwall.ips")]

    # ── GAE (Geo-IP / App) ────────────────────────────────────────────

    def _gen_gae_block(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        country = self.rng.choice(["CN", "RU", "KP", "IR"])
        src = self.rng.random_ip("198.51.100.0/24")
        content = self._build(
            device, ts, fw=device.management_ip, pri=4,
            c=1154, m=88,
            msg=f"Geo-IP Filter: Connection from {country} blocked",
            src=src, srcCountry=country,
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "GAE_BLOCK",
                                 log_source="sonicwall.gae")]

    # ── VPN ────────────────────────────────────────────────────────────

    def _gen_vpn_tunnel_status(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", self.rng.random_ip("203.0.113.0/24"))
        status = params.get("status", self.rng.choice(["up", "down"]))
        content = self._build(
            device, ts, fw=device.management_ip, pri=5,
            c=519, m=self.rng.randint(1, 50),
            msg=f"IPSec tunnel {status}",
            peerGw=peer, tunnelIfName="vpn_Corp",
        )
        sev = Severity.INFO if status == "up" else Severity.WARNING
        return [self._make_event(device, ts, sev, content, "VPN_TUNNEL_STATUS",
                                 log_source="sonicwall.vpn")]

    def _gen_vpn_sa_delete(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        peer = params.get("peer_ip", self.rng.random_ip("203.0.113.0/24"))
        content = self._build(
            device, ts, fw=device.management_ip, pri=5,
            c=519, m=7,
            msg="IKE SA deleted",
            peerGw=peer, reason="DPD timeout",
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "VPN_SA_DELETE",
                                 log_source="sonicwall.vpn")]

    # ── Auth ───────────────────────────────────────────────────────────

    def _gen_auth_success(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        content = self._build(
            device, ts, fw=device.management_ip, pri=6,
            c=32, m=558,
            msg=f"Administrator login allowed",
            usr=user, src=self.rng.random_ip("10.0.0.0/8"),
        )
        return [self._make_event(device, ts, Severity.INFO, content, "AUTH_SUCCESS",
                                 log_source="sonicwall.system")]

    def _gen_auth_failure(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        src = self.rng.random_ip("198.51.100.0/24")
        content = self._build(
            device, ts, fw=device.management_ip, pri=4,
            c=32, m=557,
            msg="Administrator login denied - incorrect password",
            usr=user, src=src,
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "AUTH_FAILURE",
                                 log_source="sonicwall.system")]

    # ── System / HA ────────────────────────────────────────────────────

    def _gen_system_alert(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        alert = self.rng.choice([
            "CPU utilization exceeded threshold (90%)",
            "Memory utilization exceeded threshold (85%)",
            "License expiring in 30 days",
        ])
        content = self._build(
            device, ts, fw=device.management_ip, pri=3,
            c=2, m=self.rng.randint(1, 100),
            msg=alert,
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "SYSTEM_ALERT",
                                 log_source="sonicwall.system")]

    def _gen_ha_failover(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        content = self._build(
            device, ts, fw=device.management_ip, pri=2,
            c=48, m=1,
            msg="HA: Unit transitioning from STANDBY to ACTIVE",
            reason="Primary heartbeat timeout",
        )
        return [self._make_event(device, ts, Severity.ALERT, content, "HA_FAILOVER",
                                 log_source="sonicwall.ha")]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        choices = ["fw_allow", "fw_allow", "fw_deny", "auth_success", "vpn_tunnel_status"]
        weights = [0.4, 0.2, 0.15, 0.15, 0.1]
        evt = self.rng.weighted_choice(choices, weights)
        return getattr(self, f"_gen_{evt}")(device, ts, params)
