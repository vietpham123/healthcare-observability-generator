"""Citrix ADC (NetScaler) log generator.

Generates Citrix ADC syslog matching NSLOG and SYSLOG audit format:
  TIMESTAMP hostname : EVENT_TYPE ... : message details
Covers FR-213.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor


@register_vendor
class CitrixVendor(BaseVendor):
    vendor_type = VendorType.CITRIX

    def supported_event_types(self) -> list[str]:
        return [
            "lb_vserver_up", "lb_vserver_down",
            "service_up", "service_down",
            "ssl_handshake_success", "ssl_handshake_failure",
            "appfw_violation", "appfw_xss", "appfw_sqli",
            "gslb_site_up", "gslb_site_down",
            "ha_failover", "config_change",
            "auth_failure",
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
        return ts.strftime("%m/%d/%Y:%H:%M:%S")

    # ── Load Balancing VServer ─────────────────────────────────────────

    def _gen_lb_vserver_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        vs = params.get("vserver", "vs_web_443")
        vip = params.get("vip", "10.0.1.100")
        content = (f"{self._ts(ts)}  {device.hostname} : EVENT DEVICEUP "
                   f"{vip}:{params.get('port',443)} - Vserver {vs} - "
                   f"State UP - Effective state UP")
        return [self._make_event(device, ts, Severity.NOTICE, content, "DEVICEUP",
                                 log_source="citrix.ns",
                                 attributes={"citrix.vserver": vs})]

    def _gen_lb_vserver_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        vs = params.get("vserver", "vs_web_443")
        vip = params.get("vip", "10.0.1.100")
        content = (f"{self._ts(ts)}  {device.hostname} : EVENT DEVICEDOWN "
                   f"{vip}:{params.get('port',443)} - Vserver {vs} - "
                   f"State DOWN - All services are down")
        return [self._make_event(device, ts, Severity.ERROR, content, "DEVICEDOWN",
                                 log_source="citrix.ns")]

    # ── Backend service ────────────────────────────────────────────────

    def _gen_service_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        svc = params.get("service", f"svc_web_{self.rng.randint(1,10)}")
        ip = params.get("ip", self.rng.random_ip("10.0.1.0/24"))
        content = (f"{self._ts(ts)}  {device.hostname} : EVENT MONITORUP "
                   f"{ip}:443 - Service {svc} - State UP - "
                   f"Monitor http-ecv: UP")
        return [self._make_event(device, ts, Severity.NOTICE, content, "MONITORUP",
                                 log_source="citrix.ns")]

    def _gen_service_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        svc = params.get("service", f"svc_web_{self.rng.randint(1,10)}")
        ip = params.get("ip", self.rng.random_ip("10.0.1.0/24"))
        content = (f"{self._ts(ts)}  {device.hostname} : EVENT MONITORDOWN "
                   f"{ip}:443 - Service {svc} - State DOWN - "
                   f"Monitor http-ecv: DOWN - Last response: Timeout")
        return [self._make_event(device, ts, Severity.WARNING, content, "MONITORDOWN",
                                 log_source="citrix.ns")]

    # ── SSL ────────────────────────────────────────────────────────────

    def _gen_ssl_handshake_success(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src = self.rng.random_ip("10.0.0.0/8")
        cipher = self.rng.choice(["TLS1.3-AES256-GCM-SHA384", "TLS1.2-ECDHE-RSA-AES256-GCM-SHA384"])
        content = (f"{self._ts(ts)}  {device.hostname} : SSLLOG SSL_HANDSHAKE_SUCCESS "
                   f"ClientIP {src} - ClientPort {self.rng.random_port()} - "
                   f"VserverServiceIP 10.0.1.100 - VserverServicePort 443 - "
                   f"CipherSuite \"{cipher}\"")
        return [self._make_event(device, ts, Severity.INFO, content, "SSL_HANDSHAKE_SUCCESS",
                                 log_source="citrix.ssl")]

    def _gen_ssl_handshake_failure(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src = self.rng.random_ip("198.51.100.0/24")
        reason = self.rng.choice([
            "sslv3 alert handshake failure", "certificate unknown",
            "no shared cipher", "protocol version mismatch",
        ])
        content = (f"{self._ts(ts)}  {device.hostname} : SSLLOG SSL_HANDSHAKE_FAILURE "
                   f"ClientIP {src} - ClientPort {self.rng.random_port()} - "
                   f"VserverServiceIP 10.0.1.100 - VserverServicePort 443 - "
                   f"Reason \"{reason}\"")
        return [self._make_event(device, ts, Severity.WARNING, content, "SSL_HANDSHAKE_FAILURE",
                                 log_source="citrix.ssl")]

    # ── AppFirewall ────────────────────────────────────────────────────

    def _gen_appfw_violation(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        violation = params.get("violation", self.rng.choice([
            "Buffer Overflow", "Cookie Consistency", "Content Type",
            "Start URL", "Deny URL",
        ]))
        src = self.rng.random_ip("198.51.100.0/24")
        content = (f"{self._ts(ts)}  {device.hostname} : APPFW APPFW_VIOLATION "
                   f"type=\"{violation}\" action=\"blocked\" "
                   f"src={src} profile=\"pr_web_security\"")
        return [self._make_event(device, ts, Severity.WARNING, content, "APPFW_VIOLATION",
                                 log_source="citrix.appfw")]

    def _gen_appfw_xss(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src = self.rng.random_ip("198.51.100.0/24")
        content = (f"{self._ts(ts)}  {device.hostname} : APPFW APPFW_XSS "
                   f"Cross-site scripting attempt detected "
                   f"src={src} uri=/search?q=<script> action=blocked "
                   f"profile=\"pr_web_security\"")
        return [self._make_event(device, ts, Severity.ALERT, content, "APPFW_XSS",
                                 log_source="citrix.appfw")]

    def _gen_appfw_sqli(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src = self.rng.random_ip("198.51.100.0/24")
        content = (f"{self._ts(ts)}  {device.hostname} : APPFW APPFW_SQL "
                   f"SQL injection attempt detected "
                   f"src={src} uri=/api/users?id=1' action=blocked "
                   f"profile=\"pr_web_security\"")
        return [self._make_event(device, ts, Severity.ALERT, content, "APPFW_SQL",
                                 log_source="citrix.appfw")]

    # ── GSLB ───────────────────────────────────────────────────────────

    def _gen_gslb_site_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        site = params.get("site", "dc-east")
        content = (f"{self._ts(ts)}  {device.hostname} : EVENT GSLBSITEUP "
                   f"Site {site} - State UP - MEP status: Active")
        return [self._make_event(device, ts, Severity.NOTICE, content, "GSLBSITEUP",
                                 log_source="citrix.gslb")]

    def _gen_gslb_site_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        site = params.get("site", "dc-east")
        content = (f"{self._ts(ts)}  {device.hostname} : EVENT GSLBSITEDOWN "
                   f"Site {site} - State DOWN - MEP status: Inactive")
        return [self._make_event(device, ts, Severity.ERROR, content, "GSLBSITEDOWN",
                                 log_source="citrix.gslb")]

    # ── HA ─────────────────────────────────────────────────────────────

    def _gen_ha_failover(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        content = (f"{self._ts(ts)}  {device.hostname} : HA STATECHANGE "
                   f"Node state changed from Secondary to Primary - "
                   f"Reason: Peer heartbeat timeout after 3 missed intervals")
        return [self._make_event(device, ts, Severity.ALERT, content, "HA_STATECHANGE",
                                 log_source="citrix.ha")]

    def _gen_config_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "nsroot")
        cmd = self.rng.choice([
            "set lb vserver vs_web -lbMethod ROUNDROBIN",
            "add server web10 10.0.1.10",
            "bind lb vserver vs_web svc_web_1",
            "save ns config",
        ])
        content = (f"{self._ts(ts)}  {device.hostname} : UI CMD_EXECUTED "
                   f"User {user} - Remote_ip {self.rng.random_ip('10.0.0.0/8')} - "
                   f"Command \"{cmd}\" - Status \"Success\"")
        return [self._make_event(device, ts, Severity.INFO, content, "CMD_EXECUTED",
                                 log_source="citrix.ns")]

    def _gen_auth_failure(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "nsroot")
        src = self.rng.random_ip("198.51.100.0/24")
        content = (f"{self._ts(ts)}  {device.hostname} : UI LOGIN_FAILURE "
                   f"User {user} - Remote_ip {src} - "
                   f"Failure_reason \"Invalid credentials\"")
        return [self._make_event(device, ts, Severity.WARNING, content, "LOGIN_FAILURE",
                                 log_source="citrix.ns")]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        choices = [
            "ssl_handshake_success", "lb_vserver_up", "service_up",
            "config_change", "ssl_handshake_success",
        ]
        weights = [0.35, 0.15, 0.15, 0.1, 0.25]
        evt = self.rng.weighted_choice(choices, weights)
        return getattr(self, f"_gen_{evt}")(device, ts, params)
