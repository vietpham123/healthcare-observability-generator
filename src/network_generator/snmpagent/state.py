"""Shared state writer — exports live device state to a JSON file
that the SNMP agent reads to answer polls.

Written by the generator's tick loop, read by the standalone SNMP agent process.
State file uses atomic write (write-to-temp + rename) to avoid partial reads.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from netloggen.core.models import Device, MetricEvent, Topology

logger = logging.getLogger(__name__)

DEFAULT_STATE_PATH = "/tmp/netloggen-snmp-state.json"


def export_device_state(
    topology: Topology,
    metrics: list[MetricEvent],
    state_path: str = DEFAULT_STATE_PATH,
) -> None:
    """Write current device state to a JSON file (atomic write).

    Called once per tick by the generator. The SNMP agent polls this file.
    """
    state = _build_state(topology, metrics)
    _atomic_write(state_path, state)


def _build_state(topology: Topology, metrics: list[MetricEvent]) -> dict[str, Any]:
    """Build the shared state dict from topology + latest metrics."""
    devices: dict[str, Any] = {}

    for device in topology.devices:
        dev_state: dict[str, Any] = {
            "hostname": device.hostname,
            "vendor": device.vendor.value,
            "model": device.model,
            "os_version": device.os_version,
            "role": device.role.value,
            "site": device.site,
            "management_ip": device.management_ip,
            "serial_number": device.serial_number,
            "cpu_utilization": device.cpu_utilization,
            "memory_utilization": device.memory_utilization,
            "uptime_seconds": device.uptime_seconds,
            "session_count": device.session_count,
            "interfaces": {},
        }

        for iface in device.interfaces:
            dev_state["interfaces"][iface.name] = {
                "if_index": iface.if_index,
                "speed": iface.speed,
                "status": iface.status.value,
                "description": iface.description,
                "ip_address": iface.ip_address,
            }

        devices[device.hostname] = dev_state

    # Overlay latest metric values per device/interface
    for m in metrics:
        dev_key = m.device
        if dev_key not in devices:
            continue

        iface_name = m.dimensions.get("interface")
        if iface_name and iface_name in devices[dev_key]["interfaces"]:
            # Interface-level metric
            iface_state = devices[dev_key]["interfaces"][iface_name]
            iface_state[m.metric_key] = m.value
        else:
            # Device-level metric
            devices[dev_key][m.metric_key] = m.value

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_count": len(devices),
        "devices": devices,
    }


def _atomic_write(path: str, data: dict) -> None:
    """Write JSON atomically: temp file + rename."""
    dir_path = os.path.dirname(path) or "/tmp"
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp", prefix=".snmpstate-")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, separators=(",", ":"))
        os.replace(tmp_path, path)
    except Exception:
        logger.exception(f"Failed to write SNMP state to {path}")
        # Clean up temp file if rename failed
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def load_device_state(state_path: str = DEFAULT_STATE_PATH) -> dict[str, Any]:
    """Read the shared state file. Used by the SNMP agent."""
    try:
        with open(state_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"State file not found: {state_path}")
        return {"devices": {}}
    except json.JSONDecodeError:
        logger.warning(f"Corrupt state file: {state_path}")
        return {"devices": {}}
