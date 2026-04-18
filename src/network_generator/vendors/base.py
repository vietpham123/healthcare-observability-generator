"""Base vendor class — all vendor generators inherit from this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from netloggen.core.models import Device, LogEvent, Severity, VendorType
from netloggen.core.random_utils import SeededRandom


class BaseVendor(ABC):
    vendor_type: VendorType

    def __init__(self, rng: SeededRandom):
        self.rng = rng

    @abstractmethod
    def generate_event(
        self, event_type: str, params: dict[str, Any], device: Device, timestamp: datetime
    ) -> list[LogEvent]:
        pass

    @abstractmethod
    def supported_event_types(self) -> list[str]:
        pass

    def _make_event(
        self,
        device: Device,
        timestamp: datetime,
        severity: Severity,
        content: str,
        event_type: str,
        log_source: str = "",
        attributes: dict[str, Any] | None = None,
        scenario_id: str = "",
    ) -> LogEvent:
        return LogEvent(
            timestamp=self.rng.jitter_timestamp(timestamp, max_ms=200),
            device=device.hostname,
            vendor=self.vendor_type,
            severity=severity,
            facility=23,  # local7
            content=content,
            event_type=event_type,
            log_source=log_source or self.vendor_type.value,
            attributes=attributes or {},
            scenario_id=scenario_id,
            site=device.site,
            device_role=device.role.value,
            device_model=device.model,
        )

    def _format_syslog_timestamp(self, ts: datetime) -> str:
        """RFC 3164 BSD syslog timestamp: 'Apr 14 10:23:45'"""
        return ts.strftime("%b %d %H:%M:%S")

    def _format_iso_timestamp(self, ts: datetime) -> str:
        """ISO 8601 timestamp with milliseconds."""
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# Registry of vendor generators
_VENDOR_REGISTRY: dict[VendorType, type[BaseVendor]] = {}


def register_vendor(cls: type[BaseVendor]) -> type[BaseVendor]:
    _VENDOR_REGISTRY[cls.vendor_type] = cls
    return cls


def get_vendor(vendor_type: VendorType, rng: SeededRandom) -> BaseVendor:
    if vendor_type not in _VENDOR_REGISTRY:
        raise ValueError(f"No vendor generator registered for {vendor_type}")
    return _VENDOR_REGISTRY[vendor_type](rng)


def get_all_vendors(rng: SeededRandom) -> dict[VendorType, BaseVendor]:
    return {vt: cls(rng) for vt, cls in _VENDOR_REGISTRY.items()}
