"""Clock and time management for the generator."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum


class ClockMode(str, Enum):
    REALTIME = "realtime"
    ACCELERATED = "accelerated"
    BATCH = "batch"


class Clock:
    def __init__(
        self,
        mode: ClockMode = ClockMode.REALTIME,
        acceleration: float = 1.0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ):
        self.mode = mode
        self.acceleration = max(acceleration, 0.01)
        self.start_time = start_time or datetime.now(timezone.utc)
        self.end_time = end_time
        self._epoch = time.monotonic()
        self._sim_epoch = self.start_time

    def now(self) -> datetime:
        if self.mode == ClockMode.REALTIME:
            return datetime.now(timezone.utc)
        elif self.mode == ClockMode.ACCELERATED:
            elapsed_real = time.monotonic() - self._epoch
            elapsed_sim = elapsed_real * self.acceleration
            return self._sim_epoch.replace(
                tzinfo=timezone.utc
            ) + __import__("datetime").timedelta(seconds=elapsed_sim)
        else:  # BATCH
            return self._sim_epoch

    def advance_batch(self, seconds: float) -> None:
        if self.mode == ClockMode.BATCH:
            self._sim_epoch += __import__("datetime").timedelta(seconds=seconds)

    def is_finished(self) -> bool:
        if self.end_time is None:
            return False
        return self.now() >= self.end_time

    def sleep_interval(self, sim_seconds: float) -> float:
        if self.mode == ClockMode.REALTIME:
            return sim_seconds
        elif self.mode == ClockMode.ACCELERATED:
            return sim_seconds / self.acceleration
        else:
            return 0.0
