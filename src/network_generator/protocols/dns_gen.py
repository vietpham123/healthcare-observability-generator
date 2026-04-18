"""DNS query/response log generator.

Generates realistic DNS query logs matching common DNS server log formats
(BIND named, Windows DNS, Infoblox). Covers FR-601.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity
from netloggen.core.random_utils import SeededRandom


# Common internal domains for enterprise
_INTERNAL_DOMAINS = [
    "intranet.corp.local", "mail.corp.local", "dc01.corp.local",
    "sharepoint.corp.local", "jira.corp.local", "confluence.corp.local",
    "gitlab.corp.local", "monitoring.corp.local", "erp.corp.local",
]

_EXTERNAL_DOMAINS = [
    "www.google.com", "cdn.cloudflare.net", "api.github.com",
    "login.microsoftonline.com", "s3.amazonaws.com", "update.microsoft.com",
    "fonts.googleapis.com", "registry.npmjs.org", "pypi.org",
    "slack-edge.com", "zoom.us", "teams.microsoft.com",
]

_SUSPICIOUS_DOMAINS = [
    "c2-server.evil.example", "crypto-miner.example.xyz",
    "exfil.data-steal.io", "phishing-login.example.net",
    "dga-nxdomain-asdkjhf.com", "malware-drop.example.ru",
]

_RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "PTR", "NS", "SOA"]
_RESPONSE_CODES = ["NOERROR", "NXDOMAIN", "SERVFAIL", "REFUSED", "FORMERR"]


class DNSLogGenerator:
    """Generates DNS query/response log events."""

    def __init__(self, rng: SeededRandom | None = None) -> None:
        self.rng = rng or SeededRandom()
        self._query_id = 10000

    def generate_events(
        self,
        device: Device,
        timestamp: datetime,
        event_type: str = "dns_query",
        params: dict[str, Any] | None = None,
    ) -> list[LogEvent]:
        params = params or {}
        method = getattr(self, f"_gen_{event_type}", None)
        if method is None:
            return self._gen_dns_query(device, timestamp, params)
        return method(device, timestamp, params)

    def _next_id(self) -> int:
        self._query_id += 1
        return self._query_id

    def _gen_dns_query(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        """Standard DNS query log (BIND-style)."""
        client_ip = params.get("client_ip", self.rng.random_ip("10.0.0.0/8"))
        domain = params.get("domain", self._pick_domain(params))
        qtype = params.get("qtype", self.rng.weighted_choice(
            _RECORD_TYPES, [0.45, 0.1, 0.15, 0.05, 0.05, 0.03, 0.07, 0.05, 0.05]
        ))
        qid = self._next_id()
        rcode = self._pick_rcode(domain)

        content = (
            f"{ts.strftime('%d-%b-%Y %H:%M:%S.%f')[:-3]} "
            f"queries: info: client @0x{self.rng.randint(0x7f000000,0x7fffffff):x} "
            f"{client_ip}#{self.rng.random_port()} ({domain}): "
            f"query: {domain} IN {qtype} + ({device.management_ip})"
        )

        events = [self._make_event(device, ts, Severity.INFO, content, "DNS_QUERY",
                                   log_source="dns.named",
                                   attributes={
                                       "dns.question.name": domain,
                                       "dns.question.type": qtype,
                                       "dns.response_code": rcode,
                                       "network.client.ip": client_ip,
                                   })]

        # Generate response log
        if params.get("include_response", True):
            resp_content = self._format_response(device, ts, client_ip, domain, qtype, rcode, qid)
            events.append(self._make_event(device, ts, Severity.INFO, resp_content, "DNS_RESPONSE",
                                           log_source="dns.named"))
        return events

    def _gen_dns_nxdomain(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        """NXDOMAIN response — common in DGA malware or misconfig."""
        domain = params.get("domain", self.rng.choice(_SUSPICIOUS_DOMAINS))
        params["domain"] = domain
        return self._gen_dns_query(device, ts, params)

    def _gen_dns_servfail(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        """SERVFAIL — upstream resolver or zone issue."""
        domain = params.get("domain", self.rng.choice(_INTERNAL_DOMAINS))
        client_ip = self.rng.random_ip("10.0.0.0/8")
        content = (
            f"{ts.strftime('%d-%b-%Y %H:%M:%S.%f')[:-3]} "
            f"queries: warning: client @0x{self.rng.randint(0x7f000000,0x7fffffff):x} "
            f"{client_ip}#{self.rng.random_port()} ({domain}): "
            f"query failed (SERVFAIL) for {domain}/IN/A: "
            f"all upstream nameservers unreachable"
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "DNS_SERVFAIL",
                                 log_source="dns.named",
                                 attributes={"dns.question.name": domain, "dns.response_code": "SERVFAIL"})]

    def _gen_dns_zone_transfer(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        """Suspicious zone transfer attempt (AXFR)."""
        client_ip = params.get("client_ip", self.rng.random_ip("198.51.100.0/24"))
        zone = params.get("zone", "corp.local")
        content = (
            f"{ts.strftime('%d-%b-%Y %H:%M:%S.%f')[:-3]} "
            f"xfer-out: warning: client @0x{self.rng.randint(0x7f000000,0x7fffffff):x} "
            f"{client_ip}#{self.rng.random_port()}: zone transfer '{zone}/IN' denied"
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "DNS_AXFR_DENIED",
                                 log_source="dns.named",
                                 attributes={"dns.question.name": zone})]

    def _gen_dns_tunneling(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        """DNS tunneling detection — long subdomain queries."""
        base = self.rng.choice(["tunnel.evil.example", "c2.malware.io"])
        # Generate long random subdomain typical of DNS tunneling
        subdomain = "".join(self.rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(60))
        domain = f"{subdomain}.{base}"
        client_ip = self.rng.random_ip("10.0.0.0/8")
        content = (
            f"{ts.strftime('%d-%b-%Y %H:%M:%S.%f')[:-3]} "
            f"queries: info: client @0x{self.rng.randint(0x7f000000,0x7fffffff):x} "
            f"{client_ip}#{self.rng.random_port()} ({domain}): "
            f"query: {domain} IN TXT + ({device.management_ip})"
        )
        return [self._make_event(device, ts, Severity.WARNING, content, "DNS_TUNNEL_SUSPECT",
                                 log_source="dns.named",
                                 attributes={
                                     "dns.question.name": domain,
                                     "dns.question.type": "TXT",
                                     "network.threat.name": "DNS Tunneling",
                                 })]

    # ── helpers ────────────────────────────────────────────────────────

    def _pick_domain(self, params: dict) -> str:
        category = params.get("category", "normal")
        if category == "suspicious":
            return self.rng.choice(_SUSPICIOUS_DOMAINS)
        pool = _INTERNAL_DOMAINS + _EXTERNAL_DOMAINS
        return self.rng.choice(pool)

    def _pick_rcode(self, domain: str) -> str:
        if any(d in domain for d in ["evil", "malware", "dga", "exfil", "phish"]):
            return self.rng.weighted_choice(
                _RESPONSE_CODES, [0.2, 0.5, 0.15, 0.1, 0.05]
            )
        return self.rng.weighted_choice(
            _RESPONSE_CODES, [0.92, 0.04, 0.02, 0.01, 0.01]
        )

    def _format_response(self, device: Device, ts: datetime, client_ip: str,
                         domain: str, qtype: str, rcode: str, qid: int) -> str:
        if rcode == "NOERROR":
            if qtype == "A":
                answer = self.rng.random_ip("10.0.0.0/8") if "corp" in domain else self.rng.random_ip("203.0.113.0/24")
            elif qtype == "AAAA":
                answer = "2001:db8::1"
            elif qtype == "CNAME":
                answer = f"cdn.{domain}"
            else:
                answer = f"response-data-for-{qtype}"
        else:
            answer = rcode

        return (
            f"{ts.strftime('%d-%b-%Y %H:%M:%S.%f')[:-3]} "
            f"queries: info: client @0x{self.rng.randint(0x7f000000,0x7fffffff):x} "
            f"{client_ip}#{self.rng.random_port()}: "
            f"query response: {domain} IN {qtype} {rcode} {answer}"
        )

    def _make_event(self, device: Device, ts: datetime, severity: Severity,
                    content: str, event_type: str, log_source: str = "dns",
                    attributes: dict[str, str] | None = None) -> LogEvent:
        return LogEvent(
            timestamp=ts,
            device=device.hostname,
            vendor=device.vendor,
            severity=severity,
            facility=20,  # local4
            event_type=event_type,
            content=content,
            log_source=log_source,
            attributes=attributes or {},
        )
