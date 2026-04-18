"""NetFlow/IPFIX binary exporter — sends real NetFlow v5/v9 packets via UDP.

Produces binary flow records decodable by standard collectors
(nfcapd, ntopng, Dynatrace, SiLK, etc.).
Covers FR-501, FR-502, FR-503, FR-505.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time

from netloggen.core.models import FlowRecord, LogEvent, MetricEvent, TrapEvent
from netloggen.outputs.base import BaseOutput

logger = logging.getLogger(__name__)

# NetFlow v5 header: version(2) + count(2) + sysUptime(4) + unix_secs(4) +
#                    unix_nsecs(4) + flow_sequence(4) + engine_type(1) + engine_id(1) + sampling(2)
_NFv5_HEADER_FMT = "!HHIIIIBBH"
_NFv5_HEADER_SIZE = struct.calcsize(_NFv5_HEADER_FMT)

# NetFlow v5 record: 48 bytes each
_NFv5_RECORD_FMT = "!IIIHHIIIIHHBBBBHHBBH"
_NFv5_RECORD_SIZE = struct.calcsize(_NFv5_RECORD_FMT)

# Protocol numbers
_PROTO_MAP = {"tcp": 6, "udp": 17, "icmp": 1, "gre": 47, "esp": 50}

# NetFlow v9 constants
_NFv9_TEMPLATE_FLOWSET_ID = 0
_NFv9_DATA_FLOWSET_BASE_ID = 256

# IPFIX constants
_IPFIX_VERSION = 10
_IPFIX_TEMPLATE_SET_ID = 2


class NetFlowOutput(BaseOutput):
    """Export binary NetFlow v5/v9 or IPFIX packets via UDP."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 2055,
        version: int = 5,
    ):
        self.host = host
        self.port = port
        self.version = version
        self._sock: socket.socket | None = None
        self._seq = 0
        self._template_id = _NFv9_DATA_FLOWSET_BASE_ID
        self._boot_time = time.time()
        self._template_sent = False
        self._stats = {"sent": 0, "failed": 0, "packets": 0}

    async def connect(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)
        self._boot_time = time.time()
        logger.info(f"NetFlow v{self.version} output ready → {self.host}:{self.port}")

    async def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None
        logger.info(f"NetFlow output stats: {self._stats}")

    async def send_logs(self, events: list[LogEvent]) -> int:
        return 0

    async def send_metrics(self, metrics: list[MetricEvent]) -> int:
        return 0

    async def send_traps(self, traps: list[TrapEvent]) -> int:
        return 0

    async def send_flows(self, flows: list[FlowRecord]) -> int:
        if not self._sock or not flows:
            return 0

        sent = 0
        # Split into batches of 30 records per packet (UDP size limit)
        batch_size = 30
        for i in range(0, len(flows), batch_size):
            batch = flows[i: i + batch_size]
            try:
                if self.version == 5:
                    packet = self._encode_v5(batch)
                elif self.version == 9:
                    packet = self._encode_v9(batch)
                elif self.version == 10:
                    packet = self._encode_ipfix(batch)
                else:
                    packet = self._encode_v5(batch)

                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, self._sock.sendto, packet, (self.host, self.port)
                )
                sent += len(batch)
                self._stats["sent"] += len(batch)
                self._stats["packets"] += 1
            except Exception as e:
                logger.warning(f"NetFlow send failed: {e}")
                self._stats["failed"] += len(batch)

        return sent

    # --- NetFlow v5 encoding ---

    def _encode_v5(self, flows: list[FlowRecord]) -> bytes:
        now = time.time()
        uptime_ms = int((now - self._boot_time) * 1000) & 0xFFFFFFFF
        unix_secs = int(now)
        unix_nsecs = int((now - unix_secs) * 1e9)

        header = struct.pack(
            _NFv5_HEADER_FMT,
            5,               # version
            len(flows),      # count
            uptime_ms,       # sysUptime
            unix_secs,       # unix_secs
            unix_nsecs,      # unix_nsecs
            self._seq,       # flow_sequence
            1,               # engine_type
            0,               # engine_id
            0,               # sampling_interval
        )
        self._seq += len(flows)

        records = b""
        for f in flows:
            proto = _PROTO_MAP.get(f.protocol.lower(), 6)
            src_ip = _ip_to_int(f.src_ip)
            dst_ip = _ip_to_int(f.dst_ip)
            # Input/output interface indices (use hash of name)
            in_if = abs(hash(f.input_interface)) % 65535 if f.input_interface else 0
            out_if = abs(hash(f.output_interface)) % 65535 if f.output_interface else 0
            first = uptime_ms - 60000  # flow started ~60s ago
            last = uptime_ms

            records += struct.pack(
                _NFv5_RECORD_FMT,
                src_ip,          # srcaddr
                dst_ip,          # dstaddr
                0,               # nexthop
                in_if,           # input
                out_if,          # output
                f.packets_total, # dPkts
                f.bytes_total,   # dOctets
                first,           # first
                last,            # last
                f.src_port,      # srcport
                f.dst_port,      # dstport
                0,               # pad1
                f.tcp_flags,     # tcp_flags
                proto,           # prot
                0,               # tos
                f.src_as,        # src_as
                f.dst_as,        # dst_as
                0,               # src_mask
                0,               # dst_mask
                0,               # pad2
            )

        return header + records

    # --- NetFlow v9 encoding ---

    def _encode_v9(self, flows: list[FlowRecord]) -> bytes:
        now = time.time()
        uptime_ms = int((now - self._boot_time) * 1000) & 0xFFFFFFFF
        unix_secs = int(now)
        self._seq += 1

        flowsets = b""

        # Send template every packet (simple approach)
        template = self._build_v9_template()
        flowsets += template

        # Data flowset
        data = self._build_v9_data(flows, uptime_ms)
        flowsets += data

        # v9 header: version(2) + count(2) + sysUptime(4) + unix_secs(4) + seq(4) + source_id(4)
        count = 2  # template flowset + data flowset
        header = struct.pack("!HHIIII", 9, count, uptime_ms, unix_secs, self._seq, 1)

        return header + flowsets

    def _build_v9_template(self) -> bytes:
        # Field definitions: (type, length)
        fields = [
            (8, 4),    # IPV4_SRC_ADDR
            (12, 4),   # IPV4_DST_ADDR
            (7, 2),    # L4_SRC_PORT
            (11, 2),   # L4_DST_PORT
            (4, 1),    # PROTOCOL
            (1, 4),    # IN_BYTES
            (2, 4),    # IN_PKTS
            (6, 1),    # TCP_FLAGS
            (10, 2),   # INPUT_SNMP
            (14, 2),   # OUTPUT_SNMP
            (16, 4),   # SRC_AS
            (17, 4),   # DST_AS
        ]

        template_body = struct.pack("!HH", self._template_id, len(fields))
        for ftype, flen in fields:
            template_body += struct.pack("!HH", ftype, flen)

        # Template flowset: flowset_id=0, length includes header
        total_len = 4 + len(template_body)  # 4 bytes for flowset header
        # Pad to 4-byte boundary
        pad = (4 - total_len % 4) % 4
        total_len += pad

        flowset = struct.pack("!HH", _NFv9_TEMPLATE_FLOWSET_ID, total_len)
        flowset += template_body
        flowset += b"\x00" * pad
        return flowset

    def _build_v9_data(self, flows: list[FlowRecord], uptime_ms: int) -> bytes:
        records = b""
        for f in flows:
            proto = _PROTO_MAP.get(f.protocol.lower(), 6)
            in_if = abs(hash(f.input_interface)) % 65535 if f.input_interface else 0
            out_if = abs(hash(f.output_interface)) % 65535 if f.output_interface else 0

            records += struct.pack("!I", _ip_to_int(f.src_ip))
            records += struct.pack("!I", _ip_to_int(f.dst_ip))
            records += struct.pack("!H", f.src_port)
            records += struct.pack("!H", f.dst_port)
            records += struct.pack("!B", proto)
            records += struct.pack("!I", f.bytes_total)
            records += struct.pack("!I", f.packets_total)
            records += struct.pack("!B", f.tcp_flags)
            records += struct.pack("!H", in_if)
            records += struct.pack("!H", out_if)
            records += struct.pack("!I", f.src_as)
            records += struct.pack("!I", f.dst_as)

        total_len = 4 + len(records)
        pad = (4 - total_len % 4) % 4
        total_len += pad

        flowset = struct.pack("!HH", self._template_id, total_len)
        flowset += records
        flowset += b"\x00" * pad
        return flowset

    # --- IPFIX (NetFlow v10) encoding ---

    def _encode_ipfix(self, flows: list[FlowRecord]) -> bytes:
        now = time.time()
        unix_secs = int(now)
        self._seq += 1

        flowsets = self._build_v9_template()  # IPFIX uses same template concept
        # Adjust template flowset ID
        flowsets = struct.pack("!HH", _IPFIX_TEMPLATE_SET_ID,
                               len(flowsets)) + flowsets[4:]

        data = self._build_v9_data(flows, 0)
        flowsets += data

        # IPFIX header: version(2) + length(2) + export_time(4) + seq(4) + domain_id(4)
        total_len = 16 + len(flowsets)
        header = struct.pack("!HHIII", _IPFIX_VERSION, total_len, unix_secs, self._seq, 1)

        return header + flowsets

    @property
    def stats(self) -> dict:
        return dict(self._stats)


def _ip_to_int(ip: str) -> int:
    """Convert dotted-quad IPv4 to 32-bit integer."""
    parts = ip.split(".")
    if len(parts) != 4:
        return 0
    try:
        return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])
    except (ValueError, IndexError):
        return 0
