"""DHCP lease log generator.

Generates DHCP server log events matching ISC DHCP / Windows DHCP formats.
Supports DISCOVER, OFFER, REQUEST, ACK, NAK, RELEASE, DECLINE, EXPIRE.
Covers FR-602.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity
from netloggen.core.random_utils import SeededRandom


_HOSTNAMES = [
    "WIN-PC-{n}", "MAC-{n}", "LINUX-WS-{n}", "IP-PHONE-{n}",
    "PRINTER-{n}", "IOT-SENSOR-{n}", "CAMERA-{n}", "AP-{n}",
]


class DHCPLogGenerator:
    """Generates DHCP server log events."""

    def __init__(self, rng: SeededRandom | None = None) -> None:
        self.rng = rng or SeededRandom()
        self._lease_pool_usage = 0.0  # 0.0 to 1.0

    @property
    def pool_usage(self) -> float:
        return self._lease_pool_usage

    @pool_usage.setter
    def pool_usage(self, val: float) -> None:
        self._lease_pool_usage = max(0.0, min(1.0, val))

    def generate_events(
        self,
        device: Device,
        timestamp: datetime,
        event_type: str = "dhcp_ack",
        params: dict[str, Any] | None = None,
    ) -> list[LogEvent]:
        params = params or {}
        method = getattr(self, f"_gen_{event_type}", None)
        if method is None:
            return self._gen_dhcp_ack(device, timestamp, params)
        return method(device, timestamp, params)

    # ── DHCP message types ─────────────────────────────────────────────

    def _gen_dhcp_discover(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        mac = params.get("mac", self.rng.random_mac())
        hostname = params.get("hostname", self._random_hostname())
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} dhcpd: "
                   f"DHCPDISCOVER from {mac} ({hostname}) via eth0")
        return [self._make_event(device, ts, Severity.INFO, content, "DHCPDISCOVER",
                                 attributes={"dhcp.client.mac": mac, "dhcp.client.hostname": hostname})]

    def _gen_dhcp_offer(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ip = params.get("ip", self.rng.random_ip("10.0.2.0/24"))
        mac = params.get("mac", self.rng.random_mac())
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} dhcpd: "
                   f"DHCPOFFER on {ip} to {mac} via eth0")
        return [self._make_event(device, ts, Severity.INFO, content, "DHCPOFFER",
                                 attributes={"dhcp.assigned_ip": ip, "dhcp.client.mac": mac})]

    def _gen_dhcp_request(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ip = params.get("ip", self.rng.random_ip("10.0.2.0/24"))
        mac = params.get("mac", self.rng.random_mac())
        hostname = params.get("hostname", self._random_hostname())
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} dhcpd: "
                   f"DHCPREQUEST for {ip} from {mac} ({hostname}) via eth0")
        return [self._make_event(device, ts, Severity.INFO, content, "DHCPREQUEST",
                                 attributes={"dhcp.assigned_ip": ip, "dhcp.client.mac": mac})]

    def _gen_dhcp_ack(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ip = params.get("ip", self.rng.random_ip("10.0.2.0/24"))
        mac = params.get("mac", self.rng.random_mac())
        hostname = params.get("hostname", self._random_hostname())
        lease_time = params.get("lease_time", self.rng.choice([3600, 7200, 14400, 28800, 86400]))
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} dhcpd: "
                   f"DHCPACK on {ip} to {mac} ({hostname}) via eth0 "
                   f"lease-time {lease_time}")
        self._lease_pool_usage = min(1.0, self._lease_pool_usage + 0.001)
        return [self._make_event(device, ts, Severity.INFO, content, "DHCPACK",
                                 attributes={
                                     "dhcp.assigned_ip": ip,
                                     "dhcp.client.mac": mac,
                                     "dhcp.lease_time": str(lease_time),
                                 })]

    def _gen_dhcp_nak(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ip = params.get("ip", self.rng.random_ip("10.0.2.0/24"))
        mac = params.get("mac", self.rng.random_mac())
        reason = params.get("reason", "not in correct subnet")
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} dhcpd: "
                   f"DHCPNAK on {ip} to {mac}: {reason}")
        return [self._make_event(device, ts, Severity.WARNING, content, "DHCPNAK",
                                 attributes={"dhcp.client.mac": mac})]

    def _gen_dhcp_release(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ip = params.get("ip", self.rng.random_ip("10.0.2.0/24"))
        mac = params.get("mac", self.rng.random_mac())
        hostname = params.get("hostname", self._random_hostname())
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} dhcpd: "
                   f"DHCPRELEASE of {ip} from {mac} ({hostname}) via eth0")
        self._lease_pool_usage = max(0.0, self._lease_pool_usage - 0.001)
        return [self._make_event(device, ts, Severity.INFO, content, "DHCPRELEASE",
                                 attributes={"dhcp.assigned_ip": ip, "dhcp.client.mac": mac})]

    def _gen_dhcp_decline(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ip = params.get("ip", self.rng.random_ip("10.0.2.0/24"))
        mac = params.get("mac", self.rng.random_mac())
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} dhcpd: "
                   f"DHCPDECLINE of {ip} from {mac} via eth0: "
                   f"abandoned - address already in use (duplicate IP detected)")
        return [self._make_event(device, ts, Severity.WARNING, content, "DHCPDECLINE",
                                 attributes={"dhcp.assigned_ip": ip, "dhcp.client.mac": mac})]

    def _gen_dhcp_expire(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ip = params.get("ip", self.rng.random_ip("10.0.2.0/24"))
        mac = params.get("mac", self.rng.random_mac())
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} dhcpd: "
                   f"DHCPEXPIRE {ip} lease for {mac} expired")
        self._lease_pool_usage = max(0.0, self._lease_pool_usage - 0.001)
        return [self._make_event(device, ts, Severity.NOTICE, content, "DHCPEXPIRE",
                                 attributes={"dhcp.assigned_ip": ip})]

    def _gen_dhcp_pool_exhausted(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        subnet = params.get("subnet", "10.0.2.0/24")
        mac = params.get("mac", self.rng.random_mac())
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} dhcpd: "
                   f"DHCPDISCOVER from {mac} via eth0: "
                   f"network {subnet}: no free leases")
        self._lease_pool_usage = 1.0
        return [self._make_event(device, ts, Severity.ERROR, content, "DHCP_POOL_EXHAUSTED",
                                 attributes={"dhcp.subnet": subnet, "dhcp.client.mac": mac})]

    # ── helpers ────────────────────────────────────────────────────────

    def _random_hostname(self) -> str:
        template = self.rng.choice(_HOSTNAMES)
        return template.format(n=self.rng.randint(1, 999))

    def _make_event(self, device: Device, ts: datetime, severity: Severity,
                    content: str, event_type: str,
                    attributes: dict[str, str] | None = None) -> LogEvent:
        return LogEvent(
            timestamp=ts,
            device=device.hostname,
            vendor=device.vendor,
            severity=severity,
            facility=20,  # local4
            event_type=event_type,
            content=content,
            log_source="dhcp.dhcpd",
            attributes=attributes or {},
        )
