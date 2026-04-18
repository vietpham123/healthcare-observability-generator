"""F5 BIG-IP log generator — LTM, ASM, APM, and system logs.

Generates F5-style syslog with facility-based dispatch:
  TIMESTAMP hostname FACILITY[PID]: message
Covers FR-209.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor


@register_vendor
class F5Vendor(BaseVendor):
    vendor_type = VendorType.F5

    def supported_event_types(self) -> list[str]:
        return [
            "ltm_pool_member_down", "ltm_pool_member_up",
            "ltm_virtual_status", "ltm_connection",
            "asm_violation", "asm_attack",
            "apm_session_start", "apm_session_end",
            "system_failover", "system_config_change",
            "system_cpu_high", "system_disk_alert",
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
        return ts.strftime("%b %d %H:%M:%S")

    def _pid(self) -> int:
        return self.rng.randint(1000, 65000)

    # ── LTM (Local Traffic Manager) ───────────────────────────────────

    def _gen_ltm_pool_member_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        pool = params.get("pool", "/Common/web_pool")
        member = params.get("member", f"10.0.1.{self.rng.randint(10,50)}:443")
        monitor = params.get("monitor", "https")
        content = (f"{self._ts(ts)} {device.hostname} mcpd[{self._pid()}]: "
                   f"01070638:5: Pool {pool} member {member} monitor status down. "
                   f"[ {monitor}: up ] [ was -> now down ] [ from node ]")
        return [self._make_event(device, ts, Severity.WARNING, content, "LTM_POOL_MEMBER_DOWN",
                                 log_source="f5.ltm",
                                 attributes={"f5.pool": pool, "f5.member": member})]

    def _gen_ltm_pool_member_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        pool = params.get("pool", "/Common/web_pool")
        member = params.get("member", f"10.0.1.{self.rng.randint(10,50)}:443")
        content = (f"{self._ts(ts)} {device.hostname} mcpd[{self._pid()}]: "
                   f"01070727:5: Pool {pool} member {member} monitor status up. "
                   f"[ https: up ] [ was down for 120s ]")
        return [self._make_event(device, ts, Severity.NOTICE, content, "LTM_POOL_MEMBER_UP",
                                 log_source="f5.ltm")]

    def _gen_ltm_virtual_status(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        vs = params.get("virtual_server", "/Common/vs_web")
        status = params.get("status", "available")
        content = (f"{self._ts(ts)} {device.hostname} mcpd[{self._pid()}]: "
                   f"01070640:5: Virtual {vs} has become {status}")
        sev = Severity.INFO if status == "available" else Severity.WARNING
        return [self._make_event(device, ts, sev, content, "LTM_VS_STATUS",
                                 log_source="f5.ltm")]

    def _gen_ltm_connection(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        vs = params.get("virtual_server", "/Common/vs_web")
        src = self.rng.random_ip("10.0.0.0/8")
        dst = self.rng.random_ip("10.0.1.0/24")
        content = (f"{self._ts(ts)} {device.hostname} tmm[{self._pid()}]: "
                   f"Rule /Common/irule_log <CLIENT_ACCEPTED>: "
                   f"Connection from {src}:{self.rng.random_port()} to "
                   f"{vs} ({dst}:{self.rng.choice([80,443,8443])})")
        return [self._make_event(device, ts, Severity.INFO, content, "LTM_CONNECTION",
                                 log_source="f5.ltm")]

    # ── ASM (Application Security Manager / WAF) ──────────────────────

    def _gen_asm_violation(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        violation = params.get("violation", self.rng.choice([
            "Illegal URL", "Illegal parameter", "Modified domain cookie",
            "Illegal file type", "Attack signature detected",
        ]))
        src = self.rng.random_ip("198.51.100.0/24")
        uri = self.rng.choice(["/admin/config", "/api/v1/users", "/login", "/search?q=test"])
        content = (f"{self._ts(ts)} {device.hostname} ASM:"
                   f"{self._ts(ts)} {device.hostname} ASM:unit_hostname=\"{device.hostname}\","
                   f"management_ip_address=\"{device.management_ip}\","
                   f"policy_name=\"/Common/web_policy\","
                   f"violation_rating=\"{self.rng.randint(1,5)}\","
                   f"request_status=\"blocked\","
                   f"response_code=\"403\","
                   f"ip_client=\"{src}\","
                   f"sig_ids=\"{self.rng.randint(200000000,299999999)}\","
                   f"violations=\"{violation}\","
                   f"uri=\"{uri}\"")
        return [self._make_event(device, ts, Severity.WARNING, content, "ASM_VIOLATION",
                                 log_source="f5.asm",
                                 attributes={"network.threat.name": violation})]

    def _gen_asm_attack(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        attack = params.get("attack", self.rng.choice([
            "SQL-Injection", "Cross-Site-Scripting", "Path-Traversal",
            "Command-Execution", "Server-Side-Code-Injection",
        ]))
        src = self.rng.random_ip("198.51.100.0/24")
        content = (f"{self._ts(ts)} {device.hostname} ASM:"
                   f"attack_type=\"{attack}\","
                   f"ip_client=\"{src}\","
                   f"severity=\"Critical\","
                   f"request_status=\"blocked\","
                   f"policy_name=\"/Common/web_policy\"")
        return [self._make_event(device, ts, Severity.ALERT, content, "ASM_ATTACK",
                                 log_source="f5.asm")]

    # ── APM (Access Policy Manager) ───────────────────────────────────

    def _gen_apm_session_start(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", f"user_{self.rng.randint(100,999)}")
        src = self.rng.random_ip("10.0.0.0/8")
        session_id = f"{self.rng.randint(10000000,99999999)}"
        content = (f"{self._ts(ts)} {device.hostname} apmd[{self._pid()}]: "
                   f"01490000:5: {session_id}: New session from client IP {src} "
                   f"for user {user} - access policy /Common/corp_vpn_policy")
        return [self._make_event(device, ts, Severity.INFO, content, "APM_SESSION_START",
                                 log_source="f5.apm")]

    def _gen_apm_session_end(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", f"user_{self.rng.randint(100,999)}")
        session_id = f"{self.rng.randint(10000000,99999999)}"
        content = (f"{self._ts(ts)} {device.hostname} apmd[{self._pid()}]: "
                   f"01490005:5: {session_id}: Session deleted for user {user} "
                   f"- Duration: {self.rng.randint(60,28800)}s")
        return [self._make_event(device, ts, Severity.INFO, content, "APM_SESSION_END",
                                 log_source="f5.apm")]

    # ── System ─────────────────────────────────────────────────────────

    def _gen_system_failover(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        new_state = params.get("state", "active")
        content = (f"{self._ts(ts)} {device.hostname} sod[{self._pid()}]: "
                   f"010c0047:5: Standby unit {device.hostname} becoming {new_state}. "
                   f"Reason: Peer heartbeat lost")
        return [self._make_event(device, ts, Severity.ALERT, content, "SYSTEM_FAILOVER",
                                 log_source="f5.system")]

    def _gen_system_config_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", "admin")
        content = (f"{self._ts(ts)} {device.hostname} mcpd[{self._pid()}]: "
                   f"01070417:6: AUDIT - user {user} - "
                   f"transaction #{self.rng.randint(100000,999999)} - "
                   f"object 0 - modify { self.rng.choice(['/Common/web_pool', '/Common/vs_web', '/Common/node_10.0.1.10']) }")
        return [self._make_event(device, ts, Severity.INFO, content, "SYS_CONFIG_CHANGE",
                                 log_source="f5.system")]

    def _gen_system_cpu_high(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        pct = params.get("cpu_pct", self.rng.randint(85, 99))
        content = (f"{self._ts(ts)} {device.hostname} tmm[{self._pid()}]: "
                   f"01010028:4: No free TMM memory, CPU at {pct}%")
        return [self._make_event(device, ts, Severity.WARNING, content, "SYS_CPU_HIGH",
                                 log_source="f5.system")]

    def _gen_system_disk_alert(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        pct = params.get("disk_pct", self.rng.randint(90, 99))
        partition = params.get("partition", "/var")
        content = (f"{self._ts(ts)} {device.hostname} syslog-ng[{self._pid()}]: "
                   f"Disk partition {partition} has only {100-pct}% free "
                   f"({pct}% used)")
        return [self._make_event(device, ts, Severity.WARNING, content, "SYS_DISK_ALERT",
                                 log_source="f5.system")]

    # ── Baseline ───────────────────────────────────────────────────────

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        choices = [
            "ltm_connection", "ltm_virtual_status",
            "apm_session_start", "apm_session_end",
            "system_config_change",
        ]
        weights = [0.35, 0.15, 0.2, 0.2, 0.1]
        evt = self.rng.weighted_choice(choices, weights)
        return getattr(self, f"_gen_{evt}")(device, ts, params)
