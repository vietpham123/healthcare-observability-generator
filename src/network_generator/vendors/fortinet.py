"""Fortinet FortiGate / FortiOS syslog generator.

Generates logs matching FortiOS key-value syslog format.

Real device examples:
  date=2026-04-14 time=10:23:45 devname="hq-fg-01" devid="FGT600E1234567890" logid="0000000013" type="traffic" subtype="forward" level="notice" vd="root" eventtime=1713091425 srcip=192.0.2.100 srcport=54321 srcintf="port1" srcintfrole="lan" dstip=203.0.113.50 dstport=443 dstintf="port2" dstintfrole="wan" poluuid="12345678-1234-1234-1234-123456789012" sessionid=839201 proto=6 action="accept" policyid=10 policyname="Allow-Web" policytype="policy" service="HTTPS" dstcountry="United States" srccountry="Reserved" trandisp="snat" transip=198.51.100.1 transport=54321 appid=40568 app="SSL" appcat="Network.Service" apprisk="elevated" duration=30 sentbyte=15234 rcvdbyte=482910 sentpkt=50 rcvdpkt=200 utmaction="allow"
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor

_FG_APPS = [
    ("SSL", "Network.Service", "elevated"),
    ("HTTP.BROWSER", "Web.Client", "low"),
    ("DNS", "Network.Service", "low"),
    ("HTTPS.BROWSER", "Web.Client", "elevated"),
    ("SSH", "Network.Service", "elevated"),
    ("Google.Services", "Cloud.IT", "low"),
    ("Microsoft.Office.Online", "Cloud.IT", "low"),
    ("Zoom", "Video/Audio", "low"),
    ("Slack", "Collaboration", "low"),
    ("YouTube", "Video/Audio", "medium"),
]

_FG_UTM_ACTIONS = ["allow", "block", "monitor"]

_FG_COUNTRIES = [
    "United States", "Germany", "United Kingdom", "China", "Russia",
    "France", "Japan", "India", "Brazil", "Canada", "Australia",
    "Netherlands", "Reserved",
]

_FG_IPS_ATTACKS = [
    ("HTTP.Server.Header.Buffer.Overflow", "critical", "server", "2024001", "Web Application Attack"),
    ("SSL.Anonymous.Cipher.Suites.Detected", "medium", "server", "2024002", "Misc Attack"),
    ("DNS.Query.Amplification", "high", "server", "2024003", "Attempted Denial of Service"),
    ("HTTP.URI.SQL.Injection", "high", "server", "2024004", "Web Application Attack"),
    ("SSH.Brute.Force.Login", "high", "client", "2024005", "Attempted Administrator Privilege Gain"),
    ("TCP.SYN.Flood", "critical", "network", "2024006", "Attempted Denial of Service"),
    ("HTTP.XSS.Attempt", "medium", "server", "2024007", "Web Application Attack"),
    ("SMB.Remote.Code.Execution", "critical", "server", "2024008", "A Network Trojan was Detected"),
]

_FG_WEBFILTER_CATEGORIES = [
    ("Malicious Websites", "block", 26),
    ("Phishing", "block", 61),
    ("Spam URLs", "block", 62),
    ("Pornography", "block", 5),
    ("Social Networking", "warning", 7),
    ("Streaming Media and Download", "monitor", 13),
    ("Games", "monitor", 15),
    ("Search Engines and Portals", "allow", 25),
    ("Educational Institutions", "allow", 29),
    ("Finance and Banking", "allow", 30),
]

_FG_FILE_NAMES = [
    "invoice_Q4_2024.pdf", "setup.exe", "report_final.docx", "archive.zip",
    "vcruntime140.dll", "update.jar", "budget_2025.xlsx", "analytics.js",
    "deploy_script.ps1", "installer_v3.msi", "payload.exe", "readme.pdf",
]
_FG_FILE_TYPES = ["PDF", "EXE", "DOCX", "ZIP", "DLL", "JAR", "XLSX", "JS"]
_FG_FILE_DISPOSITIONS = ["Malware", "Clean", "Unknown", "Suspicious"]
_FG_MALWARE_NAMES = [
    "W32/Trojan.1234!tr", "W32/Ransom.5678!tr", "W32/Backdoor.9012!tr",
    "W32/Worm.3456!tr", "JS/Agent.7890!tr", "PDF/Exploit.2345!tr",
]
_FG_IOC_TYPES = ["ip", "domain", "url", "file_hash"]
_FG_IOC_DOMAINS = [
    "evil-domain.com", "malware-c2.net", "phishing-login.xyz", "exploit-kit.biz",
    "botnet-relay.org", "crypto-miner.ru",
]
_FG_IOC_CATEGORIES = ["C2", "Malware", "Phishing", "Exploit Kit", "Botnet", "Ransomware"]


@register_vendor
class FortinetVendor(BaseVendor):
    vendor_type = VendorType.FORTINET

    def __init__(self, rng: SeededRandom):
        super().__init__(rng)
        self._session_counter = rng.randint(100000, 999999)

    def supported_event_types(self) -> list[str]:
        return [
            "traffic_forward_accept", "traffic_forward_deny",
            "traffic_local",
            "utm_ips", "utm_webfilter", "utm_antivirus", "utm_appcontrol",
            "utm_file", "utm_ioc",
            "event_system", "event_vpn",
            "baseline_info",
        ]

    _ALIASES = {
        "traffic_forward": "_gen_traffic_forward_accept",
        "traffic_deny": "_gen_traffic_forward_deny",
    }

    def generate_event(
        self, event_type: str, params: dict[str, Any], device: Device, timestamp: datetime
    ) -> list[LogEvent]:
        if event_type in self._ALIASES:
            method = getattr(self, self._ALIASES[event_type], None)
        else:
            method = getattr(self, f"_gen_{event_type}", None)
        if method is None:
            return []
        return method(device, timestamp, params)

    def _next_session(self) -> int:
        self._session_counter += 1
        return self._session_counter

    def _fg_ts(self, ts: datetime) -> tuple[str, str]:
        return ts.strftime("%Y-%m-%d"), ts.strftime("%H:%M:%S")

    def _devid(self, device: Device) -> str:
        return device.serial_number or f"FGT600E{self.rng.randint(1000000000, 9999999999)}"

    def _kv(self, **kwargs) -> str:
        parts = []
        for k, v in kwargs.items():
            if isinstance(v, str) and (" " in v or "." in v or "/" in v):
                parts.append(f'{k}="{v}"')
            else:
                parts.append(f"{k}={v}")
        return " ".join(parts)

    # --- Traffic logs ---

    def _gen_traffic_forward_accept(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_traffic(device, ts, params, "forward", "accept")

    def _gen_traffic_forward_deny(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_traffic(device, ts, params, "forward", "deny")

    def _gen_traffic_local(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        return self._gen_traffic(device, ts, params, "local", "accept")

    def _gen_traffic(self, device: Device, ts: datetime, params: dict, subtype: str, action: str) -> list[LogEvent]:
        date_str, time_str = self._fg_ts(ts)
        src_ip = params.get("src_ip", self.rng.random_ip("10.1.0.0/16"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("203.0.113.0/24"))
        src_port = params.get("src_port", self.rng.random_port())
        dst_port = params.get("dst_port", self.rng.random_port(ephemeral=False))
        protocol = params.get("protocol_num", 6)
        session_id = self._next_session()
        app_info = self.rng.choice(_FG_APPS)
        sent = params.get("sentbyte", self.rng.random_bytes_count(500, 50000))
        rcvd = params.get("rcvdbyte", self.rng.random_bytes_count(500, 500000))
        duration = params.get("duration", self.rng.randint(1, 600))
        policy_id = params.get("policyid", self.rng.randint(1, 50))
        policy_name = params.get("policyname", "Allow-Web-Outbound")
        src_intf = params.get("srcintf", "port1")
        dst_intf = params.get("dstintf", "port2")
        dst_country = self.rng.choice(_FG_COUNTRIES[:12])

        content = self._kv(
            date=date_str, time=time_str,
            devname=device.hostname, devid=self._devid(device),
            logid="0000000013", type="traffic", subtype=subtype,
            level="notice", vd="root",
            eventtime=int(ts.timestamp()),
            srcip=src_ip, srcport=src_port,
            srcintf=src_intf, srcintfrole="lan",
            dstip=dst_ip, dstport=dst_port,
            dstintf=dst_intf, dstintfrole="wan",
            sessionid=session_id, proto=protocol,
            action=action, policyid=policy_id,
            policyname=policy_name, policytype="policy",
            service="HTTPS" if dst_port == 443 else "HTTP" if dst_port == 80 else "TCP",
            dstcountry=dst_country, srccountry="Reserved",
            duration=duration, sentbyte=sent, rcvdbyte=rcvd,
            sentpkt=self.rng.randint(5, 500),
            rcvdpkt=self.rng.randint(5, 5000),
            appid=self.rng.randint(10000, 50000),
            app=app_info[0], appcat=app_info[1],
            apprisk=app_info[2],
            utmaction="allow" if action == "accept" else "block",
        )

        return [self._make_event(
            device, ts, Severity.NOTICE if action == "accept" else Severity.WARNING,
            content, f"traffic.{subtype}",
            log_source="fortinet.traffic",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "src_port": str(src_port), "dst_port": str(dst_port),
                "protocol": "tcp" if protocol == 6 else "udp" if protocol == 17 else str(protocol),
                "network.firewall.action": action,
                "network.firewall.rule_name": policy_name,
                "network.firewall.application": app_info[0],
                "network.firewall.src_zone": src_intf,
                "network.firewall.dst_zone": dst_intf,
                "network.firewall.session_id": str(session_id),
                "network.firewall.bytes_sent": str(sent),
                "network.firewall.bytes_recv": str(rcvd),
                "network.log.type": "traffic",
                "network.log.subtype": subtype,
                "network.geo.dst_country": dst_country,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- UTM logs ---

    def _gen_utm_ips(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        date_str, time_str = self._fg_ts(ts)
        attack = self.rng.choice(_FG_IPS_ATTACKS)
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("10.1.0.0/16"))
        action = params.get("action", "detected" if attack[1] in ("medium", "low") else "dropped")
        signature_id = attack[3]
        classification = attack[4]
        impact_level = attack[1]

        content = self._kv(
            date=date_str, time=time_str,
            devname=device.hostname, devid=self._devid(device),
            logid="0419016384", type="utm", subtype="ips",
            eventtype="signature", level=attack[1], vd="root",
            eventtime=int(ts.timestamp()),
            severity=attack[1], srcip=src_ip,
            dstip=dst_ip, srcport=self.rng.random_port(),
            dstport=self.rng.random_port(ephemeral=False),
            srcintf="port2", dstintf="port1",
            proto=6, action=action,
            attack=attack[0],
            attackid=signature_id,
            ref="http://www.fortiguard.com",
        )
        return [self._make_event(
            device, ts, Severity.WARNING if attack[1] == "critical" else Severity.NOTICE,
            content, "utm.ips",
            log_source="fortinet.utm",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "network.ips.attack_name": attack[0],
                "network.ips.severity": attack[1],
                "network.ips.action": action,
                "network.ips.signature_id": signature_id,
                "network.ips.classification": classification,
                "network.ips.impact_level": impact_level,
                "network.log.type": "utm",
                "network.log.subtype": "ips",
                "network.security.event_type": "ips_event",
                "network.security.severity": impact_level,
                "network.security.classification": classification,
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_utm_webfilter(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        date_str, time_str = self._fg_ts(ts)
        cat_info = self.rng.choice(_FG_WEBFILTER_CATEGORIES)
        src_ip = params.get("src_ip", self.rng.random_ip("10.1.0.0/16"))
        url = params.get("url", f"https://example-{self.rng.randint(1, 999)}.com/page")
        content = self._kv(
            date=date_str, time=time_str,
            devname=device.hostname, devid=self._devid(device),
            logid="0316013056", type="utm", subtype="webfilter",
            eventtype="ftgd_allow", level="notice", vd="root",
            eventtime=int(ts.timestamp()),
            srcip=src_ip, dstip=self.rng.random_ip("203.0.113.0/24"),
            srcport=self.rng.random_port(),
            dstport=443, hostname=url,
            catdesc=cat_info[0], action=cat_info[1],
            cat=cat_info[2],
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "utm.webfilter",
            log_source="fortinet.utm",
            attributes={
                "src_ip": src_ip,
                "network.url.category": cat_info[0],
                "network.url.action": cat_info[1],
                "network.log.type": "utm",
                "network.log.subtype": "webfilter",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_utm_antivirus(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        date_str, time_str = self._fg_ts(ts)
        virus_name = f"W32/{self.rng.choice(['Trojan', 'Worm', 'Ransom', 'Backdoor'])}.{self.rng.randint(1000, 9999)}!tr"
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        file_name = self.rng.choice(_FG_FILE_NAMES)
        file_type = file_name.rsplit(".", 1)[-1].upper() if "." in file_name else "BIN"
        file_hash = f"{self.rng.randint(0, 2**128):032x}{self.rng.randint(0, 2**128):032x}"
        content = self._kv(
            date=date_str, time=time_str,
            devname=device.hostname, devid=self._devid(device),
            logid="0211008192", type="utm", subtype="virus",
            eventtype="infected", level="warning", vd="root",
            eventtime=int(ts.timestamp()),
            srcip=src_ip,
            dstip=self.rng.random_ip("10.1.0.0/16"),
            srcport=self.rng.random_port(),
            dstport=self.rng.random_port(ephemeral=False),
            action="blocked", virus=virus_name,
            dtype="Virus", ref="http://www.fortiguard.com",
            filename=file_name, filetype=file_type,
            filehash=file_hash,
        )
        return [self._make_event(
            device, ts, Severity.WARNING, content, "utm.virus",
            log_source="fortinet.utm",
            attributes={
                "src_ip": src_ip,
                "network.threat.type": "virus",
                "network.threat.name": virus_name,
                "network.threat.action": "blocked",
                "network.file.name": file_name,
                "network.file.type": file_type,
                "network.file.sha256": file_hash,
                "network.malware.name": virus_name,
                "network.malware.family": virus_name.split("/")[1].split(".")[0] if "/" in virus_name else "Unknown",
                "network.malware.disposition": "blocked",
                "network.malware.file_hash": file_hash,
                "network.malware.file_name": file_name,
                "network.log.type": "utm",
                "network.log.subtype": "virus",
                "network.security.event_type": "malware_event",
                "network.security.severity": "high",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_utm_appcontrol(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        date_str, time_str = self._fg_ts(ts)
        app = self.rng.choice(_FG_APPS)
        action = params.get("action", self.rng.choice(["pass", "block", "monitor"]))
        src_ip = params.get("src_ip", self.rng.random_ip("10.1.0.0/16"))
        content = self._kv(
            date=date_str, time=time_str,
            devname=device.hostname, devid=self._devid(device),
            logid="1059028704", type="utm", subtype="app-ctrl",
            eventtype="app-ctrl-all", level="notice", vd="root",
            eventtime=int(ts.timestamp()),
            srcip=src_ip,
            dstip=self.rng.random_ip("203.0.113.0/24"),
            srcport=self.rng.random_port(),
            dstport=443, app=app[0],
            appcat=app[1], apprisk=app[2],
            action=action,
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "utm.app-ctrl",
            log_source="fortinet.utm",
            attributes={
                "src_ip": src_ip,
                "network.firewall.application": app[0],
                "network.firewall.app_category": app[1],
                "network.firewall.app_risk": app[2],
                "network.firewall.action": action,
                "network.log.type": "utm",
                "network.log.subtype": "app-ctrl",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- Event logs ---

    def _gen_event_system(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        date_str, time_str = self._fg_ts(ts)
        msg = params.get("message", self.rng.choice([
            "Admin login successful", "System configuration changed",
            "Firmware upgrade check completed", "NTP synchronization successful",
            "HA heartbeat received from peer", "License check completed",
        ]))
        level = params.get("level", "notice")
        content = self._kv(
            date=date_str, time=time_str,
            devname=device.hostname, devid=self._devid(device),
            logid="0100032003", type="event", subtype="system",
            level=level, vd="root",
            eventtime=int(ts.timestamp()), msg=msg,
        )
        return [self._make_event(
            device, ts, Severity.NOTICE, content, "event.system",
            log_source="fortinet.event",
            attributes={"network.log.type": "event", "network.log.subtype": "system"},
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_event_vpn(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        date_str, time_str = self._fg_ts(ts)
        action = params.get("action", self.rng.choice(["tunnel-up", "tunnel-down", "phase2-up", "phase2-down"]))
        remote_ip = params.get("remip", self.rng.random_ip("203.0.113.0/24"))
        vpn_name = params.get("vpn_name", f"VPN-{self.rng.choice(['HQ', 'Branch', 'DC'])}-{self.rng.randint(1, 10)}")
        content = self._kv(
            date=date_str, time=time_str,
            devname=device.hostname, devid=self._devid(device),
            logid="0101039949", type="event", subtype="vpn",
            level="notice" if "up" in action else "warning",
            vd="root", eventtime=int(ts.timestamp()),
            action=action, remip=remote_ip,
            tunneltype="ipsec", tunnelid=self.rng.randint(1, 100),
            vpntunnel=vpn_name,
            msg=f"IPsec {action} for peer {remote_ip}",
        )
        return [self._make_event(
            device, ts, Severity.NOTICE if "up" in action else Severity.WARNING,
            content, f"event.vpn.{action}",
            log_source="fortinet.event",
            attributes={
                "network.vpn.action": action,
                "network.vpn.peer_ip": remote_ip,
                "network.vpn.tunnel_name": vpn_name,
                "network.log.type": "event",
                "network.log.subtype": "vpn",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        msg_type = self.rng.weighted_choice(
            ["traffic_forward_accept", "event_system", "utm_appcontrol", "utm_webfilter",
             "utm_ips", "utm_file", "utm_antivirus", "utm_ioc"],
            [0.35, 0.15, 0.12, 0.12, 0.10, 0.06, 0.05, 0.05],
        )
        return getattr(self, f"_gen_{msg_type}")(device, ts, params)

    # --- UTM File Events (analytics sandbox) ---

    def _gen_utm_file(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        date_str, time_str = self._fg_ts(ts)
        file_name = params.get("file_name", self.rng.choice(_FG_FILE_NAMES))
        file_type = params.get("file_type", file_name.rsplit(".", 1)[-1].upper() if "." in file_name else "BIN")
        file_size = params.get("file_size", self.rng.randint(1024, 52428800))
        file_hash = params.get("file_hash", f"{self.rng.randint(0, 2**128):032x}{self.rng.randint(0, 2**128):032x}")
        disposition = params.get("file_disposition", self.rng.weighted_choice(
            _FG_FILE_DISPOSITIONS, [0.08, 0.60, 0.20, 0.12],
        ))
        direction = params.get("direction", self.rng.choice(["download", "upload"]))
        src_ip = params.get("src_ip", self.rng.random_ip("192.0.2.0/24"))
        dst_ip = params.get("dst_ip", self.rng.random_ip("10.1.0.0/16"))

        content = self._kv(
            date=date_str, time=time_str,
            devname=device.hostname, devid=self._devid(device),
            logid="0211008193", type="utm", subtype="virus",
            eventtype="analytics", level="notice", vd="root",
            eventtime=int(ts.timestamp()),
            srcip=src_ip, dstip=dst_ip,
            srcport=self.rng.random_port(),
            dstport=self.rng.random_port(ephemeral=False),
            filename=file_name, filetype=file_type,
            filesize=file_size, filehash=file_hash,
            action="passthrough" if disposition == "Clean" else "blocked",
            direction=direction,
        )
        return [self._make_event(
            device, ts, Severity.WARNING if disposition == "Malware" else Severity.NOTICE,
            content, "utm.file",
            log_source="fortinet.utm",
            attributes={
                "src_ip": src_ip, "dst_ip": dst_ip,
                "network.file.name": file_name,
                "network.file.type": file_type,
                "network.file.size": str(file_size),
                "network.file.sha256": file_hash,
                "network.file.disposition": disposition,
                "network.file.direction": direction,
                "network.log.type": "utm",
                "network.log.subtype": "file",
                "network.security.event_type": "file_event",
                "network.security.severity": "high" if disposition == "Malware" else "low",
            },
            scenario_id=params.get("scenario_id", ""),
        )]

    # --- UTM IOC Events (Threat Intelligence) ---

    def _gen_utm_ioc(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        date_str, time_str = self._fg_ts(ts)
        ioc_type = params.get("ioc_type", self.rng.choice(_FG_IOC_TYPES))
        if ioc_type == "ip":
            ioc_value = self.rng.random_ip("198.51.100.0/24")
        elif ioc_type == "domain":
            ioc_value = self.rng.choice(_FG_IOC_DOMAINS)
        elif ioc_type == "url":
            ioc_value = f"http://{self.rng.choice(_FG_IOC_DOMAINS)}/malware/{self.rng.randint(1,999)}"
        else:
            ioc_value = f"{self.rng.randint(0, 2**128):032x}{self.rng.randint(0, 2**128):032x}"
        ioc_confidence = params.get("ioc_confidence", self.rng.choice(["high", "medium", "low"]))
        ioc_category = params.get("ioc_category", self.rng.choice(_FG_IOC_CATEGORIES))
        src_ip = params.get("src_ip", self.rng.random_ip("10.1.0.0/16"))

        content = self._kv(
            date=date_str, time=time_str,
            devname=device.hostname, devid=self._devid(device),
            logid="0211008194", type="utm", subtype="ips",
            eventtype="botnet", level="warning", vd="root",
            eventtime=int(ts.timestamp()),
            srcip=src_ip,
            dstip=self.rng.random_ip("203.0.113.0/24"),
            action="detected",
            botnetdomain=ioc_value if ioc_type == "domain" else "",
            botnetip=ioc_value if ioc_type == "ip" else "",
        )
        return [self._make_event(
            device, ts, Severity.WARNING,
            content, "utm.ioc",
            log_source="fortinet.utm",
            attributes={
                "src_ip": src_ip,
                "network.ioc.type": ioc_type,
                "network.ioc.value": ioc_value,
                "network.ioc.source": "FortiGuard",
                "network.ioc.confidence": ioc_confidence,
                "network.ioc.category": ioc_category,
                "network.log.type": "utm",
                "network.log.subtype": "ioc",
                "network.security.event_type": "ioc_event",
                "network.security.severity": "critical" if ioc_confidence == "high" else "high",
            },
            scenario_id=params.get("scenario_id", ""),
        )]
