"""SNMP trap sender — sends BER-encoded SNMPv2c trap PDUs via UDP.

Produces real SNMP trap packets decodable by any standard trap receiver
(e.g., snmptrapd, Dynatrace SNMP extension, SolarWinds, etc.).
Covers FR-401, FR-403, FR-404.

Note: SNMPv3 USM support (FR-402) requires pysnmp optional dependency.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from datetime import timezone

from netloggen.core.models import FlowRecord, LogEvent, MetricEvent, TrapEvent
from netloggen.outputs.base import BaseOutput

logger = logging.getLogger(__name__)

# ASN.1 / BER tag constants
_INTEGER = 0x02
_OCTET_STRING = 0x04
_NULL = 0x05
_OID = 0x06
_SEQUENCE = 0x30
_IP_ADDRESS = 0x40
_COUNTER32 = 0x41
_GAUGE32 = 0x42
_TIMETICKS = 0x43
_SNMPv2_TRAP = 0xA7  # SNMPv2-Trap-PDU

# Well-known OIDs
_OID_SNMP_TRAP_OID = "1.3.6.1.6.3.1.1.4.1.0"
_OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"


class SNMPTrapOutput(BaseOutput):
    """Send BER-encoded SNMPv2c traps via UDP."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 162,
        community: str = "public",
    ):
        self.host = host
        self.port = port
        self.community = community
        self._sock: socket.socket | None = None
        self._request_id = 1
        self._stats = {"sent": 0, "failed": 0}

    async def connect(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)
        logger.info(f"SNMP trap output ready → {self.host}:{self.port}")

    async def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None
        logger.info(f"SNMP trap output stats: {self._stats}")

    async def send_logs(self, events: list[LogEvent]) -> int:
        return 0

    async def send_metrics(self, metrics: list[MetricEvent]) -> int:
        return 0

    async def send_traps(self, traps: list[TrapEvent]) -> int:
        sent = 0
        for trap in traps:
            try:
                pdu = self._encode_trap(trap)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, self._sock.sendto, pdu, (self.host, self.port)
                )
                sent += 1
                self._stats["sent"] += 1
            except Exception as e:
                logger.warning(f"SNMP trap send failed: {e}")
                self._stats["failed"] += 1
        return sent

    async def send_flows(self, flows: list[FlowRecord]) -> int:
        return 0

    def _encode_trap(self, trap: TrapEvent) -> bytes:
        """Build a complete SNMPv2c Trap PDU packet."""
        # Varbinds list
        uptime_ticks = int(time.time() * 100) & 0xFFFFFFFF
        varbinds = []

        # sysUpTime.0
        varbinds.append(self._encode_varbind(
            _OID_SYS_UPTIME, _encode_timeticks(uptime_ticks)
        ))
        # snmpTrapOID.0
        varbinds.append(self._encode_varbind(
            _OID_SNMP_TRAP_OID, _encode_oid(trap.trap_oid)
        ))

        # Additional varbinds from trap data
        for key, value in trap.varbinds.items():
            # Use a synthetic OID based on key hash for non-standard varbinds
            oid = trap.attributes.get(f"{key}_oid", f"1.3.6.1.4.1.99999.1.{abs(hash(key)) % 1000}")
            if isinstance(value, int):
                varbinds.append(self._encode_varbind(oid, _encode_integer(value)))
            else:
                varbinds.append(self._encode_varbind(oid, _encode_octet_string(str(value))))

        varbind_seq = _encode_sequence(b"".join(varbinds))

        # Trap PDU
        request_id = _encode_integer(self._request_id)
        self._request_id += 1
        error_status = _encode_integer(0)
        error_index = _encode_integer(0)

        trap_pdu_body = request_id + error_status + error_index + varbind_seq
        trap_pdu = bytes([_SNMPv2_TRAP]) + _encode_length(len(trap_pdu_body)) + trap_pdu_body

        # SNMP message wrapper
        version = _encode_integer(1)  # SNMPv2c
        community = _encode_octet_string(self.community)

        message_body = version + community + trap_pdu
        message = _encode_sequence(message_body)
        return message

    def _encode_varbind(self, oid_str: str, value_bytes: bytes) -> bytes:
        oid_encoded = _encode_oid(oid_str)
        return _encode_sequence(oid_encoded + value_bytes)

    @property
    def stats(self) -> dict:
        return dict(self._stats)


# --- BER encoding helpers ---

def _encode_length(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])
    elif length < 0x100:
        return bytes([0x81, length])
    elif length < 0x10000:
        return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
    else:
        return bytes([0x83, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF])


def _encode_integer(value: int) -> bytes:
    if value == 0:
        payload = b"\x00"
    else:
        payload = value.to_bytes((value.bit_length() + 8) // 8, byteorder="big", signed=True)
    return bytes([_INTEGER]) + _encode_length(len(payload)) + payload


def _encode_octet_string(value: str) -> bytes:
    data = value.encode("utf-8")
    return bytes([_OCTET_STRING]) + _encode_length(len(data)) + data


def _encode_oid(oid_str: str) -> bytes:
    parts = [int(p) for p in oid_str.split(".")]
    if len(parts) < 2:
        parts = parts + [0] * (2 - len(parts))

    # First two components encoded as 40*X + Y
    encoded = [40 * parts[0] + parts[1]]

    for p in parts[2:]:
        if p < 128:
            encoded.append(p)
        else:
            # Multi-byte encoding
            sub = []
            while p > 0:
                sub.append(p & 0x7F)
                p >>= 7
            sub.reverse()
            for i in range(len(sub) - 1):
                sub[i] |= 0x80
            encoded.extend(sub)

    payload = bytes(encoded)
    return bytes([_OID]) + _encode_length(len(payload)) + payload


def _encode_timeticks(value: int) -> bytes:
    payload = struct.pack("!I", value & 0xFFFFFFFF)
    # strip leading zeros but keep at least one byte
    while len(payload) > 1 and payload[0:1] == b"\x00":
        payload = payload[1:]
    return bytes([_TIMETICKS]) + _encode_length(len(payload)) + payload


def _encode_sequence(data: bytes) -> bytes:
    return bytes([_SEQUENCE]) + _encode_length(len(data)) + data
