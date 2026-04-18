"""Syslog output adapter — sends logs via UDP, TCP, or TLS to standard syslog receivers.

Supports RFC 3164 (BSD) and RFC 5424 (IETF structured) framing.
Covers FR-801 and FR-215.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import ssl
from datetime import timezone

from netloggen.core.models import FlowRecord, LogEvent, MetricEvent, TrapEvent
from netloggen.outputs.base import BaseOutput

logger = logging.getLogger(__name__)

_SEVERITY_MAP = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7}


class SyslogOutput(BaseOutput):
    """Send syslog messages to a remote receiver via UDP, TCP, or TLS."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 514,
        protocol: str = "udp",
        syslog_format: str = "rfc3164",
        verify_ssl: bool = True,
        ca_file: str | None = None,
    ):
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.syslog_format = syslog_format.lower()
        self.verify_ssl = verify_ssl
        self.ca_file = ca_file
        self._sock: socket.socket | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._stats = {"sent": 0, "failed": 0}

    async def connect(self) -> None:
        if self.protocol == "udp":
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setblocking(False)
            logger.info(f"Syslog UDP output ready → {self.host}:{self.port}")
        elif self.protocol in ("tcp", "tls"):
            ssl_ctx = None
            if self.protocol == "tls":
                ssl_ctx = ssl.create_default_context()
                if self.ca_file:
                    ssl_ctx.load_verify_locations(self.ca_file)
                if not self.verify_ssl:
                    ssl_ctx.check_hostname = False
                    ssl_ctx.verify_mode = ssl.CERT_NONE
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port, ssl=ssl_ctx
            )
            logger.info(f"Syslog {self.protocol.upper()} output connected → {self.host}:{self.port}")
        else:
            raise ValueError(f"Unsupported syslog protocol: {self.protocol}")

    async def close(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
        if self._sock:
            self._sock.close()
            self._sock = None
        logger.info(f"Syslog output stats: {self._stats}")

    async def send_logs(self, events: list[LogEvent]) -> int:
        sent = 0
        for event in events:
            msg = self._format_message(event)
            try:
                await self._send_raw(msg)
                sent += 1
                self._stats["sent"] += 1
            except Exception as e:
                logger.warning(f"Syslog send failed: {e}")
                self._stats["failed"] += 1
        return sent

    async def send_metrics(self, metrics: list[MetricEvent]) -> int:
        return 0  # Metrics not sent via syslog

    async def send_traps(self, traps: list[TrapEvent]) -> int:
        return 0  # Traps sent via SNMP adapter, not syslog

    async def send_flows(self, flows: list[FlowRecord]) -> int:
        return 0  # Flows sent via NetFlow adapter, not syslog

    def _format_message(self, event: LogEvent) -> bytes:
        if self.syslog_format == "rfc5424":
            return self._format_rfc5424(event)
        return self._format_rfc3164(event)

    def _format_rfc3164(self, event: LogEvent) -> bytes:
        """RFC 3164 BSD syslog: <PRI>TIMESTAMP HOSTNAME MSG"""
        pri = event.pri
        ts = event.timestamp.astimezone(timezone.utc)
        ts_str = ts.strftime("%b %d %H:%M:%S")
        msg = f"<{pri}>{ts_str} {event.device} {event.content}"
        return msg.encode("utf-8", errors="replace")

    def _format_rfc5424(self, event: LogEvent) -> bytes:
        """RFC 5424 IETF syslog: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID SD MSG"""
        pri = event.pri
        ts = event.timestamp.astimezone(timezone.utc)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        hostname = event.device
        app_name = event.log_source or "-"
        proc_id = "-"
        msg_id = event.event_type or "-"

        # Structured data
        sd_parts = []
        sd_params = {
            "vendor": event.vendor.value,
            "site": event.site,
            "role": event.device_role,
        }
        if event.scenario_id:
            sd_params["scenarioId"] = event.scenario_id
        # Add event attributes to structured data
        for k, v in event.attributes.items():
            safe_key = k.replace(".", "_").replace(" ", "_")[:32]
            sd_params[safe_key] = str(v)

        param_str = " ".join(
            f'{k}="{_sd_escape(str(v))}"' for k, v in sd_params.items() if v
        )
        sd = f'[netloggen@49876 {param_str}]' if param_str else "-"

        msg = f"<{pri}>1 {ts_str} {hostname} {app_name} {proc_id} {msg_id} {sd} {event.content}"
        return msg.encode("utf-8", errors="replace")

    async def _send_raw(self, data: bytes) -> None:
        if self.protocol == "udp":
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._sock.sendto, data, (self.host, self.port)
            )
        elif self._writer:
            # TCP/TLS: octet-counting framing (RFC 5425)
            framed = f"{len(data)} ".encode() + data + b"\n"
            self._writer.write(framed)
            await self._writer.drain()

    @property
    def stats(self) -> dict:
        return dict(self._stats)


def _sd_escape(value: str) -> str:
    """Escape special characters in RFC 5424 structured data values."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("]", "\\]")
