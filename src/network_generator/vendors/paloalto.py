"""Palo Alto Networks PAN-OS syslog generator.

Generates logs matching PAN-OS CSV syslog format for:
  TRAFFIC, THREAT, SYSTEM, CONFIG log types.

Real device examples:
  1,2026/04/14 10:23:45,001234567890,TRAFFIC,end,2816,2026/04/14 10:23:45,192.0.2.100,203.0.113.50,...
  1,2026/04/14 10:23:45,001234567890,THREAT,vulnerability,2816,2026/04/14 10:23:45,192.0.2.100,...

PAN-OS syslog CSV fields are positional and version dependent.
This implements PAN-OS 11.x format.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor

_ACTIONS = ["allow", "deny", "drop", "reset-client", "reset-server", "reset-both"]

_APPS = [
    "ssl", "web-browsing", "dns", "ssh", "smtp", "imap", "pop3", "ftp",
    "ms-office365", "youtube", "facebook", "google-base", "zoom",
    "teams", "slack", "salesforce", "aws-console", "azure-management",
    "github", "jira", "confluence", "jenkins", "docker", "kubernetes",
    "ntp", "snmp", "syslog", "icmp", "ping", "traceroute",
]

_URL_CATEGORIES = [
    "business-and-economy", "computer-and-internet-info", "educational-institutions",
    "financial-services", "government", "health-and-medicine", "news",
    "search-engines", "social-networking", "streaming-media",
    "technology", "web-advertisements", "unknown",
    "malware", "phishing", "command-and-control", "grayware",
    "hacking", "proxy-avoidance-and-anonymizers",
]

_THREAT_TYPES = [
    ("vulnerability", "CVE-2024-", "server"),
    ("spyware", "Spyware.Gen.", "client"),
    ("virus", "Virus/Win32.", "client"),
    ("wildfire", "WildFire.", "server"),
    ("flood", "Flood.", "network"),
]

_THREAT_ACTIONS = ["alert", "drop", "reset-client", "reset-server", "reset-both", "block-url", "block-ip"]

_SYSTEM_EVENT_TYPES = [
    "globalprotect", "auth", "general", "ha", "upgrade", "license", "config",
]

_GP_EVENTS = [
    "GlobalProtect gateway agent message. Login from: {ip}, User: {user}, Client OS: Windows 11",
    "GlobalProtect portal agent message. Portal address: {ip}, User: {user}, Config refresh",
    "GlobalProtect gateway agent message. Logout from: {ip}, User: {user}, Reason: user-logout",
]

_FILE_TYPES = ["PDF", "EXE", "DOCX", "ZIP", "DLL", "JAR", "XLSX", "JS", "PS1", "MSI"]
_FILE_DISPOSITIONS = ["malware", "benign", "grayware", "phishing", "unknown"]
_FILE_NAMES = [
    "invoice_Q4_2024.pdf", "setup.exe", "report_final.docx", "archive.zip",
    "vcruntime140.dll", "update.jar", "budget_2025.xlsx", "analytics.js",
    "deploy_script.ps1", "installer_v3.msi", "payload.exe", "readme.pdf",
]

_MALWARE_NAMES = [
    "Trojan.Win32.Agent.gen", "Ransom.Win32.WannaCry", "Backdoor.Linux.Mirai",
    "Worm.Win32.Conficker", "Spyware.Win32.KeyLogger",
]
_MALWARE_FAMILIES = ["Agent", "WannaCry", "Mirai", "Conficker", "KeyLogger", "Emotet", "TrickBot"]

_IOC_TYPES = ["ip", "domain", "url", "file_hash"]
_IOC_DOMAINS = [
    "evil-domain.com", "malware-c2.net", "phishing-login.xyz", "exploit-kit.biz",
    "botnet-relay.org", "crypto-miner.ru",
]
_IOC_CATEGORIES = ["C2", "Malware", "Phishing", "Exploit Kit", "Botnet", "Ransomware"]

_IPS_CLASSIFICATIONS = [
    "A Network Trojan was Detected",
    "Attempted Administrator Privilege Gain",
    "Web Application Attack",
    "Potential Corporate Privacy Violation",
    "Misc Attack",
    "Attempted Denial of Service",
    "Attempted Information Leak",
    "Executable Code was Detected",
]


@register_vendor
class PaloAltoVendor(BaseVendor):
    vendor_type = VendorType.PALOALTO

    def __init__(self, rng: SeededRandom):
        super().__init__(rng)
        self._log_id_counter = rng.randint(100000000, 999999999)

    def supported_event_types(self) -> list[str]:
        return [
            "traffic_allow", "traffic_deny", "traffic_drop", "traffic_end",
            "threat_vulnerability", "threat_spyware", "threat_virus",
            "threat_url_filtering", "threat_wildfire",
            "threat_file", "threat_ioc",
            "system_general", "system_ha", "system_globalprotect",
            "config_change",
            "baseline_info",
        ]

    _ALIASES = {
        "threat_detect": "_dispatch_threat",
        "system_event": "_gen_system_general",
        "traffic_forward": "_gen_traffic_allow",
    }

    def generate_event(
        self, event_type: str, params: dict[str, Any], device: Device, timestamp: datetime
    ) -> list[LogEvent]:
        # Check aliases first (for scenario semantic names)
        if event_type in self._ALIASES:
            method = getattr(self, self._ALIASES[event_type], None)
        else:
            method = getattr(self, f"_gen_{event_type}", None)
        if method is None:
            return []
        return method(device, timestamp, params)

    def _dispatch_threat(self, device: Device, timestamp: datetime, params: dict) -> list[LogEvent]:
        threat_type = params.get("threat_type", "vulnerability")
        method = getattr(self, f"_gen_threat_{threat_type}", self._gen_threat_vulnerability)
        return method(device, timestamp, params)

    def _next_log_id(self) -> int:
        self._log_id_counter += 1
        return self._log_id_counter

    def _pan_ts(self, ts: datetime) -> str:
        return ts.strftime("%Y/%m/%d %H:%M:%S")

    def _serial(self, device: Device) -> str:
        return device.serial_number or f"00{self.rng.randint(1000000000, 9999999999)}"

    # --- TRAFFIC logs ---

    def _gen_traffic_log(self, device: Device, ts: datetime, params: dict, action: str, subtype: str) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("10.1.0.0/16"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("203.0.113.0/24"))
        nat_src = params.get("nat_src_ip", src_ip)
        nat_dst = params.get("nat_dst_ip", dst_ip)
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))
        protocol = params.get("protocol", "tcp")
        app = params.get("application", self.rng.choice(_APPS))
        src_zone = params.get("src_zone", "trust")
        dst_zone = params.get("dst_zone", "untrust")
        rule = params.get("rule_name", "Allow-Outbound")
        session_id = params.get("session_id", self.rng.randint(100000, 999999))
        bytes_sent = params.get("bytes_sent", self.rng.random_bytes_count(500, 50000))
        bytes_recv = params.get("bytes_recv", self.rng.random_bytes_count(500, 500000))
        packets_sent = params.get("packets_sent", self.rng.randint(5, 500))
        packets_recv = params.get("packets_recv", self.rng.randint(5, 5000))
        elapsed = params.get("elapsed_seconds", self.rng.randint(1, 600))
        category = params.get("url_category", self.rng.choice(_URL_CATEGORIES[:13]))
        serial = self._serial(device)
        pan_ts = self._pan_ts(ts)
        log_id = self._next_log_id()

        # PAN-OS TRAFFIC CSV format (simplified from full 80+ field format)
        fields = [
            "1",                    # future use
            pan_ts,                 # receive_time
            serial,                 # serial
            "TRAFFIC",              # type
            subtype,                # subtype (start/end/drop/deny)
            "2816",                 # config_version
            pan_ts,                 # generated_time
            src_ip,                 # src
            dst_ip,                 # dst
            nat_src,                # natsrc
            nat_dst,                # natdst
            rule,                   # rule
            "",                     # srcuser
            "",                     # dstuser
            app,                    # application
            "vsys1",                # vsys
            src_zone,               # from
            dst_zone,               # to
            "ethernet1/1",          # inbound_if
            "ethernet1/3",          # outbound_if
            "Syslog-Forward",       # log_action
            pan_ts,                 # time_logged
            str(session_id),        # sessionid
            str(self.rng.randint(1, 100)),  # repeat_count
            str(src_port),          # sport
            str(dst_port),          # dport
            "0",                    # natsport
            "0",                    # natdport
            "0x400053",             # flags
            protocol,               # proto
            action,                 # action
            str(bytes_sent + bytes_recv),  # bytes
            str(bytes_sent),        # bytes_sent
            str(bytes_recv),        # bytes_received
            str(packets_sent + packets_recv),  # packets
            pan_ts,                 # start_time
            str(elapsed),           # elapsed
            category,               # category
            "0",                    # padding
            str(self.rng.randint(0, 999999)),  # seqno
            pan_ts,                 # action_flags
            device.hostname,        # device_name
            "from-policy",          # action_source
        ]

        content = ",".join(fields)

        return [self._make_event(
            device, ts, Severity.INFO, content, f"TRAFFIC.{subtype}",
            log_source="paloalto.traffic",
            attributes={
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": str(src_port),
                "dst_port": str(dst_port),
                "protocol": protocol,
                "network.firewall.action": action,
                "network.firewall.rule_name": rule,
                "network.firewall.application": app,
                "network.firewall.src_zone": src_zone,
                "network.firewall.dst_zone": dst_zone,
                "network.firewall.session_id": str(session_id),
                "network.firewall.bytes_sent": str(bytes_sent),
                "network.firewall.bytes_recv": str(bytes_recv),
                "network.log.type": "TRAFFIC",
                "network.log.subtype": subtype,
                "network.url.category": category,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_traffic_allow(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_traffic_log(device, ts, params, "allow", "end")

    def _gen_traffic_deny(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_traffic_log(device, ts, params, "deny", "deny")

    def _gen_traffic_drop(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_traffic_log(device, ts, params, "drop", "drop")

    def _gen_traffic_end(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_traffic_log(device, ts, params, "allow", "end")

    # --- THREAT logs ---

    def _gen_threat_log(self, device: Device, ts: datetime, params: dict, threat_type: str) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("10.1.0.0/16"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("203.0.113.0/24"))
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))
        action = params.get("action", self.rng.choice(_THREAT_ACTIONS))
        rule = params.get("rule_name", "Security-Policy")
        severity_str = params.get("threat_severity", self.rng.choice(["critical", "high", "medium", "low", "informational"]))
        serial = self._serial(device)
        pan_ts = self._pan_ts(ts)

        # Generate realistic threat name
        threat_info = next((t for t in _THREAT_TYPES if t[0] == threat_type), _THREAT_TYPES[0])
        threat_name = f"{threat_info[1]}{self.rng.randint(2020, 2026)}-{self.rng.randint(1000, 9999)}"
        threat_id = self.rng.randint(10000, 99999)
        direction = threat_info[2] if len(threat_info) > 2 else "client-to-server"

        fields = [
            "1", pan_ts, serial, "THREAT", threat_type,
            "2816", pan_ts, src_ip, dst_ip, src_ip, dst_ip,
            rule, "", "", self.rng.choice(_APPS), "vsys1",
            "trust", "untrust", "ethernet1/1", "ethernet1/3",
            "Syslog-Forward", pan_ts, str(self.rng.randint(100000, 999999)),
            "1", str(src_port), str(dst_port), "0", "0",
            "0x400053", "tcp", action, "", str(threat_id),
            threat_name, severity_str, direction,
            str(self.rng.randint(0, 999999)), pan_ts,
            device.hostname,
        ]

        content = ",".join(fields)

        # Generate IPS-style fields for vulnerability/spyware threats
        classification = self.rng.choice(_IPS_CLASSIFICATIONS) if threat_type in ("vulnerability", "spyware") else ""
        impact_level = severity_str if severity_str in ("critical", "high", "medium", "low") else "medium"

        attrs = {
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": str(src_port),
                "dst_port": str(dst_port),
                "network.firewall.action": action,
                "network.firewall.rule_name": rule,
                "network.threat.type": threat_type,
                "network.threat.name": threat_name,
                "network.threat.id": str(threat_id),
                "network.threat.severity": severity_str,
                "network.threat.direction": direction,
                "network.log.type": "THREAT",
                "network.log.subtype": threat_type,
                "network.security.event_type": f"threat_{threat_type}",
                "network.security.severity": impact_level,
        }
        if threat_type in ("vulnerability", "spyware"):
            attrs["network.ips.signature_id"] = str(threat_id)
            attrs["network.ips.classification"] = classification
            attrs["network.ips.impact_level"] = impact_level
            attrs["network.ips.action"] = action
            attrs["network.security.classification"] = classification

        return [self._make_event(
            device, ts, Severity.WARNING if severity_str in ("high", "critical") else Severity.NOTICE,
            content, f"THREAT.{threat_type}",
            log_source="paloalto.threat",
            attributes=attrs,
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_threat_vulnerability(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_threat_log(device, ts, params, "vulnerability")

    def _gen_threat_spyware(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_threat_log(device, ts, params, "spyware")

    def _gen_threat_virus(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_threat_log(device, ts, params, "virus")

    def _gen_threat_wildfire(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_threat_log(device, ts, params, "wildfire")

    def _gen_threat_url_filtering(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        url_cat = params.get("url_category", self.rng.choice(_URL_CATEGORIES))
        params["action"] = params.get("action", "block-url" if url_cat in ("malware", "phishing", "command-and-control") else "alert")
        return self._gen_threat_log(device, ts, params, "url")

    # --- SYSTEM logs ---

    def _gen_system_general(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        serial = self._serial(device)
        pan_ts = self._pan_ts(ts)
        event_id = self.rng.choice(["general", "crypto", "device-management"])
        msg = params.get("message", f"System event: {event_id} completed successfully")
        content = f"1,{pan_ts},{serial},SYSTEM,{event_id},2816,{pan_ts},{msg}"
        return [self._make_event(
            device, ts, Severity.INFO, content, f"SYSTEM.{event_id}",
            log_source="paloalto.system",
            attributes={"network.log.type": "SYSTEM", "network.log.subtype": event_id},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_system_ha(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        state = params.get("state", self.rng.choice(["active", "passive", "active-primary", "active-secondary"]))
        reason = params.get("reason", "HA state change")
        serial = self._serial(device)
        pan_ts = self._pan_ts(ts)
        msg = f"HA state changed to {state}: {reason}"
        content = f"1,{pan_ts},{serial},SYSTEM,ha,2816,{pan_ts},{msg}"
        return [self._make_event(
            device, ts, Severity.WARNING, content, "SYSTEM.ha",
            log_source="paloalto.system",
            attributes={
                "network.log.type": "SYSTEM",
                "network.log.subtype": "ha",
                "network.ha.state": state,
                "network.ha.reason": reason,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_system_globalprotect(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", f"user{self.rng.randint(1, 100)}")
        ip = params.get("client_ip", self.rng.random_ip("192.168.0.0/16"))
        serial = self._serial(device)
        pan_ts = self._pan_ts(ts)
        template = self.rng.choice(_GP_EVENTS)
        msg = template.format(ip=ip, user=user)
        content = f"1,{pan_ts},{serial},SYSTEM,globalprotect,2816,{pan_ts},{msg}"
        return [self._make_event(
            device, ts, Severity.INFO, content, "SYSTEM.globalprotect",
            log_source="paloalto.system",
            attributes={
                "network.log.type": "SYSTEM",
                "network.log.subtype": "globalprotect",
                "network.vpn.user": user,
                "network.vpn.client_ip": ip,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- CONFIG logs ---

    def _gen_config_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        cmd = params.get("command", "commit")
        client = params.get("client", "Web")
        result = params.get("result", "Succeeded")
        serial = self._serial(device)
        pan_ts = self._pan_ts(ts)
        content = f"1,{pan_ts},{serial},CONFIG,0,2816,{pan_ts},,,,0,{client},{cmd},{user},{result},,{device.hostname}"
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "CONFIG",
            log_source="paloalto.config",
            attributes={
                "network.log.type": "CONFIG",
                "network.config.user": user,
                "network.config.command": cmd,
                "network.config.client": client,
                "network.config.result": result,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        msg_type = self.rng.weighted_choice(
            ["traffic_allow", "traffic_end", "system_general", "system_globalprotect",
             "threat_vulnerability", "threat_file", "threat_ioc"],
            [0.30, 0.25, 0.12, 0.10, 0.10, 0.07, 0.06],
        )
        return getattr(self, f"_gen_{msg_type}")(device, ts, params)

    # --- FILE threat logs (WildFire file inspection) ---

    def _gen_threat_file(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("10.1.0.0/16"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("203.0.113.0/24"))
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))
        file_name = params.get("file_name", self.rng.choice(_FILE_NAMES))
        file_type = params.get("file_type", file_name.rsplit(".", 1)[-1].upper() if "." in file_name else "BIN")
        file_hash = params.get("file_hash", f"{self.rng.randint(0, 2**128):032x}{self.rng.randint(0, 2**128):032x}")
        disposition = params.get("file_disposition", self.rng.weighted_choice(
            _FILE_DISPOSITIONS, [0.08, 0.60, 0.10, 0.07, 0.15],
        ))
        action = params.get("action", "alert" if disposition == "benign" else "block-url")
        rule = params.get("rule_name", "Security-Policy")
        serial = self._serial(device)
        pan_ts = self._pan_ts(ts)

        malware_name = ""
        malware_family = ""
        if disposition == "malware":
            malware_name = self.rng.choice(_MALWARE_NAMES)
            malware_family = self.rng.choice(_MALWARE_FAMILIES)

        fields = [
            "1", pan_ts, serial, "THREAT", "file",
            "2816", pan_ts, src_ip, dst_ip, src_ip, dst_ip,
            rule, "", "", self.rng.choice(_APPS[:8]), "vsys1",
            "trust", "untrust", "ethernet1/1", "ethernet1/3",
            "Syslog-Forward", pan_ts, str(self.rng.randint(100000, 999999)),
            "1", str(src_port), str(dst_port), "0", "0",
            "0x400053", "tcp", action, file_name, "0",
            f"WildFire.{file_type}", disposition, "server-to-client",
            str(self.rng.randint(0, 999999)), pan_ts,
            device.hostname,
        ]
        content = ",".join(fields)

        attrs = {
            "src_ip": src_ip, "dst_ip": dst_ip,
            "src_port": str(src_port), "dst_port": str(dst_port),
            "network.firewall.action": action,
            "network.firewall.rule_name": rule,
            "network.file.name": file_name,
            "network.file.type": file_type,
            "network.file.sha256": file_hash,
            "network.file.disposition": disposition,
            "network.file.direction": "download",
            "network.log.type": "THREAT",
            "network.log.subtype": "file",
            "network.security.event_type": "file_event",
            "network.security.severity": "high" if disposition == "malware" else "low",
        }
        if malware_name:
            attrs["network.malware.name"] = malware_name
            attrs["network.malware.family"] = malware_family
            attrs["network.malware.disposition"] = "detected"
            attrs["network.malware.file_hash"] = file_hash
            attrs["network.malware.file_name"] = file_name
            attrs["network.security.event_type"] = "malware_event"

        return [self._make_event(
            device, ts, Severity.WARNING if disposition == "malware" else Severity.NOTICE,
            content, "THREAT.file",
            log_source="paloalto.threat",
            attributes=attrs,
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- IOC threat logs (Threat Intelligence) ---

    def _gen_threat_ioc(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_ip = params.get("src_ip", self.rng.random_ip("10.1.0.0/16"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("203.0.113.0/24"))
        ioc_type = params.get("ioc_type", self.rng.choice(_IOC_TYPES))
        if ioc_type == "ip":
            ioc_value = self.rng.random_ip("198.51.100.0/24")
        elif ioc_type == "domain":
            ioc_value = self.rng.choice(_IOC_DOMAINS)
        elif ioc_type == "url":
            ioc_value = f"http://{self.rng.choice(_IOC_DOMAINS)}/malware/{self.rng.randint(1,999)}"
        else:
            ioc_value = f"{self.rng.randint(0, 2**128):032x}{self.rng.randint(0, 2**128):032x}"
        ioc_confidence = params.get("ioc_confidence", self.rng.choice(["high", "medium", "low"]))
        ioc_category = params.get("ioc_category", self.rng.choice(_IOC_CATEGORIES))
        action = params.get("action", self.rng.choice(["block-ip", "alert", "drop"]))
        serial = self._serial(device)
        pan_ts = self._pan_ts(ts)

        fields = [
            "1", pan_ts, serial, "THREAT", "spyware",
            "2816", pan_ts, src_ip, dst_ip, src_ip, dst_ip,
            "IOC-Policy", "", "", "unknown-tcp", "vsys1",
            "trust", "untrust", "ethernet1/1", "ethernet1/3",
            "Syslog-Forward", pan_ts, str(self.rng.randint(100000, 999999)),
            "1", str(self.rng.random_port()), "443", "0", "0",
            "0x400053", "tcp", action, "", "0",
            f"IOC:{ioc_type}:{ioc_value}", ioc_confidence, "client-to-server",
            str(self.rng.randint(0, 999999)), pan_ts,
            device.hostname,
        ]
        content = ",".join(fields)

        return [self._make_event(
            device, ts, Severity.WARNING,
            content, "THREAT.spyware",
            log_source="paloalto.threat",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "network.firewall.action": action,
                "network.ioc.type": ioc_type,
                "network.ioc.value": ioc_value,
                "network.ioc.source": "WildFire Intelligence",
                "network.ioc.confidence": ioc_confidence,
                "network.ioc.category": ioc_category,
                "network.log.type": "THREAT",
                "network.log.subtype": "spyware",
                "network.security.event_type": "ioc_event",
                "network.security.severity": "critical" if ioc_confidence == "high" else "high",
            },
            scenario_id=params.get("scenario_id", ""),
        )]
