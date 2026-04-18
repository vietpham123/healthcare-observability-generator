"""Topology engine — loads YAML topology into the device graph model."""

from __future__ import annotations

from pathlib import Path

import yaml

from netloggen.core.models import (
    Device,
    DeviceRole,
    Interface,
    InterfaceStatus,
    Topology,
    VendorType,
    Zone,
)


def load_topology(config_path: str | Path) -> Topology:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Topology config not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    sites = raw.get("sites", [])
    devices = []

    for dev_raw in raw.get("devices", []):
        interfaces = []
        for iface_raw in dev_raw.get("interfaces", []):
            ip_addr = iface_raw.get("ip", iface_raw.get("ip_address", ""))
            if "/" in ip_addr:
                ip_part, mask_part = ip_addr.split("/", 1)
            else:
                ip_part = ip_addr
                mask_part = ""

            interfaces.append(Interface(
                name=iface_raw["name"],
                ip_address=ip_part,
                subnet_mask=mask_part,
                speed=iface_raw.get("speed", "1G"),
                status=InterfaceStatus(iface_raw.get("status", "up")),
                connected_to=iface_raw.get("connected_to", []),
                vlan=iface_raw.get("vlan", 0),
                if_index=iface_raw.get("if_index", 0),
                zone=iface_raw.get("zone", ""),
                description=iface_raw.get("description", ""),
            ))

        zones = []
        for zone_raw in dev_raw.get("zones", []):
            zones.append(Zone(
                name=zone_raw["name"],
                interfaces=zone_raw.get("interfaces", []),
            ))

        devices.append(Device(
            hostname=dev_raw["hostname"],
            vendor=VendorType(dev_raw["vendor"]),
            model=dev_raw.get("model", ""),
            os_version=dev_raw.get("os_version", ""),
            role=DeviceRole(dev_raw["role"]),
            site=dev_raw.get("site", "default"),
            management_ip=dev_raw.get("management_ip", ""),
            interfaces=interfaces,
            zones=zones,
            router_id=dev_raw.get("router_id", dev_raw.get("management_ip", "")),
            serial_number=dev_raw.get("serial_number", ""),
        ))

    return Topology(
        name=raw.get("name", "default"),
        sites=sites,
        devices=devices,
    )
