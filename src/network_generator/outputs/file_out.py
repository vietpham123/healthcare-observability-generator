"""File output adapter — writes generated data to JSON, CSV, or raw syslog files.

Supports formats: json (NDJSON), csv (RFC 4180), raw (vendor-formatted syslog lines).
Covers FR-804.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import timezone
from pathlib import Path

from netloggen.core.models import FlowRecord, LogEvent, MetricEvent, TrapEvent
from netloggen.outputs.base import BaseOutput

_LOG_CSV_FIELDS = [
    "timestamp", "device", "vendor", "severity", "facility", "event_type",
    "log_source", "site", "device_role", "device_model", "scenario_id", "content",
]
_METRIC_CSV_FIELDS = [
    "timestamp", "device", "site", "metric_key", "value", "value_type",
    "vendor", "interface", "model", "role",
]
_FLOW_CSV_FIELDS = [
    "timestamp", "device", "site", "src_ip", "dst_ip", "src_port", "dst_port",
    "protocol", "bytes_total", "packets_total", "tcp_flags", "src_as", "dst_as",
    "input_interface", "output_interface",
]


class FileOutput(BaseOutput):
    def __init__(self, output_dir: str = "output", format: str = "json"):
        self.output_dir = Path(output_dir)
        self.format = format.lower()
        self._log_file = None
        self._metric_file = None
        self._trap_file = None
        self._flow_file = None
        self._csv_headers_written = {"logs": False, "metrics": False, "traps": False, "flows": False}

    async def connect(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ext = "log" if self.format == "raw" else self.format
        self._log_file = open(self.output_dir / f"logs.{ext}", "a")
        self._metric_file = open(self.output_dir / f"metrics.{ext}", "a")
        self._trap_file = open(self.output_dir / f"traps.{ext}", "a")
        self._flow_file = open(self.output_dir / f"flows.{ext}", "a")

        # Write CSV headers if new files
        if self.format == "csv":
            for name, fh, fields in [
                ("logs", self._log_file, _LOG_CSV_FIELDS),
                ("metrics", self._metric_file, _METRIC_CSV_FIELDS),
                ("flows", self._flow_file, _FLOW_CSV_FIELDS),
            ]:
                if fh.tell() == 0:
                    fh.write(",".join(fields) + "\n")
                    self._csv_headers_written[name] = True

    async def close(self) -> None:
        for f in [self._log_file, self._metric_file, self._trap_file, self._flow_file]:
            if f:
                f.close()

    async def send_logs(self, events: list[LogEvent]) -> int:
        if not self._log_file:
            return 0
        for event in events:
            if self.format == "raw":
                # Raw syslog line: <PRI>TIMESTAMP HOSTNAME MSG
                pri = event.pri
                ts = event.timestamp.astimezone(timezone.utc).strftime("%b %d %H:%M:%S")
                self._log_file.write(f"<{pri}>{ts} {event.device} {event.content}\n")
            elif self.format == "csv":
                row = {f: "" for f in _LOG_CSV_FIELDS}
                row["timestamp"] = event.timestamp.isoformat()
                row["device"] = event.device
                row["vendor"] = event.vendor.value
                row["severity"] = event.severity.name
                row["facility"] = str(event.facility)
                row["event_type"] = event.event_type
                row["log_source"] = event.log_source
                row["site"] = event.site
                row["device_role"] = event.device_role
                row["device_model"] = event.device_model
                row["scenario_id"] = event.scenario_id
                row["content"] = event.content
                buf = io.StringIO()
                writer = csv.DictWriter(buf, _LOG_CSV_FIELDS, extrasaction="ignore")
                writer.writerow(row)
                self._log_file.write(buf.getvalue())
            else:  # json
                record = {
                    "timestamp": event.timestamp.isoformat(),
                    "device": event.device,
                    "vendor": event.vendor.value,
                    "severity": event.severity.name,
                    "content": event.content,
                    "event_type": event.event_type,
                    "log_source": event.log_source,
                    "site": event.site,
                    "device_role": event.device_role,
                    **event.attributes,
                }
                if event.scenario_id:
                    record["scenario_id"] = event.scenario_id
                self._log_file.write(json.dumps(record) + "\n")
        self._log_file.flush()
        return len(events)

    async def send_metrics(self, metrics: list[MetricEvent]) -> int:
        if not self._metric_file:
            return 0
        for m in metrics:
            record = {
                "timestamp": m.timestamp.isoformat(),
                "metric_key": m.metric_key,
                "value": m.value,
                "value_type": m.value_type,
                "device": m.device,
                "site": m.site,
                **m.dimensions,
            }
            self._metric_file.write(json.dumps(record) + "\n")
        self._metric_file.flush()
        return len(metrics)

    async def send_traps(self, traps: list[TrapEvent]) -> int:
        if not self._trap_file:
            return 0
        for t in traps:
            record = {
                "timestamp": t.timestamp.isoformat(),
                "device": t.device,
                "trap_oid": t.trap_oid,
                "trap_name": t.trap_name,
                "severity": t.severity.name,
                "site": t.site,
                **t.varbinds,
                **t.attributes,
            }
            self._trap_file.write(json.dumps(record) + "\n")
        self._trap_file.flush()
        return len(traps)

    async def send_flows(self, flows: list[FlowRecord]) -> int:
        if not self._flow_file:
            return 0
        for f in flows:
            record = {
                "timestamp": f.timestamp.isoformat(),
                "device": f.device,
                "src_ip": f.src_ip,
                "dst_ip": f.dst_ip,
                "src_port": f.src_port,
                "dst_port": f.dst_port,
                "protocol": f.protocol,
                "bytes_total": f.bytes_total,
                "packets_total": f.packets_total,
                "tcp_flags": f.tcp_flags,
                "input_interface": f.input_interface,
                "output_interface": f.output_interface,
                "src_as": f.src_as,
                "dst_as": f.dst_as,
                "site": f.site,
            }
            self._flow_file.write(json.dumps(record) + "\n")
        self._flow_file.flush()
        return len(flows)
