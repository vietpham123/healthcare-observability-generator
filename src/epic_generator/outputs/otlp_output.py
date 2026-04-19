import datetime
import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class OTLPOutput:
    """Format and push logs as OpenTelemetry Protocol (OTLP) log records,
    compatible with Dynatrace Log Ingest API v2.

    Supports two output modes:
    - "dynatrace": Uses Dynatrace-specific log ingest format
    - "otlp": Uses standard OTLP JSON export format
    """

    def __init__(self, endpoint, api_token=None, mode="dynatrace",
                 batch_size=50, max_retries=3, default_attributes=None):
        """
        Args:
            endpoint: Full URL of the log ingest endpoint.
            api_token: API token for authentication.
            mode: "dynatrace" or "otlp".
            batch_size: Events to buffer before flush.
            max_retries: Retry attempts on failure.
            default_attributes: Dict of attributes to add to every log record.
        """
        self.endpoint = endpoint
        self.api_token = api_token
        self.mode = mode
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.default_attributes = default_attributes or {}

        self._headers = {"Content-Type": "application/json; charset=utf-8"}
        if api_token:
            if mode == "dynatrace":
                self._headers["Authorization"] = f"Api-Token {api_token}"
            else:
                self._headers["Authorization"] = f"Bearer {api_token}"

        self._buffer = []

    def write(self, formatted_event, attributes=None):
        """Buffer a log event with optional per-event attributes.

        Args:
            formatted_event: str log content.
            attributes: optional dict of event-specific attributes.
        """
        record = self._build_record(formatted_event, attributes)
        self._buffer.append(record)

        if len(self._buffer) >= self.batch_size:
            self.flush()

    def write_with_context(self, formatted_event, event_type=None,
                           user_id=None, patient_mrn=None, severity="INFO",
                           host=None):
        """Write a log event with Epic-specific context attributes.

        Convenience method that builds Dynatrace-friendly attributes.
        """
        attributes = {}
        if event_type:
            attributes["epic.event.type"] = event_type
        if user_id:
            attributes["epic.user.id"] = user_id
        if patient_mrn:
            attributes["epic.patient.mrn"] = patient_mrn
        if host:
            attributes["dt.entity.host"] = host

        record = self._build_record(formatted_event, attributes, severity)
        self._buffer.append(record)

        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        """POST buffered log records to the endpoint."""
        if not self._buffer:
            return

        if self.mode == "dynatrace":
            payload = self._build_dynatrace_payload()
        else:
            payload = self._build_otlp_payload()

        body = json.dumps(payload).encode("utf-8")

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    self.endpoint,
                    data=body,
                    headers=self._headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    status = resp.getcode()
                    if status < 300:
                        logger.debug("OTLP flush: sent %d records (HTTP %d)",
                                     len(self._buffer), status)
                        self._buffer.clear()
                        return
                    else:
                        logger.warning("OTLP flush: HTTP %d", status)
            except urllib.error.HTTPError as e:
                logger.warning("OTLP flush attempt %d/%d: HTTP %d",
                               attempt, self.max_retries, e.code)
            except (urllib.error.URLError, OSError) as e:
                logger.warning("OTLP flush attempt %d/%d: %s",
                               attempt, self.max_retries, e)

        logger.error("OTLP flush failed after %d attempts, dropping %d records",
                     self.max_retries, len(self._buffer))
        self._buffer.clear()

    def _build_record(self, content, attributes=None, severity="INFO"):
        """Build a single log record dict."""
        if self.mode == "dynatrace":
            record = {
                "content": content,
                "log.source": "epic-simulator",
                "severity": severity,
                "timestamp": datetime.datetime.now().isoformat(),
            }
            record.update(self.default_attributes)
            if attributes:
                record.update(attributes)
            return record
        else:
            # OTLP format
            record = {
                "timeUnixNano": str(int(datetime.datetime.now().timestamp() * 1e9)),
                "severityText": severity,
                "body": {"stringValue": content},
                "attributes": [],
            }
            all_attrs = {**self.default_attributes, **(attributes or {})}
            all_attrs["log.source"] = "epic-simulator"
            for k, v in all_attrs.items():
                record["attributes"].append({
                    "key": k,
                    "value": {"stringValue": str(v)},
                })
            return record

    def _build_dynatrace_payload(self):
        """Build Dynatrace Log Ingest v2 payload."""
        return self._buffer

    def _build_otlp_payload(self):
        """Build OTLP JSON export payload."""
        return {
            "resourceLogs": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "epic-simulator"}},
                            {"key": "service.version", "value": {"stringValue": "2.0.0"}},
                        ]
                    },
                    "scopeLogs": [
                        {
                            "scope": {"name": "epic-simulator"},
                            "logRecords": self._buffer,
                        }
                    ],
                }
            ]
        }

    def close(self):
        """Flush remaining buffer."""
        self.flush()
