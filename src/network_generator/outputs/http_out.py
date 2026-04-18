"""HTTP webhook output adapter — sends events via POST to configurable endpoints.

Covers FR-809. Supports custom headers and JSON payload.
"""

from __future__ import annotations

import json
import logging
from datetime import timezone

import aiohttp

from netloggen.core.models import FlowRecord, LogEvent, MetricEvent, TrapEvent
from netloggen.outputs.base import BaseOutput

logger = logging.getLogger(__name__)


class HTTPWebhookOutput(BaseOutput):
    """Send all event types as JSON POST requests to a webhook endpoint."""

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        batch_size: int = 100,
        verify_ssl: bool = True,
    ):
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.batch_size = batch_size
        self.verify_ssl = verify_ssl
        self._session: aiohttp.ClientSession | None = None
        self._stats = {"sent": 0, "failed": 0}

    async def connect(self) -> None:
        connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
        )
        logger.info(f"HTTP webhook output connected → {self.url}")

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        logger.info(f"HTTP webhook stats: {self._stats}")

    async def send_logs(self, events: list[LogEvent]) -> int:
        return await self._send_batch([
            {
                "type": "log",
                "timestamp": e.timestamp.astimezone(timezone.utc).isoformat(),
                "device": e.device,
                "vendor": e.vendor.value,
                "severity": (e.severity.name if hasattr(e.severity, "name") else str(e.severity)),
                "content": e.content,
                "event_type": e.event_type,
                "site": e.site,
                **e.attributes,
            }
            for e in events
        ])

    async def send_metrics(self, metrics: list[MetricEvent]) -> int:
        return await self._send_batch([
            {
                "type": "metric",
                "timestamp": m.timestamp.astimezone(timezone.utc).isoformat(),
                "metric_key": m.metric_key,
                "value": m.value,
                "device": m.device,
                **m.dimensions,
            }
            for m in metrics
        ])

    async def send_traps(self, traps: list[TrapEvent]) -> int:
        return await self._send_batch([
            {
                "type": "trap",
                "timestamp": t.timestamp.astimezone(timezone.utc).isoformat(),
                "device": t.device,
                "trap_oid": t.trap_oid,
                "trap_name": t.trap_name,
                **t.varbinds,
            }
            for t in traps
        ])

    async def send_flows(self, flows: list[FlowRecord]) -> int:
        return await self._send_batch([
            {
                "type": "flow",
                "timestamp": f.timestamp.astimezone(timezone.utc).isoformat(),
                "device": f.device,
                "src_ip": f.src_ip,
                "dst_ip": f.dst_ip,
                "src_port": f.src_port,
                "dst_port": f.dst_port,
                "protocol": f.protocol,
                "bytes_total": f.bytes_total,
            }
            for f in flows
        ])

    async def _send_batch(self, records: list[dict]) -> int:
        if not self._session or not records:
            return 0
        sent = 0
        for i in range(0, len(records), self.batch_size):
            batch = records[i: i + self.batch_size]
            try:
                async with self._session.post(
                    self.url, headers=self.headers, data=json.dumps(batch)
                ) as resp:
                    if resp.status < 300:
                        sent += len(batch)
                        self._stats["sent"] += len(batch)
                    else:
                        self._stats["failed"] += len(batch)
                        body = await resp.text()
                        logger.warning(f"Webhook failed ({resp.status}): {body[:200]}")
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                self._stats["failed"] += len(batch)
        return sent
