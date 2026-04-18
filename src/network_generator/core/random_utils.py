"""Seeded random utilities for reproducible, realistic data generation."""

from __future__ import annotations

import ipaddress
import random
from datetime import datetime, timedelta


class SeededRandom:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def jitter(self, base_seconds: float, variance: float = 0.2) -> float:
        low = base_seconds * (1.0 - variance)
        high = base_seconds * (1.0 + variance)
        return self.rng.uniform(low, high)

    def jitter_timestamp(self, ts: datetime, max_ms: int = 500) -> datetime:
        offset_ms = self.rng.randint(-max_ms, max_ms)
        return ts + timedelta(milliseconds=offset_ms)

    def choice(self, seq):
        return self.rng.choice(seq)

    def choices(self, seq, k: int = 1):
        return self.rng.choices(seq, k=k)

    def randint(self, a: int, b: int) -> int:
        return self.rng.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        return self.rng.uniform(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        return self.rng.gauss(mu, sigma)

    def random_ip(self, subnet: str = "10.0.0.0/8") -> str:
        network = ipaddress.IPv4Network(subnet, strict=False)
        hosts = list(network.hosts())
        if not hosts:
            return str(network.network_address)
        return str(self.rng.choice(hosts))

    def random_port(self, ephemeral: bool = True) -> int:
        if ephemeral:
            return self.rng.randint(49152, 65535)
        return self.rng.choice([80, 443, 22, 53, 25, 110, 143, 993, 3306, 5432, 8080, 8443])

    def random_mac(self) -> str:
        octets = [self.rng.randint(0, 255) for _ in range(6)]
        octets[0] = octets[0] & 0xFE  # unicast
        return ":".join(f"{o:02x}" for o in octets)

    def random_bytes_count(self, min_bytes: int = 100, max_bytes: int = 1_000_000) -> int:
        return self.rng.randint(min_bytes, max_bytes)

    def weighted_choice(self, items: list, weights: list[float]):
        return self.rng.choices(items, weights=weights, k=1)[0]

    def should_occur(self, probability: float) -> bool:
        return self.rng.random() < probability

    def diurnal_factor(self, hour: int) -> float:
        """Return a 0.0–1.0 factor based on time of day for realistic traffic patterns."""
        # Business hours peak, overnight low
        if 8 <= hour <= 17:
            return 0.7 + self.rng.uniform(0, 0.3)
        elif 18 <= hour <= 21:
            return 0.3 + self.rng.uniform(0, 0.2)
        elif 22 <= hour or hour <= 5:
            return 0.05 + self.rng.uniform(0, 0.1)
        else:  # 6-7 AM ramp up
            return 0.3 + self.rng.uniform(0, 0.3)
