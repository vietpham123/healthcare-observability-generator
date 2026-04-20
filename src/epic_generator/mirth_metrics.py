"""Mirth Connect channel metrics emitter.

Sends synthetic Mirth Connect integration engine metrics to Dynatrace
via the Metrics Ingest API v2 (MINT line protocol).

Channels simulated:
  LAB-RESULTS-IN    HL7v2 inbound   - Lab results from analyzers
  ADT-OUT           HL7v2 outbound  - ADT notifications to downstream
  PHARMACY-ORDERS   HL7v2 bidir     - Pharmacy order communication
  RADIOLOGY-RESULTS HL7v2 inbound   - Radiology results from PACS
  SCHEDULING-OUT    FHIR  outbound  - FHIR scheduling notifications

Metrics per channel per tick:
  healthcare.mirth.channel.messages.received  count,delta
  healthcare.mirth.channel.messages.sent      count,delta
  healthcare.mirth.channel.messages.errors    count,delta
  healthcare.mirth.channel.messages.filtered  count,delta
  healthcare.mirth.channel.queue.depth        gauge
  healthcare.mirth.channel.status             gauge (1=running, 0=stopped)
"""

import logging
import random
import ssl
import urllib.request

logger = logging.getLogger("epic_generator.mirth_metrics")

CHANNELS = [
    {"name": "LAB-RESULTS-IN", "type": "HL7v2", "direction": "inbound"},
    {"name": "ADT-OUT", "type": "HL7v2", "direction": "outbound"},
    {"name": "PHARMACY-ORDERS", "type": "HL7v2", "direction": "bidirectional"},
    {"name": "RADIOLOGY-RESULTS", "type": "HL7v2", "direction": "inbound"},
    {"name": "SCHEDULING-OUT", "type": "FHIR", "direction": "outbound"},
]


class MirthMetricsEmitter:
    """Emit Mirth Connect channel metrics via Dynatrace Metrics API v2."""

    def __init__(self, dt_endpoint, dt_token, site="kcrmc-main"):
        base = dt_endpoint.rstrip("/")
        self.endpoint = base + "/api/v2/metrics/ingest"
        self.token = dt_token
        self.site = site
        self._tick = 0
        self._queue_depths = {ch["name"]: 0 for ch in CHANNELS}
        self._ctx = ssl.create_default_context()

    def tick(self, scenario=None):
        """Generate and send metrics for one tick. Returns True on success."""
        if scenario == "hl7_interface_failure":
            factor = min(1.0, self._tick / 60.0)
            lines = self._generate_failure_tick(factor)
        elif scenario == "core_switch_failure":
            lines = self._generate_failure_tick(0.3)
        else:
            lines = self._generate_baseline_tick()
        self._tick += 1
        return self._send(lines)

    def reset(self):
        """Reset internal state (call when scenario changes)."""
        self._tick = 0
        self._queue_depths = {ch["name"]: 0 for ch in CHANNELS}

    def _generate_baseline_tick(self):
        """Normal Mirth metrics: messages flowing, queues near-empty, rare errors."""
        lines = []
        for ch in CHANNELS:
            name = ch["name"]
            received = random.randint(15, 45)
            sent = received - random.randint(0, 2)
            errors = 1 if random.random() < 0.05 else 0
            filtered = random.randint(0, 3)
            queue = max(0, self._queue_depths[name] + random.randint(-2, 2))
            self._queue_depths[name] = min(queue, 5)
            dims = self._dims(ch)
            lines.append(f"healthcare.mirth.channel.messages.received,{dims} count,delta={received}")
            lines.append(f"healthcare.mirth.channel.messages.sent,{dims} count,delta={sent}")
            lines.append(f"healthcare.mirth.channel.messages.errors,{dims} count,delta={errors}")
            lines.append(f"healthcare.mirth.channel.messages.filtered,{dims} count,delta={filtered}")
            lines.append(f"healthcare.mirth.channel.queue.depth,{dims} gauge,{self._queue_depths[name]}")
            lines.append(f"healthcare.mirth.channel.status,{dims} gauge,1")
        return "\n".join(lines)

    def _generate_failure_tick(self, severity):
        """Degraded Mirth metrics simulating HL7 interface failure."""
        lines = []
        for ch in CHANNELS:
            name = ch["name"]
            dims = self._dims(ch)
            if ch["type"] == "HL7v2":
                received = random.randint(15, 45)
                sent_rate = max(0.0, 1.0 - severity * 0.9)
                sent = max(0, int(received * sent_rate) + random.randint(-1, 1))
                errors = int(received * severity * 0.7) + random.randint(0, 3)
                queue_delta = int(20 * severity) + random.randint(-2, 5)
                self._queue_depths[name] = min(
                    self._queue_depths[name] + queue_delta, 5000
                )
                status = 0 if severity > 0.8 else 1
            else:
                received = random.randint(10, 30)
                sent = received - random.randint(0, int(3 * severity + 1))
                errors = random.randint(0, int(5 * severity + 1))
                self._queue_depths[name] = min(
                    max(0, self._queue_depths[name] + random.randint(-1, int(5 * severity + 1))),
                    500
                )
                status = 1
            lines.append(f"healthcare.mirth.channel.messages.received,{dims} count,delta={received}")
            lines.append(f"healthcare.mirth.channel.messages.sent,{dims} count,delta={sent}")
            lines.append(f"healthcare.mirth.channel.messages.errors,{dims} count,delta={errors}")
            lines.append(f"healthcare.mirth.channel.messages.filtered,{dims} count,delta=0")
            lines.append(f"healthcare.mirth.channel.queue.depth,{dims} gauge,{self._queue_depths[name]}")
            lines.append(f"healthcare.mirth.channel.status,{dims} gauge,{status}")
        return "\n".join(lines)

    def _dims(self, ch):
        name = ch["name"]
        ctype = ch["type"]
        direction = ch["direction"]
        site = self.site
        return f'channel.name="{name}",channel.type="{ctype}",channel.direction="{direction}",healthcare.site="{site}"'

    def _send(self, metric_lines):
        """POST metric lines to Dynatrace Metrics API v2."""
        try:
            data = metric_lines.encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={
                    "Authorization": f"Api-Token {self.token}",
                    "Content-Type": "text/plain; charset=utf-8",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, context=self._ctx, timeout=10) as resp:
                return resp.status == 202
        except Exception as e:
            logger.warning("Mirth metrics send failed: %s", e)
            return False
