"""HP/Aruba switch and wireless controller log generator.

Generates Aruba CX / AOS-CX syslog and ArubaOS wireless controller messages.
Covers FR-210.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom
from netloggen.vendors.base import BaseVendor, register_vendor


@register_vendor
class ArubaVendor(BaseVendor):
    vendor_type = VendorType.ARUBA

    def supported_event_types(self) -> list[str]:
        return [
            "interface_down", "interface_up",
            "ap_up", "ap_down", "client_associate", "client_disassociate",
            "rogue_ap_detected", "wids_attack",
            "auth_success", "auth_failure",
            "controller_failover",
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
        return ts.strftime("%b %d %H:%M:%S %Y")

    # ── Wired (AOS-CX) ────────────────────────────────────────────────

    def _gen_interface_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "1/1/1")
        content = (f"{self._ts(ts)} {device.hostname} hpe-switch: "
                   f"LACP/5/LACP_DOWN: Port {iface} state changed to DOWN")
        return [self._make_event(device, ts, Severity.WARNING, content, "LACP_DOWN",
                                 log_source="aruba.lacp",
                                 attributes={"network.interface.name": iface})]

    def _gen_interface_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        iface = params.get("interface", "1/1/1")
        content = (f"{self._ts(ts)} {device.hostname} hpe-switch: "
                   f"LACP/5/LACP_UP: Port {iface} state changed to UP")
        return [self._make_event(device, ts, Severity.NOTICE, content, "LACP_UP",
                                 log_source="aruba.lacp")]

    # ── Wireless ───────────────────────────────────────────────────────

    def _gen_ap_up(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ap_name = params.get("ap_name", f"AP-{self.rng.randint(100,999)}")
        ap_ip = params.get("ap_ip", self.rng.random_ip("10.10.0.0/16"))
        content = (f"{self._ts(ts)} {device.hostname} stm[{self.rng.randint(1000,9999)}]: "
                   f"<501106> <NOTI> |AP {ap_name}@{ap_ip}: AP is now up and ready, "
                   f"BSSID {self.rng.random_mac()}")
        return [self._make_event(device, ts, Severity.NOTICE, content, "AP_UP",
                                 log_source="aruba.stm",
                                 attributes={"wireless.ap.name": ap_name})]

    def _gen_ap_down(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ap_name = params.get("ap_name", f"AP-{self.rng.randint(100,999)}")
        ap_ip = params.get("ap_ip", self.rng.random_ip("10.10.0.0/16"))
        reason = params.get("reason", self.rng.choice([
            "AP rebooted", "PSE fault", "Heartbeat timeout", "Radio failure",
        ]))
        content = (f"{self._ts(ts)} {device.hostname} stm[{self.rng.randint(1000,9999)}]: "
                   f"<501107> <WARN> |AP {ap_name}@{ap_ip}: AP went down - {reason}")
        return [self._make_event(device, ts, Severity.WARNING, content, "AP_DOWN",
                                 log_source="aruba.stm",
                                 attributes={"wireless.ap.name": ap_name})]

    def _gen_client_associate(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        mac = self.rng.random_mac()
        ssid = params.get("ssid", self.rng.choice(["Corp-WiFi", "Guest-WiFi", "IoT-Net"]))
        ap_name = params.get("ap_name", f"AP-{self.rng.randint(100,999)}")
        content = (f"{self._ts(ts)} {device.hostname} stm[{self.rng.randint(1000,9999)}]: "
                   f"<501082> <NOTI> |STA {mac} associated to AP {ap_name} "
                   f"SSID {ssid} BSSID {self.rng.random_mac()} channel {self.rng.choice([1,6,11,36,40,44,48])}")
        return [self._make_event(device, ts, Severity.INFO, content, "CLIENT_ASSOCIATE",
                                 log_source="aruba.stm")]

    def _gen_client_disassociate(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        mac = self.rng.random_mac()
        reason = self.rng.choice(["Idle timeout", "Deauth from client", "Roamed", "AP down"])
        content = (f"{self._ts(ts)} {device.hostname} stm[{self.rng.randint(1000,9999)}]: "
                   f"<501083> <NOTI> |STA {mac} disassociated - reason: {reason}")
        return [self._make_event(device, ts, Severity.INFO, content, "CLIENT_DISASSOCIATE",
                                 log_source="aruba.stm")]

    def _gen_rogue_ap_detected(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        rogue_mac = self.rng.random_mac()
        channel = self.rng.choice([1, 6, 11, 36, 40])
        rssi = self.rng.randint(-80, -30)
        content = (f"{self._ts(ts)} {device.hostname} wms[{self.rng.randint(1000,9999)}]: "
                   f"<501003> <WARN> |Rogue AP detected: BSSID {rogue_mac} "
                   f"SSID \"Evil-Twin\" channel {channel} RSSI {rssi}dBm "
                   f"classification: Interfering")
        return [self._make_event(device, ts, Severity.WARNING, content, "ROGUE_AP_DETECTED",
                                 log_source="aruba.wms")]

    def _gen_wids_attack(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        attack = self.rng.choice([
            "Deauthentication flood", "Disassociation flood",
            "EAPOL-Start flood", "Beacon flood",
        ])
        src_mac = self.rng.random_mac()
        content = (f"{self._ts(ts)} {device.hostname} wms[{self.rng.randint(1000,9999)}]: "
                   f"<501008> <CRIT> |WIDS: {attack} detected from {src_mac}")
        return [self._make_event(device, ts, Severity.ALERT, content, "WIDS_ATTACK",
                                 log_source="aruba.wids",
                                 attributes={"network.threat.name": attack})]

    def _gen_auth_success(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", f"user{self.rng.randint(100,999)}")
        mac = self.rng.random_mac()
        content = (f"{self._ts(ts)} {device.hostname} authmgr[{self.rng.randint(1000,9999)}]: "
                   f"<501200> <NOTI> |802.1X authentication succeeded for {user} "
                   f"MAC {mac} role=employee")
        return [self._make_event(device, ts, Severity.INFO, content, "AUTH_SUCCESS",
                                 log_source="aruba.authmgr")]

    def _gen_auth_failure(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        user = params.get("user", f"user{self.rng.randint(100,999)}")
        mac = self.rng.random_mac()
        content = (f"{self._ts(ts)} {device.hostname} authmgr[{self.rng.randint(1000,9999)}]: "
                   f"<501201> <WARN> |802.1X authentication failed for {user} "
                   f"MAC {mac} - RADIUS reject")
        return [self._make_event(device, ts, Severity.WARNING, content, "AUTH_FAILURE",
                                 log_source="aruba.authmgr")]

    def _gen_controller_failover(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        new_role = params.get("role", "master")
        content = (f"{self._ts(ts)} {device.hostname} cfgm[{self.rng.randint(1000,9999)}]: "
                   f"<140001> <WARN> |Controller HA: Transitioning to {new_role}. "
                   f"Peer heartbeat lost after 30s")
        return [self._make_event(device, ts, Severity.ALERT, content, "CONTROLLER_FAILOVER",
                                 log_source="aruba.cfgm")]

    def _gen_baseline_info(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        choices = ["client_associate", "client_disassociate", "auth_success", "ap_up", "interface_up"]
        weights = [0.3, 0.25, 0.2, 0.15, 0.1]
        evt = self.rng.weighted_choice(choices, weights)
        return getattr(self, f"_gen_{evt}")(device, ts, params)
