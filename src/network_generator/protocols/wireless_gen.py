"""Wireless LAN controller log generator.

Generates wireless controller logs for AP management, client roaming,
RF events, and WIDS alerts. Generic WLC format applicable to Cisco WLC,
Aruba controllers, etc. Covers FR-604.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity
from netloggen.core.random_utils import SeededRandom


_SSIDS = ["Corp-WiFi", "Guest-WiFi", "IoT-Net", "Voice-WiFi", "Secure-802.1X"]
_CHANNELS_24 = [1, 6, 11]
_CHANNELS_5 = [36, 40, 44, 48, 52, 56, 60, 64, 149, 153, 157, 161]
_AUTH_METHODS = ["WPA2-Enterprise", "WPA3-Enterprise", "WPA2-PSK", "Open"]
_AP_MODELS = ["AP-505", "AP-515", "AP-535", "AP-635", "C9130AXI", "C9120AXI"]


class WirelessLogGenerator:
    """Generates wireless LAN controller log events."""

    def __init__(self, rng: SeededRandom | None = None) -> None:
        self.rng = rng or SeededRandom()
        self._ap_counter = 0

    def generate_events(
        self,
        device: Device,
        timestamp: datetime,
        event_type: str = "client_associate",
        params: dict[str, Any] | None = None,
    ) -> list[LogEvent]:
        params = params or {}
        method = getattr(self, f"_gen_{event_type}", None)
        if method is None:
            return self._gen_client_associate(device, timestamp, params)
        return method(device, timestamp, params)

    # ── AP management ──────────────────────────────────────────────────

    def _gen_ap_join(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ap_name = params.get("ap_name", self._random_ap_name())
        ap_mac = self.rng.random_mac()
        ap_ip = params.get("ap_ip", self.rng.random_ip("10.10.0.0/16"))
        model = self.rng.choice(_AP_MODELS)
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*apfMsConnTask: AP {ap_name} ({ap_mac}) joined controller "
                   f"with IP {ap_ip}, model {model}, firmware 8.10.190.0")
        return [self._make_event(device, ts, Severity.NOTICE, content, "AP_JOIN",
                                 attributes={"wireless.ap.name": ap_name, "wireless.ap.ip": ap_ip})]

    def _gen_ap_disassociate(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ap_name = params.get("ap_name", self._random_ap_name())
        reason = params.get("reason", self.rng.choice([
            "AP rebooted", "Discovery timeout", "DTLS connection lost",
            "Controller initiated", "Firmware mismatch",
        ]))
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*apfMsConnTask: AP {ap_name} disassociated - Reason: {reason}")
        return [self._make_event(device, ts, Severity.WARNING, content, "AP_DISASSOCIATE",
                                 attributes={"wireless.ap.name": ap_name})]

    # ── Client events ──────────────────────────────────────────────────

    def _gen_client_associate(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        mac = params.get("client_mac", self.rng.random_mac())
        ssid = params.get("ssid", self.rng.choice(_SSIDS))
        ap_name = params.get("ap_name", self._random_ap_name())
        channel = self.rng.choice(_CHANNELS_24 + _CHANNELS_5)
        rssi = self.rng.randint(-80, -30)
        auth = self.rng.choice(_AUTH_METHODS) if "Corp" in ssid or "Secure" in ssid else "WPA2-PSK"
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*dot11MsgTask: STA {mac} Associated with AP {ap_name} "
                   f"SSID '{ssid}' channel {channel} RSSI {rssi}dBm "
                   f"auth {auth}")
        return [self._make_event(device, ts, Severity.INFO, content, "CLIENT_ASSOCIATE",
                                 attributes={
                                     "wireless.client.mac": mac,
                                     "wireless.ssid": ssid,
                                     "wireless.channel": str(channel),
                                     "wireless.rssi": str(rssi),
                                 })]

    def _gen_client_disassociate(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        mac = params.get("client_mac", self.rng.random_mac())
        reason = params.get("reason", self.rng.choice([
            "Client deauthentication", "Inactivity timeout",
            "Excessive retries", "AP down", "Roamed to another AP",
        ]))
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*dot11MsgTask: STA {mac} Disassociated - Reason: {reason}")
        return [self._make_event(device, ts, Severity.INFO, content, "CLIENT_DISASSOCIATE",
                                 attributes={"wireless.client.mac": mac})]

    def _gen_client_roam(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        mac = params.get("client_mac", self.rng.random_mac())
        from_ap = params.get("from_ap", self._random_ap_name())
        to_ap = params.get("to_ap", self._random_ap_name())
        roam_type = self.rng.choice(["Fast BSS Transition (802.11r)", "OKC", "Full re-auth"])
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*dot11MsgTask: STA {mac} roamed from {from_ap} to {to_ap} "
                   f"({roam_type}) latency {self.rng.randint(5, 200)}ms")
        return [self._make_event(device, ts, Severity.INFO, content, "CLIENT_ROAM",
                                 attributes={
                                     "wireless.client.mac": mac,
                                     "wireless.roam.from_ap": from_ap,
                                     "wireless.roam.to_ap": to_ap,
                                 })]

    def _gen_client_auth_failure(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        mac = params.get("client_mac", self.rng.random_mac())
        reason = self.rng.choice([
            "RADIUS reject", "Invalid certificate", "EAP timeout",
            "Wrong password", "MAC not allowed",
        ])
        ssid = params.get("ssid", self.rng.choice(_SSIDS))
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*dot1xMsgTask: STA {mac} authentication failed on SSID '{ssid}' "
                   f"- Reason: {reason}")
        return [self._make_event(device, ts, Severity.WARNING, content, "CLIENT_AUTH_FAILURE",
                                 attributes={"wireless.client.mac": mac, "wireless.ssid": ssid})]

    # ── RF events ──────────────────────────────────────────────────────

    def _gen_rf_interference(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ap_name = params.get("ap_name", self._random_ap_name())
        channel = self.rng.choice(_CHANNELS_24)
        interference_pct = self.rng.randint(40, 95)
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*rfMgrTask: AP {ap_name} channel {channel} "
                   f"interference {interference_pct}% — "
                   f"co-channel APs detected: {self.rng.randint(2,8)}")
        return [self._make_event(device, ts, Severity.WARNING, content, "RF_INTERFERENCE",
                                 attributes={"wireless.ap.name": ap_name})]

    def _gen_rf_channel_change(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ap_name = params.get("ap_name", self._random_ap_name())
        old_ch = self.rng.choice(_CHANNELS_5)
        new_ch = self.rng.choice([c for c in _CHANNELS_5 if c != old_ch])
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*rfMgrTask: AP {ap_name} DCA changed 5GHz channel "
                   f"from {old_ch} to {new_ch} (interference avoidance)")
        return [self._make_event(device, ts, Severity.INFO, content, "RF_CHANNEL_CHANGE",
                                 attributes={"wireless.ap.name": ap_name})]

    def _gen_rf_radar_detected(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        ap_name = params.get("ap_name", self._random_ap_name())
        channel = self.rng.choice([52, 56, 60, 64])  # DFS channels
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*rfMgrTask: AP {ap_name} DFS radar detected on channel {channel}, "
                   f"moving to channel {self.rng.choice([36, 40, 44, 48])}")
        return [self._make_event(device, ts, Severity.WARNING, content, "RF_RADAR_DETECTED",
                                 attributes={"wireless.ap.name": ap_name})]

    # ── WIDS/WIPS ──────────────────────────────────────────────────────

    def _gen_wids_rogue_ap(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        rogue_mac = self.rng.random_mac()
        rogue_ssid = params.get("ssid", self.rng.choice(["Evil-Twin", "Free-WiFi", "Corp-WiFi"]))
        detecting_ap = self._random_ap_name()
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*widsTask: Rogue AP detected BSSID {rogue_mac} "
                   f"SSID '{rogue_ssid}' on channel {self.rng.choice(_CHANNELS_24)} "
                   f"RSSI {self.rng.randint(-70, -20)}dBm "
                   f"detected by {detecting_ap} — Classification: "
                   f"{self.rng.choice(['Malicious', 'Interfering', 'Unclassified'])}")
        return [self._make_event(device, ts, Severity.ALERT, content, "WIDS_ROGUE_AP",
                                 attributes={"wireless.rogue.bssid": rogue_mac})]

    def _gen_wids_deauth_flood(self, device: Device, ts: datetime, params: dict) -> list[LogEvent]:
        src_mac = self.rng.random_mac()
        ap_name = self._random_ap_name()
        count = self.rng.randint(100, 5000)
        content = (f"{ts.strftime('%b %d %H:%M:%S')} {device.hostname} wlc: "
                   f"*widsTask: Deauthentication flood detected from {src_mac} "
                   f"targeting AP {ap_name} — {count} frames in 60s")
        return [self._make_event(device, ts, Severity.ALERT, content, "WIDS_DEAUTH_FLOOD",
                                 attributes={"network.threat.name": "Deauth Flood"})]

    # ── helpers ────────────────────────────────────────────────────────

    def _random_ap_name(self) -> str:
        self._ap_counter += 1
        floor = self.rng.choice(["1F", "2F", "3F", "4F", "B1"])
        return f"AP-{floor}-{self._ap_counter % 100:02d}"

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
            log_source="wireless.wlc",
            attributes=attributes or {},
        )
