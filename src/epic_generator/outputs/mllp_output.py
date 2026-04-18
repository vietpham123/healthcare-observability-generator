import socket
import logging

logger = logging.getLogger(__name__)

# MLLP framing characters
VT = b"\x0b"   # Vertical Tab — start of message
FS = b"\x1c"   # File Separator — end of data
CR = b"\x0d"   # Carriage Return — end of message


class MLLPOutput:
    """Send HL7v2 messages via Minimal Lower Layer Protocol (MLLP)."""

    def __init__(self, host, port=2575, timeout=10):
        """
        Args:
            host: MLLP receiver hostname or IP.
            port: MLLP port (default 2575).
            timeout: Socket timeout in seconds.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket = None
        self._connect()

    def _connect(self):
        """Establish TCP connection to the MLLP receiver."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.timeout)
        self._socket.connect((self.host, self.port))

    def write(self, hl7_message):
        """Send an HL7v2 message wrapped in MLLP envelope.

        MLLP framing: VT + message + FS + CR

        Args:
            hl7_message: str, the HL7v2 message content.
        """
        envelope = VT + hl7_message.encode("utf-8") + FS + CR

        try:
            self._socket.sendall(envelope)
            # Wait for ACK (optional — some receivers don't send ACK)
            try:
                ack = self._socket.recv(4096)
                if ack and b"MSA" in ack:
                    # Parse ACK status — AA = accepted, AE = error, AR = rejected
                    ack_str = ack.decode("utf-8", errors="replace")
                    if "AE" in ack_str or "AR" in ack_str:
                        logger.warning("MLLP NACK received: %s", ack_str[:200])
            except socket.timeout:
                pass  # No ACK expected or timeout — continue
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            logger.warning("MLLP connection lost, reconnecting: %s", e)
            self._reconnect()
            try:
                self._socket.sendall(envelope)
            except OSError:
                logger.error("Failed to send MLLP message after reconnect")

    def _reconnect(self):
        """Close and re-establish the connection."""
        self.close()
        try:
            self._connect()
        except OSError as e:
            logger.error("Failed to reconnect to MLLP receiver: %s", e)

    def close(self):
        """Close the MLLP socket."""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
