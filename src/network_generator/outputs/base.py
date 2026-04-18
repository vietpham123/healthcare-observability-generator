"""Base output adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from netloggen.core.models import FlowRecord, LogEvent, MetricEvent, TrapEvent


class BaseOutput(ABC):
    @abstractmethod
    async def send_logs(self, events: list[LogEvent]) -> int:
        """Send log events. Returns count of successfully sent."""
        pass

    @abstractmethod
    async def send_metrics(self, metrics: list[MetricEvent]) -> int:
        """Send metric events. Returns count of successfully sent."""
        pass

    @abstractmethod
    async def send_traps(self, traps: list[TrapEvent]) -> int:
        """Send trap events. Returns count of successfully sent."""
        pass

    @abstractmethod
    async def send_flows(self, flows: list[FlowRecord]) -> int:
        """Send flow records. Returns count of successfully sent."""
        pass

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass
