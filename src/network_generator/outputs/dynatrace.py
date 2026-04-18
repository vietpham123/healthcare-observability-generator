"""Dynatrace output adapter — sends data directly to Dynatrace APIs.

Uses:
  - Log Ingest API v2 (/api/v2/logs/ingest) for syslog/firewall/SNMP trap logs
  - Metrics API v2 (/api/v2/metrics/ingest) for SNMP metrics and flow aggregates (MINT format)
  - Events API v2 (/api/v2/events/ingest) for SNMP traps as custom events
  - Bizevents API (/api/v2/bizevents/ingest) for incident lifecycle events
"""

from __future__ import annotations

import json
import logging
import os
from datetime import timezone

import aiohttp

from netloggen.core.models import FlowRecord, LogEvent, MetricEvent, TrapEvent
from netloggen.outputs.base import BaseOutput

logger = logging.getLogger(__name__)

_DEFAULT_BATCH_SIZE = 100
_DEFAULT_TIMEOUT = 30


class DynatraceOutput(BaseOutput):
    def __init__(
        self,
        endpoint: str | None = None,
        api_token: str | None = None,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        verify_ssl: bool = True,
    ):
        self.endpoint = (endpoint or os.environ.get("DT_ENDPOINT", "")).rstrip("/")
        self.api_token = api_token or os.environ.get("DT_API_TOKEN", "")
        self.batch_size = batch_size
        self.verify_ssl = verify_ssl
        self._session: aiohttp.ClientSession | None = None
        self._stats = {"logs_sent": 0, "logs_failed": 0, "metrics_sent": 0, "metrics_failed": 0,
                       "traps_sent": 0, "traps_failed": 0, "flows_sent": 0, "flows_failed": 0}

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        return {
            "Authorization": f"Api-Token {self.api_token}",
            "Content-Type": content_type,
        }

    async def connect(self) -> None:
        if not self.endpoint:
            raise ValueError("DT_ENDPOINT not set. Provide endpoint or set DT_ENDPOINT env var.")
        if not self.api_token:
            raise ValueError("DT_API_TOKEN not set. Provide api_token or set DT_API_TOKEN env var.")

        connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=_DEFAULT_TIMEOUT),
        )
        logger.info(f"Dynatrace output connected to {self.endpoint}")

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        logger.info(f"Dynatrace output stats: {self._stats}")

    # --- Log Ingest API v2 ---

    async def send_logs(self, events: list[LogEvent]) -> int:
        if not self._session:
            return 0

        total_sent = 0
        for i in range(0, len(events), self.batch_size):
            batch = events[i : i + self.batch_size]
            payload = [self._log_to_dt(e) for e in batch]

            try:
                async with self._session.post(
                    f"{self.endpoint}/api/v2/logs/ingest",
                    headers=self._headers("application/json; charset=utf-8"),
                    data=json.dumps(payload),
                ) as resp:
                    if resp.status in (200, 204):
                        total_sent += len(batch)
                        self._stats["logs_sent"] += len(batch)
                    else:
                        body = await resp.text()
                        logger.warning(f"Log ingest failed ({resp.status}): {body[:200]}")
                        self._stats["logs_failed"] += len(batch)
            except Exception as e:
                logger.error(f"Log ingest error: {e}")
                self._stats["logs_failed"] += len(batch)

        return total_sent

    def _log_to_dt(self, event: LogEvent) -> dict:
        record = {
            "content": event.content,
            "timestamp": event.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "log.source": event.log_source,
            "severity": _severity_to_dt(event.severity.name),
            "network.device.hostname": event.device,
            "network.device.vendor": event.vendor.value,
            "network.device.role": event.device_role,
            "network.device.model": event.device_model,
            "network.device.site": event.site,
            "network.event.type": event.event_type,
        }
        if event.scenario_id:
            record["network.scenario.id"] = event.scenario_id

        # Add structured attributes
        for k, v in event.attributes.items():
            record[k] = str(v)

        return record

    # --- Metrics API v2 (MINT protocol) ---

    async def send_metrics(self, metrics: list[MetricEvent]) -> int:
        if not self._session:
            return 0

        total_sent = 0
        for i in range(0, len(metrics), self.batch_size):
            batch = metrics[i : i + self.batch_size]
            lines = [self._metric_to_mint(m) for m in batch]
            payload = "\n".join(lines)

            try:
                async with self._session.post(
                    f"{self.endpoint}/api/v2/metrics/ingest",
                    headers=self._headers("text/plain; charset=utf-8"),
                    data=payload,
                ) as resp:
                    if resp.status in (200, 202):
                        total_sent += len(batch)
                        self._stats["metrics_sent"] += len(batch)
                    else:
                        body = await resp.text()
                        logger.warning(f"Metric ingest failed ({resp.status}): {body[:200]}")
                        self._stats["metrics_failed"] += len(batch)
            except Exception as e:
                logger.error(f"Metric ingest error: {e}")
                self._stats["metrics_failed"] += len(batch)

        return total_sent

    def _metric_to_mint(self, m: MetricEvent) -> str:
        dims = ",".join(f'{k}="{v}"' for k, v in m.dimensions.items() if v)
        key = m.metric_key
        if dims:
            key = f"{key},{dims}"

        ts_ms = int(m.timestamp.timestamp() * 1000)

        if m.value_type == "count":
            return f"{key} count,delta={m.value} {ts_ms}"
        else:
            return f"{key} gauge,{m.value} {ts_ms}"

    # --- Events API v2 (for SNMP traps) ---

    async def send_traps(self, traps: list[TrapEvent]) -> int:
        if not self._session:
            return 0

        total_sent = 0
        for trap in traps:
            payload = {
                "eventType": "CUSTOM_INFO" if trap.severity.value >= 4 else "CUSTOM_ALERT",
                "title": f"SNMP Trap: {trap.trap_name} on {trap.device}",
                "timeout": 15,
                "properties": {
                    "network.device.hostname": trap.device,
                    "network.trap.oid": trap.trap_oid,
                    "network.trap.name": trap.trap_name,
                    "network.trap.severity": trap.severity.name.lower(),
                    "network.device.site": trap.site,
                    **{k: str(v) for k, v in trap.varbinds.items()},
                    **trap.attributes,
                },
            }

            try:
                async with self._session.post(
                    f"{self.endpoint}/api/v2/events/ingest",
                    headers=self._headers(),
                    data=json.dumps(payload),
                ) as resp:
                    if resp.status in (200, 201):
                        total_sent += 1
                        self._stats["traps_sent"] += 1
                    else:
                        body = await resp.text()
                        logger.warning(f"Event ingest failed ({resp.status}): {body[:200]}")
                        self._stats["traps_failed"] += 1
            except Exception as e:
                logger.error(f"Event ingest error: {e}")
                self._stats["traps_failed"] += 1

        return total_sent

    # --- Flows as log events + aggregated metrics ---

    async def send_flows(self, flows: list[FlowRecord]) -> int:
        if not self._session:
            return 0

        # Send as log events for per-flow drill-down
        log_events = []
        for f in flows:
            content = (
                f"NetFlow: {f.src_ip}:{f.src_port} -> {f.dst_ip}:{f.dst_port} "
                f"{f.protocol.upper()} {f.bytes_total}B {f.packets_total}pkts"
            )
            log_events.append({
                "content": content,
                "timestamp": f.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "log.source": "netflow",
                "severity": "NONE",
                "network.flow.src_ip": f.src_ip,
                "network.flow.dst_ip": f.dst_ip,
                "network.flow.src_port": str(f.src_port),
                "network.flow.dst_port": str(f.dst_port),
                "network.flow.protocol": f.protocol,
                "network.flow.bytes": str(f.bytes_total),
                "network.flow.bytes_in": str(f.bytes_in),
                "network.flow.bytes_out": str(f.bytes_out),
                "network.flow.packets": str(f.packets_total),
                "network.flow.tcp_flags": str(f.tcp_flags),
                "network.flow.src_as": str(f.src_as),
                "network.flow.dst_as": str(f.dst_as),
                "network.flow.src.latitude": str(f.src_latitude),
                "network.flow.src.longitude": str(f.src_longitude),
                "network.flow.src.country": f.src_country,
                "network.flow.dst.latitude": str(f.dst_latitude),
                "network.flow.dst.longitude": str(f.dst_longitude),
                "network.flow.dst.country": f.dst_country,
                "network.device.hostname": f.device,
                "network.device.site": f.site,
            })

        total_sent = 0
        for i in range(0, len(log_events), self.batch_size):
            batch = log_events[i : i + self.batch_size]
            try:
                async with self._session.post(
                    f"{self.endpoint}/api/v2/logs/ingest",
                    headers=self._headers("application/json; charset=utf-8"),
                    data=json.dumps(batch),
                ) as resp:
                    if resp.status in (200, 204):
                        total_sent += len(batch)
                        self._stats["flows_sent"] += len(batch)
                    else:
                        body = await resp.text()
                        logger.warning(f"Flow log ingest failed ({resp.status}): {body[:200]}")
                        self._stats["flows_failed"] += len(batch)
            except Exception as e:
                logger.error(f"Flow ingest error: {e}")
                self._stats["flows_failed"] += len(batch)

        return total_sent

    # --- Bizevents API (FR-807) ---

    async def send_bizevents(self, events: list[dict]) -> int:
        """Send business events to Dynatrace Bizevents API."""
        if not self._session or not events:
            return 0
        total_sent = 0
        for i in range(0, len(events), self.batch_size):
            batch = events[i: i + self.batch_size]
            try:
                async with self._session.post(
                    f"{self.endpoint}/api/v2/bizevents/ingest",
                    headers=self._headers("application/cloudevents-batch+json"),
                    data=json.dumps(batch),
                ) as resp:
                    if resp.status in (200, 202, 204):
                        total_sent += len(batch)
                    else:
                        body = await resp.text()
                        logger.warning(f"Bizevent ingest failed ({resp.status}): {body[:200]}")
            except Exception as e:
                logger.error(f"Bizevent ingest error: {e}")
        return total_sent

    @property
    def stats(self) -> dict:
        return dict(self._stats)


def _severity_to_dt(severity_name: str) -> str:
    mapping = {
        "EMERGENCY": "ERROR",
        "ALERT": "ERROR",
        "CRITICAL": "ERROR",
        "ERROR": "ERROR",
        "WARNING": "WARN",
        "NOTICE": "INFO",
        "INFO": "INFO",
        "DEBUG": "DEBUG",
    }
    return mapping.get(severity_name, "NONE")
