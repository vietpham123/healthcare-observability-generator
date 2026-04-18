"""Lightweight SNMP agent — responds to SNMPv2c GET / GETNEXT / GETBULK
by reading device state from the shared JSON file.

Uses raw BER encoding/decoding (no pysnmp dependency). Multiplexes
all devices behind a single UDP port, routing by community string
(community = device hostname).

Usage:
    netloggen snmp-agent --topology config/default-topology.yaml
    snmpwalk -v2c -c core-rtr-01 localhost:1161 1.3.6.1.2.1.1
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from typing import Any

from netloggen.snmpagent.mib_profiles import build_device_oid_tree
from netloggen.snmpagent.state import DEFAULT_STATE_PATH, load_device_state

logger = logging.getLogger(__name__)

# ASN.1 / BER constants
_INTEGER = 0x02
_OCTET_STRING = 0x04
_NULL = 0x05
_OID = 0x06
_SEQUENCE = 0x30
_IP_ADDRESS = 0x40
_COUNTER32 = 0x41
_GAUGE32 = 0x42
_TIMETICKS = 0x43
_COUNTER64 = 0x46
_NO_SUCH_OBJECT = 0x80
_NO_SUCH_INSTANCE = 0x81
_END_OF_MIB_VIEW = 0x82

# PDU types
_GET_REQUEST = 0xA0
_GET_NEXT_REQUEST = 0xA1
_GET_RESPONSE = 0xA2
_GET_BULK_REQUEST = 0xA5

# Error status codes
_NO_ERROR = 0
_TOO_BIG = 1
_NO_SUCH_NAME = 2
_GEN_ERR = 5


class SNMPAgentProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for SNMP agent."""

    def __init__(self, state_path: str, cache_ttl: float = 5.0):
        self.state_path = state_path
        self.cache_ttl = cache_ttl
        self._transport: asyncio.DatagramTransport | None = None
        self._state_cache: dict[str, Any] | None = None
        self._cache_time: float = 0
        self._oid_trees: dict[str, list[tuple[tuple[int, ...], str, Any]]] = {}
        self._stats = {"requests": 0, "responses": 0, "errors": 0}

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self._transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            response = self._handle_request(data)
            if response:
                self._transport.sendto(response, addr)
                self._stats["responses"] += 1
        except Exception as e:
            logger.debug(f"Error handling SNMP request from {addr}: {e}")
            self._stats["errors"] += 1

    def _handle_request(self, data: bytes) -> bytes | None:
        """Parse incoming SNMP request and build response."""
        self._stats["requests"] += 1

        try:
            offset = 0
            # SNMP message wrapper (SEQUENCE)
            tag, length, offset = _read_tlv_header(data, offset)
            if tag != _SEQUENCE:
                return None

            # version (INTEGER)
            version, offset = _read_integer(data, offset)
            if version != 1:  # SNMPv2c only
                logger.debug(f"Unsupported SNMP version: {version}")
                return None

            # community (OCTET STRING)
            community, offset = _read_octet_string(data, offset)

            # PDU
            pdu_tag, pdu_len, pdu_start = _read_tlv_header(data, offset)
            offset = pdu_start

            # request-id, error-status, error-index (or non-repeaters, max-reps for GETBULK)
            request_id, offset = _read_integer(data, offset)
            param1, offset = _read_integer(data, offset)  # error-status or non-repeaters
            param2, offset = _read_integer(data, offset)  # error-index or max-repetitions

            # varbind list
            varbind_tag, varbind_len, offset = _read_tlv_header(data, offset)
            requested_oids: list[str] = []
            vb_end = offset + varbind_len
            while offset < vb_end:
                # Each varbind is a SEQUENCE of (OID, value)
                _, vb_item_len, offset = _read_tlv_header(data, offset)
                oid_str, offset = _read_oid(data, offset)
                # Skip the value (we only need the OID for GET/GETNEXT)
                _, val_len, offset = _read_tlv_header(data, offset)
                offset += val_len
                requested_oids.append(oid_str)

        except (IndexError, struct.error, ValueError) as e:
            logger.debug(f"Failed to parse SNMP request: {e}")
            return None

        # Look up device by community string
        oid_tree = self._get_oid_tree(community)
        if oid_tree is None:
            logger.debug(f"Unknown community/device: {community!r}")
            return None

        # Process based on PDU type
        if pdu_tag == _GET_REQUEST:
            response_varbinds = self._handle_get(requested_oids, oid_tree)
        elif pdu_tag == _GET_NEXT_REQUEST:
            response_varbinds = self._handle_get_next(requested_oids, oid_tree)
        elif pdu_tag == _GET_BULK_REQUEST:
            non_repeaters = param1
            max_reps = min(param2, 50)  # cap to prevent DoS
            response_varbinds = self._handle_get_bulk(
                requested_oids, oid_tree, non_repeaters, max_reps
            )
        else:
            return None

        return self._build_response(version, community, request_id, response_varbinds)

    def _get_oid_tree(self, community: str) -> list[tuple[tuple[int, ...], str, Any]] | None:
        """Get sorted OID tree for a device, with caching."""
        now = time.monotonic()
        if self._state_cache is None or (now - self._cache_time) > self.cache_ttl:
            self._state_cache = load_device_state(self.state_path)
            self._cache_time = now
            self._oid_trees.clear()

        if community in self._oid_trees:
            return self._oid_trees[community]

        devices = self._state_cache.get("devices", {})
        if community not in devices:
            return None

        # Build and sort OID tree
        raw_tree = build_device_oid_tree(devices[community])
        sorted_tree = []
        for oid_str, (type_str, value) in raw_tree.items():
            oid_tuple = _oid_str_to_tuple(oid_str)
            sorted_tree.append((oid_tuple, type_str, value))
        sorted_tree.sort(key=lambda x: x[0])

        self._oid_trees[community] = sorted_tree
        return sorted_tree

    def _handle_get(
        self,
        oids: list[str],
        tree: list[tuple[tuple[int, ...], str, Any]],
    ) -> list[tuple[str, bytes]]:
        """Handle GET request — exact OID match."""
        result = []
        tree_dict = {_oid_tuple_to_str(t[0]): (t[1], t[2]) for t in tree}

        for oid_str in oids:
            if oid_str in tree_dict:
                type_str, value = tree_dict[oid_str]
                result.append((oid_str, _encode_value(type_str, value)))
            else:
                result.append((oid_str, bytes([_NO_SUCH_INSTANCE, 0])))

        return result

    def _handle_get_next(
        self,
        oids: list[str],
        tree: list[tuple[tuple[int, ...], str, Any]],
    ) -> list[tuple[str, bytes]]:
        """Handle GETNEXT request — lexicographic next OID."""
        result = []
        for oid_str in oids:
            oid_tuple = _oid_str_to_tuple(oid_str)
            next_entry = self._find_next(oid_tuple, tree)
            if next_entry:
                next_oid, type_str, value = next_entry
                result.append((_oid_tuple_to_str(next_oid), _encode_value(type_str, value)))
            else:
                result.append((oid_str, bytes([_END_OF_MIB_VIEW, 0])))
        return result

    def _handle_get_bulk(
        self,
        oids: list[str],
        tree: list[tuple[tuple[int, ...], str, Any]],
        non_repeaters: int,
        max_reps: int,
    ) -> list[tuple[str, bytes]]:
        """Handle GETBULK request."""
        result = []

        # Non-repeater variables (like GETNEXT)
        for i in range(min(non_repeaters, len(oids))):
            oid_tuple = _oid_str_to_tuple(oids[i])
            next_entry = self._find_next(oid_tuple, tree)
            if next_entry:
                next_oid, type_str, value = next_entry
                result.append((_oid_tuple_to_str(next_oid), _encode_value(type_str, value)))
            else:
                result.append((oids[i], bytes([_END_OF_MIB_VIEW, 0])))

        # Repeater variables
        for i in range(non_repeaters, len(oids)):
            current = _oid_str_to_tuple(oids[i])
            for _ in range(max_reps):
                next_entry = self._find_next(current, tree)
                if next_entry:
                    next_oid, type_str, value = next_entry
                    result.append((_oid_tuple_to_str(next_oid), _encode_value(type_str, value)))
                    current = next_oid
                else:
                    result.append((_oid_tuple_to_str(current), bytes([_END_OF_MIB_VIEW, 0])))
                    break

        return result

    def _find_next(
        self,
        oid: tuple[int, ...],
        tree: list[tuple[tuple[int, ...], str, Any]],
    ) -> tuple[tuple[int, ...], str, Any] | None:
        """Find the lexicographically next OID after the given one."""
        for entry_oid, type_str, value in tree:
            if entry_oid > oid:
                return (entry_oid, type_str, value)
        return None

    def _build_response(
        self,
        version: int,
        community: str,
        request_id: int,
        varbinds: list[tuple[str, bytes]],
    ) -> bytes:
        """Encode SNMP GET-RESPONSE PDU."""
        # Encode varbinds
        encoded_varbinds = b""
        for oid_str, value_bytes in varbinds:
            oid_encoded = _encode_oid(oid_str)
            varbind = _encode_sequence(oid_encoded + value_bytes)
            encoded_varbinds += varbind

        varbind_seq = _encode_sequence(encoded_varbinds)

        # PDU: request-id, error-status(0), error-index(0), varbinds
        pdu_body = (
            _encode_integer(request_id)
            + _encode_integer(_NO_ERROR)
            + _encode_integer(0)
            + varbind_seq
        )
        pdu = bytes([_GET_RESPONSE]) + _encode_length(len(pdu_body)) + pdu_body

        # Message wrapper
        message_body = _encode_integer(version) + _encode_octet_string(community) + pdu
        return _encode_sequence(message_body)

    @property
    def stats(self) -> dict:
        return dict(self._stats)


# ─── BER Encoding Helpers ─────────────────────────────────────────

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
    elif value > 0:
        payload = value.to_bytes((value.bit_length() + 8) // 8, byteorder="big", signed=False)
        if payload[0] & 0x80:
            payload = b"\x00" + payload
    else:
        payload = value.to_bytes((value.bit_length() + 9) // 8, byteorder="big", signed=True)
    return bytes([_INTEGER]) + _encode_length(len(payload)) + payload


def _encode_octet_string(value: str) -> bytes:
    data = value.encode("utf-8")
    return bytes([_OCTET_STRING]) + _encode_length(len(data)) + data


def _encode_sequence(data: bytes) -> bytes:
    return bytes([_SEQUENCE]) + _encode_length(len(data)) + data


def _encode_oid(oid_str: str) -> bytes:
    parts = [int(p) for p in oid_str.split(".") if p]
    if len(parts) < 2:
        parts = parts + [0] * (2 - len(parts))
    encoded = [40 * parts[0] + parts[1]]
    for p in parts[2:]:
        if p < 128:
            encoded.append(p)
        else:
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


def _encode_counter32(value: int) -> bytes:
    value = value & 0xFFFFFFFF
    if value == 0:
        payload = b"\x00"
    else:
        payload = value.to_bytes((value.bit_length() + 8) // 8, byteorder="big", signed=False)
        if payload[0] & 0x80:
            payload = b"\x00" + payload
    return bytes([_COUNTER32]) + _encode_length(len(payload)) + payload


def _encode_counter64(value: int) -> bytes:
    value = value & 0xFFFFFFFFFFFFFFFF
    if value == 0:
        payload = b"\x00"
    else:
        payload = value.to_bytes((value.bit_length() + 8) // 8, byteorder="big", signed=False)
        if payload[0] & 0x80:
            payload = b"\x00" + payload
    return bytes([_COUNTER64]) + _encode_length(len(payload)) + payload


def _encode_gauge32(value: int) -> bytes:
    value = min(value, 0xFFFFFFFF) & 0xFFFFFFFF
    if value == 0:
        payload = b"\x00"
    else:
        payload = value.to_bytes((value.bit_length() + 8) // 8, byteorder="big", signed=False)
        if payload[0] & 0x80:
            payload = b"\x00" + payload
    return bytes([_GAUGE32]) + _encode_length(len(payload)) + payload


def _encode_timeticks(value: int) -> bytes:
    value = value & 0xFFFFFFFF
    payload = struct.pack("!I", value)
    # Strip leading zeros but keep at least one byte
    while len(payload) > 1 and payload[0:1] == b"\x00":
        payload = payload[1:]
    if payload[0] & 0x80:
        payload = b"\x00" + payload
    return bytes([_TIMETICKS]) + _encode_length(len(payload)) + payload


def _encode_ip_address(ip_str: str) -> bytes:
    parts = [int(p) for p in ip_str.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return bytes([_IP_ADDRESS, 4]) + bytes(parts[:4])


def _encode_value(type_str: str, value: Any) -> bytes:
    """Encode a value based on its ASN.1 type string."""
    if type_str == "str":
        return _encode_octet_string(str(value))
    elif type_str == "int":
        return _encode_integer(int(value))
    elif type_str == "gauge":
        return _encode_gauge32(int(value))
    elif type_str == "counter":
        return _encode_counter32(int(value))
    elif type_str == "counter64":
        return _encode_counter64(int(value))
    elif type_str == "timeticks":
        return _encode_timeticks(int(value))
    elif type_str == "oid":
        return _encode_oid(str(value))
    elif type_str == "ipaddr":
        return _encode_ip_address(str(value))
    else:
        return _encode_octet_string(str(value))


# ─── BER Decoding Helpers ─────────────────────────────────────────

def _read_tlv_header(data: bytes, offset: int) -> tuple[int, int, int]:
    """Read BER tag + length, return (tag, length, new_offset)."""
    tag = data[offset]
    offset += 1
    if data[offset] < 0x80:
        length = data[offset]
        offset += 1
    elif data[offset] == 0x81:
        length = data[offset + 1]
        offset += 2
    elif data[offset] == 0x82:
        length = (data[offset + 1] << 8) | data[offset + 2]
        offset += 3
    elif data[offset] == 0x83:
        length = (data[offset + 1] << 16) | (data[offset + 2] << 8) | data[offset + 3]
        offset += 4
    else:
        raise ValueError(f"Unsupported BER length encoding: 0x{data[offset]:02x}")
    return tag, length, offset


def _read_integer(data: bytes, offset: int) -> tuple[int, int]:
    """Read a BER INTEGER."""
    tag, length, offset = _read_tlv_header(data, offset)
    if tag != _INTEGER:
        raise ValueError(f"Expected INTEGER (0x02), got 0x{tag:02x}")
    value = int.from_bytes(data[offset:offset + length], byteorder="big", signed=True)
    return value, offset + length


def _read_octet_string(data: bytes, offset: int) -> tuple[str, int]:
    """Read a BER OCTET STRING."""
    tag, length, offset = _read_tlv_header(data, offset)
    if tag != _OCTET_STRING:
        raise ValueError(f"Expected OCTET STRING (0x04), got 0x{tag:02x}")
    value = data[offset:offset + length].decode("utf-8", errors="replace")
    return value, offset + length


def _read_oid(data: bytes, offset: int) -> tuple[str, int]:
    """Read a BER OBJECT IDENTIFIER."""
    tag, length, offset = _read_tlv_header(data, offset)
    if tag != _OID:
        raise ValueError(f"Expected OID (0x06), got 0x{tag:02x}")
    oid_bytes = data[offset:offset + length]
    offset += length

    if not oid_bytes:
        return "0.0", offset

    parts = [oid_bytes[0] // 40, oid_bytes[0] % 40]
    i = 1
    while i < len(oid_bytes):
        if oid_bytes[i] < 128:
            parts.append(oid_bytes[i])
            i += 1
        else:
            value = 0
            while i < len(oid_bytes) and oid_bytes[i] & 0x80:
                value = (value << 7) | (oid_bytes[i] & 0x7F)
                i += 1
            if i < len(oid_bytes):
                value = (value << 7) | oid_bytes[i]
                i += 1
            parts.append(value)

    return ".".join(str(p) for p in parts), offset


# ─── OID Utility ──────────────────────────────────────────────────

def _oid_str_to_tuple(oid_str: str) -> tuple[int, ...]:
    return tuple(int(p) for p in oid_str.split(".") if p)


def _oid_tuple_to_str(oid_tuple: tuple[int, ...]) -> str:
    return ".".join(str(p) for p in oid_tuple)


# ─── Agent Runner ─────────────────────────────────────────────────

async def run_agent(
    host: str = "0.0.0.0",
    port: int = 1161,
    state_path: str = DEFAULT_STATE_PATH,
    cache_ttl: float = 5.0,
) -> None:
    """Start the SNMP agent and run forever."""
    loop = asyncio.get_running_loop()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: SNMPAgentProtocol(state_path=state_path, cache_ttl=cache_ttl),
        local_addr=(host, port),
    )

    logger.info(f"SNMP agent listening on {host}:{port} (UDP)")
    logger.info(f"Reading state from: {state_path}")
    logger.info("Use community string = device hostname (e.g., 'core-rtr-01')")

    try:
        # Run until cancelled
        while True:
            await asyncio.sleep(60)
            state = load_device_state(state_path)
            device_count = len(state.get("devices", {}))
            ts = state.get("timestamp", "never")
            logger.info(
                f"Agent stats: {protocol.stats} | "
                f"Devices: {device_count} | Last state update: {ts}"
            )
    except asyncio.CancelledError:
        pass
    finally:
        transport.close()
        logger.info("SNMP agent stopped")
