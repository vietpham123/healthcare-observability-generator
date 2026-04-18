"""Kafka output adapter — publishes events to Apache Kafka topics.

Covers FR-808. Requires optional aiokafka dependency.
Install: pip install network-log-generator[kafka]
"""

from __future__ import annotations

import json
import logging
from datetime import timezone

from netloggen.core.models import FlowRecord, LogEvent, MetricEvent, TrapEvent
from netloggen.outputs.base import BaseOutput

logger = logging.getLogger(__name__)


class KafkaOutput(BaseOutput):
    """Publish events to Kafka topics as JSON messages."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic_prefix: str = "netloggen",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self._producer = None
        self._stats = {"sent": 0, "failed": 0}

    async def connect(self) -> None:
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError:
            raise ImportError(
                "aiokafka is required for Kafka output. "
                "Install with: pip install network-log-generator[kafka]"
            )
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        logger.info(f"Kafka output connected → {self.bootstrap_servers}")

    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None
        logger.info(f"Kafka output stats: {self._stats}")

    async def send_logs(self, events: list[LogEvent]) -> int:
        topic = f"{self.topic_prefix}.logs"
        sent = 0
        for e in events:
            record = {
                "timestamp": e.timestamp.astimezone(timezone.utc).isoformat(),
                "device": e.device, "vendor": e.vendor.value,
                "severity": e.severity.name, "content": e.content,
                "event_type": e.event_type, "site": e.site,
                **e.attributes,
            }
            if await self._send_one(topic, record, e.device):
                sent += 1
        return sent

    async def send_metrics(self, metrics: list[MetricEvent]) -> int:
        topic = f"{self.topic_prefix}.metrics"
        sent = 0
        for m in metrics:
            record = {
                "timestamp": m.timestamp.astimezone(timezone.utc).isoformat(),
                "metric_key": m.metric_key, "value": m.value,
                "device": m.device, **m.dimensions,
            }
            if await self._send_one(topic, record, m.device):
                sent += 1
        return sent

    async def send_traps(self, traps: list[TrapEvent]) -> int:
        topic = f"{self.topic_prefix}.traps"
        sent = 0
        for t in traps:
            record = {
                "timestamp": t.timestamp.astimezone(timezone.utc).isoformat(),
                "device": t.device, "trap_oid": t.trap_oid,
                "trap_name": t.trap_name, **t.varbinds,
            }
            if await self._send_one(topic, record, t.device):
                sent += 1
        return sent

    async def send_flows(self, flows: list[FlowRecord]) -> int:
        topic = f"{self.topic_prefix}.flows"
        sent = 0
        for f in flows:
            record = {
                "timestamp": f.timestamp.astimezone(timezone.utc).isoformat(),
                "device": f.device, "src_ip": f.src_ip, "dst_ip": f.dst_ip,
                "protocol": f.protocol, "bytes_total": f.bytes_total,
            }
            if await self._send_one(topic, record, f.device):
                sent += 1
        return sent

    async def _send_one(self, topic: str, value: dict, key: str) -> bool:
        try:
            await self._producer.send_and_wait(
                topic, value=value, key=key.encode("utf-8")
            )
            self._stats["sent"] += 1
            return True
        except Exception as e:
            logger.warning(f"Kafka send failed: {e}")
            self._stats["failed"] += 1
            return False
