"""NetFlow/IPFIX flow record generator.

Generates flow records as structured FlowRecord objects ready for
Dynatrace ingestion as metrics or log events — NOT binary NetFlow PDUs.
Uses real-world public IPs for external traffic so AbuseIPDB enrichment works.
"""

from __future__ import annotations

from datetime import datetime

from netloggen.core.models import Device, FlowRecord, Topology
from netloggen.core.random_utils import SeededRandom

_COMMON_SERVICES = [
    (80, "tcp"), (443, "tcp"), (22, "tcp"), (53, "udp"), (53, "tcp"),
    (25, "tcp"), (110, "tcp"), (143, "tcp"), (993, "tcp"), (995, "tcp"),
    (3306, "tcp"), (5432, "tcp"), (8080, "tcp"), (8443, "tcp"),
    (123, "udp"), (161, "udp"), (162, "udp"), (514, "udp"),
    (3389, "tcp"), (5060, "udp"), (5061, "tcp"),
]

# TCP flag combinations
_TCP_FLAGS = {
    "syn": 0x02,
    "syn_ack": 0x12,
    "ack": 0x10,
    "psh_ack": 0x18,
    "fin_ack": 0x11,
    "rst": 0x04,
    "rst_ack": 0x14,
    "normal_session": 0x1B,  # SYN+ACK+PSH+FIN
}

# Real-world public IPs with known geo — enables AbuseIPDB enrichment post-ingestion
_EXTERNAL_ENDPOINTS = [
    # (ip, as_number, country, latitude, longitude, label)
    ("8.8.8.8", 15169, "United States", 37.4056, -122.0775, "Google DNS"),
    ("8.8.4.4", 15169, "United States", 37.4056, -122.0775, "Google DNS"),
    ("1.1.1.1", 13335, "United States", 34.0522, -118.2437, "Cloudflare"),
    ("1.0.0.1", 13335, "Australia", -33.8688, 151.2093, "Cloudflare APAC"),
    ("208.67.222.222", 36692, "United States", 37.7749, -122.4194, "OpenDNS"),
    ("9.9.9.9", 19281, "United States", 40.7128, -74.0060, "Quad9"),
    ("13.107.42.14", 8075, "United States", 47.6062, -122.3321, "Microsoft"),
    ("20.190.159.0", 8075, "Netherlands", 52.3676, 4.9041, "Microsoft EU"),
    ("31.13.65.36", 32934, "United States", 37.4856, -122.1489, "Facebook"),
    ("151.101.1.140", 54113, "United States", 37.7749, -122.4194, "Fastly CDN"),
    ("104.16.132.229", 13335, "United States", 37.7749, -122.4194, "Cloudflare CDN"),
    ("52.85.132.91", 16509, "Germany", 50.1109, 8.6821, "AWS Frankfurt"),
    ("18.65.233.187", 16509, "Japan", 35.6762, 139.6503, "AWS Tokyo"),
    ("54.230.129.11", 16509, "United Kingdom", 51.5074, -0.1278, "AWS London"),
    ("35.186.224.25", 15169, "United States", 33.7490, -84.3880, "GCP Atlanta"),
    ("34.149.87.45", 15169, "France", 48.8566, 2.3522, "GCP Paris"),
    ("185.60.216.35", 32934, "Sweden", 59.3293, 18.0686, "Meta EU"),
    ("23.185.0.2", 54113, "Canada", 43.6532, -79.3832, "Fastly Toronto"),
    ("103.235.46.39", 55967, "Singapore", 1.3521, 103.8198, "Baidu SG"),
    ("157.240.1.35", 32934, "Brazil", -23.5505, -46.6333, "Meta LATAM"),
]

_INTERNAL_SUBNETS = [
    "10.1.0.0/16",
    "10.2.0.0/16",
    "10.10.0.0/16",
    "172.16.0.0/16",
]


class NetFlowGenerator:
    def __init__(self, rng: SeededRandom, topology: Topology | None = None):
        self.rng = rng
        # Build site → geo lookup from topology
        self._site_geo: dict[str, dict] = {}
        if topology:
            for site in topology.sites:
                name = site.get("name", "")
                if name and site.get("latitude"):
                    self._site_geo[name] = {
                        "latitude": float(site.get("latitude", 0)),
                        "longitude": float(site.get("longitude", 0)),
                        "country": site.get("country", ""),
                    }

    def _get_site_geo(self, site_name: str) -> dict:
        """Return geo info for a site, with fallback defaults."""
        return self._site_geo.get(site_name, {
            "latitude": 39.8283,
            "longitude": -98.5795,
            "country": "United States",
        })

    def generate_flows(
        self,
        device: Device,
        timestamp: datetime,
        count: int = 10,
        diurnal_factor: float = 1.0,
    ) -> list[FlowRecord]:
        adjusted_count = max(1, int(count * diurnal_factor))
        flows = []

        site_geo = self._get_site_geo(device.site)

        for _ in range(adjusted_count):
            direction = self.rng.weighted_choice(
                ["outbound", "inbound", "internal"],
                [0.5, 0.3, 0.2],
            )

            ext = self.rng.choice(_EXTERNAL_ENDPOINTS)

            if direction == "outbound":
                src_ip = self.rng.random_ip(self.rng.choice(_INTERNAL_SUBNETS))
                dst_ip = ext[0]
                src_as = 65001  # private AS
                dst_as = ext[1]
                src_lat, src_lon, src_country = site_geo["latitude"], site_geo["longitude"], site_geo["country"]
                dst_lat, dst_lon, dst_country = ext[3], ext[4], ext[2]
            elif direction == "inbound":
                src_ip = ext[0]
                dst_ip = self.rng.random_ip(self.rng.choice(_INTERNAL_SUBNETS))
                src_as = ext[1]
                dst_as = 65001
                src_lat, src_lon, src_country = ext[3], ext[4], ext[2]
                dst_lat, dst_lon, dst_country = site_geo["latitude"], site_geo["longitude"], site_geo["country"]
            else:
                subnet1, subnet2 = self.rng.choices(_INTERNAL_SUBNETS, k=2)
                src_ip = self.rng.random_ip(subnet1)
                dst_ip = self.rng.random_ip(subnet2)
                src_as = dst_as = 65001
                src_lat = dst_lat = site_geo["latitude"]
                src_lon = dst_lon = site_geo["longitude"]
                src_country = dst_country = site_geo["country"]

            service = self.rng.choice(_COMMON_SERVICES)
            dst_port = service[0]
            protocol = service[1]
            src_port = self.rng.random_port()

            bytes_total = self.rng.random_bytes_count(
                min_bytes=int(500 * diurnal_factor),
                max_bytes=int(500000 * diurnal_factor),
            )
            # Split into in/out — outbound has more out, inbound has more in
            if direction == "outbound":
                bytes_out = int(bytes_total * self.rng.uniform(0.6, 0.9))
                bytes_in = bytes_total - bytes_out
            elif direction == "inbound":
                bytes_in = int(bytes_total * self.rng.uniform(0.6, 0.9))
                bytes_out = bytes_total - bytes_in
            else:
                bytes_out = int(bytes_total * self.rng.uniform(0.4, 0.6))
                bytes_in = bytes_total - bytes_out

            packets = max(1, bytes_total // self.rng.randint(64, 1500))

            tcp_flags = _TCP_FLAGS["normal_session"] if protocol == "tcp" else 0

            # Pick interfaces from device
            in_iface = ""
            out_iface = ""
            if device.interfaces:
                in_iface = self.rng.choice(device.interfaces).name
                out_iface = self.rng.choice(device.interfaces).name

            flows.append(FlowRecord(
                timestamp=self.rng.jitter_timestamp(timestamp, max_ms=30000),
                device=device.hostname,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                bytes_in=bytes_in,
                bytes_out=bytes_out,
                bytes_total=bytes_total,
                packets_total=packets,
                tcp_flags=tcp_flags,
                input_interface=in_iface,
                output_interface=out_iface,
                src_as=src_as,
                dst_as=dst_as,
                site=device.site,
                src_latitude=src_lat,
                src_longitude=src_lon,
                src_country=src_country,
                dst_latitude=dst_lat,
                dst_longitude=dst_lon,
                dst_country=dst_country,
            ))

        return flows
