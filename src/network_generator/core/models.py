"""Core data models for the network topology and events."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DeviceRole(str, enum.Enum):
    CORE = "core"
    DISTRIBUTION = "distribution"
    ACCESS = "access"
    FIREWALL = "firewall"
    LOADBALANCER = "loadbalancer"
    WLC = "wlc"
    WAN_EDGE = "wan_edge"
    DNS = "dns"
    DHCP = "dhcp"


class VendorType(str, enum.Enum):
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    CISCO_ASA = "cisco_asa"
    PALOALTO = "paloalto"
    FORTINET = "fortinet"
    JUNIPER = "juniper"
    ARISTA = "arista"
    CHECKPOINT = "checkpoint"
    F5 = "f5"
    ARUBA = "aruba"
    SOPHOS = "sophos"
    SONICWALL = "sonicwall"
    CITRIX = "citrix"


class InterfaceStatus(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    ADMIN_DOWN = "admin-down"


class Interface(BaseModel):
    name: str
    ip_address: str = ""
    subnet_mask: str = ""
    speed: str = "1G"
    status: InterfaceStatus = InterfaceStatus.UP
    connected_to: list[str] = Field(default_factory=list)  # [remote_device, remote_interface]
    vlan: int = 0
    if_index: int = 0
    zone: str = ""
    description: str = ""

    # Runtime counters (mutable state for realistic metrics)
    _bytes_in: int = 0
    _bytes_out: int = 0
    _packets_in: int = 0
    _packets_out: int = 0
    _errors_in: int = 0
    _errors_out: int = 0


class Zone(BaseModel):
    name: str
    interfaces: list[str] = Field(default_factory=list)


class Device(BaseModel):
    hostname: str
    vendor: VendorType
    model: str = ""
    os_version: str = ""
    role: DeviceRole
    site: str = "default"
    management_ip: str = ""
    interfaces: list[Interface] = Field(default_factory=list)
    zones: list[Zone] = Field(default_factory=list)
    router_id: str = ""
    serial_number: str = ""

    # Runtime state
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    session_count: int = 0
    uptime_seconds: int = 0

    def get_interface(self, name: str) -> Interface | None:
        for iface in self.interfaces:
            if iface.name == name:
                return iface
        return None

    def get_zone_for_interface(self, iface_name: str) -> str:
        for zone in self.zones:
            if iface_name in zone.interfaces:
                return zone.name
        return ""


class Topology(BaseModel):
    name: str = "default"
    sites: list[dict[str, str]] = Field(default_factory=list)
    devices: list[Device] = Field(default_factory=list)

    def get_device(self, hostname: str) -> Device | None:
        for dev in self.devices:
            if dev.hostname == hostname:
                return dev
        return None

    def get_devices_by_role(self, role: DeviceRole) -> list[Device]:
        return [d for d in self.devices if d.role == role]

    def get_devices_by_vendor(self, vendor: VendorType) -> list[Device]:
        return [d for d in self.devices if d.vendor == vendor]

    def get_devices_by_site(self, site: str) -> list[Device]:
        return [d for d in self.devices if d.site == site]

    def get_connected_peer(self, device: Device, interface_name: str) -> tuple[Device, Interface] | None:
        iface = device.get_interface(interface_name)
        if not iface or len(iface.connected_to) < 2:
            return None
        peer_dev = self.get_device(iface.connected_to[0])
        if not peer_dev:
            return None
        peer_iface = peer_dev.get_interface(iface.connected_to[1])
        if not peer_iface:
            return None
        return (peer_dev, peer_iface)


class Severity(int, enum.Enum):
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7


class LogEvent(BaseModel):
    timestamp: datetime
    device: str  # hostname reference
    vendor: VendorType
    severity: Severity = Severity.INFO
    facility: int = 23  # local7
    content: str = ""  # the raw vendor-formatted message
    event_type: str = ""  # e.g., "TRAFFIC", "SYSTEM", "%LINK-3-UPDOWN"
    log_source: str = ""  # e.g., "paloalto.traffic", "cisco_ios"
    attributes: dict[str, Any] = Field(default_factory=dict)  # structured fields for DT ingestion
    scenario_id: str = ""  # correlation ID if part of a scenario
    site: str = ""
    device_role: str = ""
    device_model: str = ""

    @property
    def pri(self) -> int:
        return self.facility * 8 + self.severity.value


class MetricEvent(BaseModel):
    timestamp: datetime
    metric_key: str
    value: float
    value_type: str = "gauge"  # gauge, count
    dimensions: dict[str, str] = Field(default_factory=dict)
    device: str = ""
    site: str = ""


class TrapEvent(BaseModel):
    timestamp: datetime
    device: str
    trap_oid: str
    trap_name: str
    severity: Severity = Severity.WARNING
    varbinds: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, str] = Field(default_factory=dict)
    site: str = ""


class FlowRecord(BaseModel):
    timestamp: datetime
    device: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str = "tcp"
    bytes_in: int = 0
    bytes_out: int = 0
    bytes_total: int = 0
    packets_total: int = 0
    tcp_flags: int = 0
    input_interface: str = ""
    output_interface: str = ""
    src_as: int = 0
    dst_as: int = 0
    site: str = ""
    # Geo fields
    src_latitude: float = 0.0
    src_longitude: float = 0.0
    src_country: str = ""
    dst_latitude: float = 0.0
    dst_longitude: float = 0.0
    dst_country: str = ""
