import socket
import ssl
import logging

logger = logging.getLogger(__name__)


class SyslogOutput:
    """Send RFC 5424 syslog messages over TCP or UDP, with optional TLS."""

    def __init__(self, host, port=514, protocol="tcp", use_tls=False,
                 ca_cert=None, client_cert=None, client_key=None):
        """
        Args:
            host: Syslog server hostname or IP.
            port: Syslog server port (default 514, or 6514 for TLS).
            protocol: "tcp" or "udp".
            use_tls: Enable TLS for TCP connections.
            ca_cert: Path to CA certificate file for TLS.
            client_cert: Path to client certificate for mutual TLS.
            client_key: Path to client private key for mutual TLS.
        """
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.use_tls = use_tls
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key
        self._socket = None
        self._connect()

    def _connect(self):
        """Establish connection to syslog server."""
        if self.protocol == "udp":
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_sock.settimeout(10)

            if self.use_tls:
                context = ssl.create_default_context(
                    purpose=ssl.Purpose.SERVER_AUTH,
                    cafile=self.ca_cert,
                )
                if self.client_cert and self.client_key:
                    context.load_cert_chain(self.client_cert, self.client_key)
                self._socket = context.wrap_socket(raw_sock, server_hostname=self.host)
            else:
                self._socket = raw_sock

            self._socket.connect((self.host, self.port))

    def write(self, formatted_event):
        """Send a formatted log event as a syslog message.

        For TCP, appends a newline as message delimiter (octet-counting is
        also common but newline framing is more widely supported).
        """
        message = formatted_event.encode("utf-8")

        try:
            if self.protocol == "udp":
                # UDP has a practical limit of ~65507 bytes; truncate if needed
                if len(message) > 65000:
                    message = message[:65000]
                self._socket.sendto(message, (self.host, self.port))
            else:
                # TCP: newline-delimited framing
                self._socket.sendall(message + b"\n")
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            logger.warning("Syslog connection lost, reconnecting: %s", e)
            self._reconnect()
            # Retry once
            try:
                if self.protocol == "udp":
                    self._socket.sendto(message, (self.host, self.port))
                else:
                    self._socket.sendall(message + b"\n")
            except OSError:
                logger.error("Failed to send syslog message after reconnect")

    def _reconnect(self):
        """Close and re-establish the connection."""
        self.close()
        try:
            self._connect()
        except OSError as e:
            logger.error("Failed to reconnect to syslog server: %s", e)

    def close(self):
        """Close the socket connection."""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
