import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class APIOutput:
    """Push log events via REST API with batching and retry support.

    Designed primarily for Dynatrace Log Ingest v2 API but works with any
    REST endpoint that accepts JSON payloads.
    """

    def __init__(self, endpoint, api_token=None, batch_size=50,
                 headers=None, max_retries=3, auth_header="Authorization"):
        """
        Args:
            endpoint: Full URL of the log ingest API.
            api_token: Bearer token or API token for authentication.
            batch_size: Number of events to buffer before flushing.
            headers: Additional HTTP headers as a dict.
            max_retries: Number of retry attempts on failure.
            auth_header: Header name for the API token (default: Authorization).
        """
        self.endpoint = endpoint
        self.api_token = api_token
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.auth_header = auth_header

        self._headers = {
            "Content-Type": "application/json; charset=utf-8",
        }
        if api_token:
            self._headers[auth_header] = f"Api-Token {api_token}"
        if headers:
            self._headers.update(headers)

        self._buffer = []

    def write(self, formatted_event):
        """Buffer a log event and flush when batch is full.

        Args:
            formatted_event: str, the log event content.
        """
        self._buffer.append(formatted_event)

        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        """POST buffered events to the API endpoint."""
        if not self._buffer:
            return

        # Build payload — Dynatrace Log Ingest expects array of log entries
        payload = []
        for event in self._buffer:
            # Try to parse as JSON first (for structured logs)
            try:
                parsed = json.loads(event)
                payload.append(parsed)
            except (json.JSONDecodeError, TypeError):
                # Plain text — wrap in content field
                payload.append({"content": event})

        body = json.dumps(payload).encode("utf-8")

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    self.endpoint,
                    data=body,
                    headers=self._headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    status = resp.getcode()
                    if status < 300:
                        logger.debug("API flush: sent %d events (HTTP %d)",
                                     len(self._buffer), status)
                        self._buffer.clear()
                        return
                    else:
                        logger.warning("API flush: unexpected HTTP %d", status)
            except urllib.error.HTTPError as e:
                logger.warning("API flush attempt %d/%d failed: HTTP %d %s",
                               attempt, self.max_retries, e.code, e.reason)
            except (urllib.error.URLError, OSError) as e:
                logger.warning("API flush attempt %d/%d failed: %s",
                               attempt, self.max_retries, e)

        logger.error("API flush failed after %d attempts, dropping %d events",
                     self.max_retries, len(self._buffer))
        self._buffer.clear()

    def close(self):
        """Flush any remaining buffered events."""
        self.flush()
