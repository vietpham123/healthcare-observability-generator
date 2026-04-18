"""Vendor MIB profiles — maps OID trees to device state for SNMP agent responses.

Each vendor profile defines:
- sysObjectID (unique per vendor/platform)
- Standard MIB OIDs (SNMPv2-MIB, IF-MIB, HOST-RESOURCES-MIB)
- Vendor-specific OIDs (CISCO-PROCESS-MIB, PAN-COMMON-MIB, etc.)

OIDs use dotted-string notation without leading dot.
"""

from __future__ import annotations

from typing import Any

# ─── Standard MIB OIDs (all vendors) ──────────────────────────────

# SNMPv2-MIB::system
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_SYS_CONTACT = "1.3.6.1.2.1.1.4.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"
OID_SYS_LOCATION = "1.3.6.1.2.1.1.6.0"
OID_SYS_SERVICES = "1.3.6.1.2.1.1.7.0"

# IF-MIB::interfaces
OID_IF_NUMBER = "1.3.6.1.2.1.2.1.0"
# IF-MIB::ifTable entries (indexed by ifIndex)
OID_IF_INDEX = "1.3.6.1.2.1.2.2.1.1"        # INTEGER
OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"        # OCTET STRING
OID_IF_TYPE = "1.3.6.1.2.1.2.2.1.3"          # INTEGER (6=ethernetCsmacd)
OID_IF_MTU = "1.3.6.1.2.1.2.2.1.4"           # INTEGER
OID_IF_SPEED = "1.3.6.1.2.1.2.2.1.5"         # Gauge32 (bps)
OID_IF_PHYS_ADDR = "1.3.6.1.2.1.2.2.1.6"     # OCTET STRING (MAC)
OID_IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"   # INTEGER (1=up, 2=down, 3=testing)
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"    # INTEGER (1=up, 2=down)
OID_IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"     # Counter32
OID_IF_IN_UCAST_PKTS = "1.3.6.1.2.1.2.2.1.11" # Counter32
OID_IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14"     # Counter32
OID_IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"    # Counter32
OID_IF_OUT_UCAST_PKTS = "1.3.6.1.2.1.2.2.1.17" # Counter32
OID_IF_OUT_ERRORS = "1.3.6.1.2.1.2.2.1.20"    # Counter32

# ifXTable (64-bit counters)
OID_IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"               # OCTET STRING
OID_IF_HC_IN_OCTETS = "1.3.6.1.2.1.31.1.1.1.6"       # Counter64
OID_IF_HC_OUT_OCTETS = "1.3.6.1.2.1.31.1.1.1.10"     # Counter64
OID_IF_HIGH_SPEED = "1.3.6.1.2.1.31.1.1.1.15"        # Gauge32 (Mbps)
OID_IF_ALIAS = "1.3.6.1.2.1.31.1.1.1.18"             # OCTET STRING

# IP-MIB (simplified)
OID_IP_AD_ENT_ADDR = "1.3.6.1.2.1.4.20.1.1"           # IpAddress
OID_IP_AD_ENT_IF_INDEX = "1.3.6.1.2.1.4.20.1.2"       # INTEGER


# ─── Vendor sysObjectID values ────────────────────────────────────

VENDOR_SYS_OBJECT_IDS = {
    "cisco_ios": "1.3.6.1.4.1.9.1.2844",       # Catalyst 9500
    "cisco_nxos": "1.3.6.1.4.1.9.12.3.1.3.1023",
    "cisco_asa": "1.3.6.1.4.1.9.1.2313",        # ASA 5516-X
    "paloalto": "1.3.6.1.4.1.25461.2.3.27",     # PA-5250
    "fortinet": "1.3.6.1.4.1.12356.101.1.1",    # FortiGate-60F
    "juniper": "1.3.6.1.4.1.2636.1.1.1.2.154",
    "arista": "1.3.6.1.4.1.30065.1.3011.7060.2512.7",
    "checkpoint": "1.3.6.1.4.1.2620.1.6.123",
    "f5": "1.3.6.1.4.1.3375.2.1.3.4.43",
    "aruba": "1.3.6.1.4.1.14823.1.1.43",
    "sophos": "1.3.6.1.4.1.21067.2.1.1",
    "sonicwall": "1.3.6.1.4.1.8741.1.1",
    "citrix": "1.3.6.1.4.1.5951.1",
}


# ─── sysDescr templates per vendor ────────────────────────────────

def sys_descr(vendor: str, model: str, os_version: str, hostname: str) -> str:
    """Generate a realistic sysDescr string for a given vendor."""
    templates = {
        "cisco_ios": f"Cisco IOS Software [{model}], {model} Software (CAT9K_IOSXE), Version {os_version}, RELEASE SOFTWARE (fc5)",
        "cisco_nxos": f"Cisco NX-OS(tm) {model}, Software (NX-OS), Version {os_version}, RELEASE SOFTWARE",
        "cisco_asa": f"Cisco Adaptive Security Appliance Version {os_version}",
        "paloalto": f"Palo Alto Networks {model} series firewall, PAN-OS {os_version}",
        "fortinet": f"Fortinet {model} (S/N FGVM00000000000), FortiOS v{os_version},build1234,240101 (GA)",
        "juniper": f"Juniper Networks, Inc. {model} internet router, kernel JUNOS {os_version}",
        "arista": f"Arista Networks EOS version {os_version} running on an Arista Networks {model}",
    }
    return templates.get(vendor, f"{vendor} {model} version {os_version}")


# ─── Site / location mapping ──────────────────────────────────────

SITE_LOCATIONS = {
    "hq-dc": "US-East Data Center, Washington DC",
    "hq-campus": "US-East Campus, Ashburn VA",
    "branch-west": "US-West Branch, San Francisco CA",
}


# ─── Vendor-specific OIDs ─────────────────────────────────────────

# Cisco IOS — CISCO-PROCESS-MIB
OID_CISCO_CPU_5SEC = "1.3.6.1.4.1.9.9.109.1.1.1.1.6.1"    # cpmCPUTotal5sec
OID_CISCO_CPU_1MIN = "1.3.6.1.4.1.9.9.109.1.1.1.1.7.1"    # cpmCPUTotal1min
OID_CISCO_CPU_5MIN = "1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"    # cpmCPUTotal5min
OID_CISCO_MEM_USED = "1.3.6.1.4.1.9.9.48.1.1.1.5.1"       # ciscoMemoryPoolUsed
OID_CISCO_MEM_FREE = "1.3.6.1.4.1.9.9.48.1.1.1.6.1"       # ciscoMemoryPoolFree
OID_CISCO_MEM_NAME = "1.3.6.1.4.1.9.9.48.1.1.1.2.1"       # ciscoMemoryPoolName

# Palo Alto — PAN-COMMON-MIB
OID_PAN_SYS_SW_VERSION = "1.3.6.1.4.1.25461.2.1.2.1.1.0"   # panSysSWVersion
OID_PAN_SYS_SERIAL = "1.3.6.1.4.1.25461.2.1.2.1.3.0"       # panSysSerialNumber
OID_PAN_SYS_CPU = "1.3.6.1.4.1.25461.2.1.2.3.1.0"          # panSessionUtilization (% of max)
OID_PAN_SESS_ACTIVE = "1.3.6.1.4.1.25461.2.1.2.3.3.0"      # panSessionActive
OID_PAN_SESS_MAX = "1.3.6.1.4.1.25461.2.1.2.3.2.0"         # panSessionMax
OID_PAN_GP_ACTIVE_TUNNELS = "1.3.6.1.4.1.25461.2.1.2.5.1.3.0"  # panGPGWTunnelActive

# Fortinet — FORTINET-FORTIGATE-MIB
OID_FG_SYS_CPU = "1.3.6.1.4.1.12356.101.4.1.3.0"           # fgSysCpuUsage
OID_FG_SYS_MEM = "1.3.6.1.4.1.12356.101.4.1.4.0"           # fgSysMemUsage (%)
OID_FG_SYS_DISK = "1.3.6.1.4.1.12356.101.4.1.6.0"          # fgSysDiskUsage (%)
OID_FG_SYS_SESS_COUNT = "1.3.6.1.4.1.12356.101.4.1.8.0"    # fgSysSesCount
OID_FG_SYS_SES_RATE = "1.3.6.1.4.1.12356.101.4.1.11.0"     # fgSysSes6Rate
OID_FG_SYS_SERIAL = "1.3.6.1.4.1.12356.100.1.1.1.0"        # fnSysSerial
OID_FG_VD_SESS_CNT = "1.3.6.1.4.1.12356.101.3.2.1.1.12.1"  # fgVdEntSesCount

# Cisco ASA — CISCO-FIREWALL-MIB
OID_ASA_PERF_CPU = "1.3.6.1.4.1.9.9.109.1.1.1.1.7.1"       # shares CISCO-PROCESS-MIB
OID_ASA_CONN_IN_USE = "1.3.6.1.4.1.9.9.147.1.2.2.2.1.5.40.6"  # cfwConnectionStatValue (current)
OID_ASA_CONN_HIGH = "1.3.6.1.4.1.9.9.147.1.2.2.2.1.5.40.7"    # cfwConnectionStatValue (high)


# ─── OID tree builder ─────────────────────────────────────────────

def build_device_oid_tree(device_state: dict[str, Any]) -> dict[str, tuple[str, Any]]:
    """Build a flat OID→(type, value) dict for a single device.

    Returns dict mapping OID string → (asn1_type, value) where
    asn1_type is one of: 'str', 'int', 'gauge', 'counter', 'counter64',
    'timeticks', 'oid', 'ipaddr'.
    """
    vendor = device_state.get("vendor", "")
    hostname = device_state.get("hostname", "unknown")
    model = device_state.get("model", "")
    os_version = device_state.get("os_version", "")
    site = device_state.get("site", "")
    serial = device_state.get("serial_number", "")
    uptime = int(device_state.get("uptime_seconds", 0))
    cpu = float(device_state.get("cpu_utilization", 0))
    mem = float(device_state.get("memory_utilization", 0))
    sessions = int(device_state.get("session_count", 0))
    interfaces = device_state.get("interfaces", {})

    tree: dict[str, tuple[str, Any]] = {}

    # ── SNMPv2-MIB::system group ──
    tree[OID_SYS_DESCR] = ("str", sys_descr(vendor, model, os_version, hostname))
    tree[OID_SYS_OBJECT_ID] = ("oid", VENDOR_SYS_OBJECT_IDS.get(vendor, "1.3.6.1.4.1.99999"))
    tree[OID_SYS_UPTIME] = ("timeticks", uptime * 100)  # centiseconds
    tree[OID_SYS_CONTACT] = ("str", "Network Operations <noc@example.com>")
    tree[OID_SYS_NAME] = ("str", hostname)
    tree[OID_SYS_LOCATION] = ("str", SITE_LOCATIONS.get(site, site))
    tree[OID_SYS_SERVICES] = ("int", 78 if vendor in ("cisco_ios", "cisco_nxos") else 72)

    # ── IF-MIB ──
    iface_list = sorted(interfaces.items(), key=lambda x: x[1].get("if_index", 0))
    tree[OID_IF_NUMBER] = ("int", len(iface_list))

    for iface_name, iface_data in iface_list:
        idx = iface_data.get("if_index", 0)
        if idx == 0:
            continue

        speed_str = iface_data.get("speed", "1G")
        speed_bps = _parse_speed(speed_str)
        is_up = iface_data.get("status", "up") == "up"
        is_admin_down = iface_data.get("status") == "admin-down"
        description = iface_data.get("description", "")
        ip_addr = iface_data.get("ip_address", "")

        # Strip CIDR prefix from IP
        if "/" in ip_addr:
            ip_addr = ip_addr.split("/")[0]

        # ifTable entries
        tree[f"{OID_IF_INDEX}.{idx}"] = ("int", idx)
        tree[f"{OID_IF_DESCR}.{idx}"] = ("str", iface_name)
        tree[f"{OID_IF_TYPE}.{idx}"] = ("int", _if_type(iface_name))
        tree[f"{OID_IF_MTU}.{idx}"] = ("int", 9216 if "TenGig" in iface_name else 1500)
        tree[f"{OID_IF_SPEED}.{idx}"] = ("gauge", min(speed_bps, 4294967295))  # cap at Gauge32 max
        tree[f"{OID_IF_PHYS_ADDR}.{idx}"] = ("str", _fake_mac(hostname, idx))
        tree[f"{OID_IF_ADMIN_STATUS}.{idx}"] = ("int", 2 if is_admin_down else 1)
        tree[f"{OID_IF_OPER_STATUS}.{idx}"] = ("int", 1 if is_up else 2)

        # Traffic counters from metrics overlay
        in_octets = int(iface_data.get("network.interface.traffic.in", 0))
        out_octets = int(iface_data.get("network.interface.traffic.out", 0))
        in_errors = int(iface_data.get("network.interface.errors.in", 0))
        out_errors = int(iface_data.get("network.interface.errors.out", 0))

        tree[f"{OID_IF_IN_OCTETS}.{idx}"] = ("counter", in_octets & 0xFFFFFFFF)
        tree[f"{OID_IF_IN_UCAST_PKTS}.{idx}"] = ("counter", (in_octets // 500) & 0xFFFFFFFF)
        tree[f"{OID_IF_IN_ERRORS}.{idx}"] = ("counter", in_errors & 0xFFFFFFFF)
        tree[f"{OID_IF_OUT_OCTETS}.{idx}"] = ("counter", out_octets & 0xFFFFFFFF)
        tree[f"{OID_IF_OUT_UCAST_PKTS}.{idx}"] = ("counter", (out_octets // 500) & 0xFFFFFFFF)
        tree[f"{OID_IF_OUT_ERRORS}.{idx}"] = ("counter", out_errors & 0xFFFFFFFF)

        # ifXTable (64-bit counters)
        tree[f"{OID_IF_NAME}.{idx}"] = ("str", iface_name)
        tree[f"{OID_IF_HC_IN_OCTETS}.{idx}"] = ("counter64", in_octets)
        tree[f"{OID_IF_HC_OUT_OCTETS}.{idx}"] = ("counter64", out_octets)
        tree[f"{OID_IF_HIGH_SPEED}.{idx}"] = ("gauge", speed_bps // 1_000_000)  # Mbps
        tree[f"{OID_IF_ALIAS}.{idx}"] = ("str", description)

        # IP address table entries (indexed by IP octets)
        if ip_addr and ip_addr != "":
            ip_oid_suffix = ip_addr  # e.g., "10.0.1.1"
            tree[f"{OID_IP_AD_ENT_ADDR}.{ip_oid_suffix}"] = ("ipaddr", ip_addr)
            tree[f"{OID_IP_AD_ENT_IF_INDEX}.{ip_oid_suffix}"] = ("int", idx)

    # ── Vendor-specific OIDs ──
    _add_vendor_oids(tree, vendor, cpu, mem, sessions, serial, os_version, uptime)

    return tree


def _add_vendor_oids(
    tree: dict[str, tuple[str, Any]],
    vendor: str,
    cpu: float,
    mem: float,
    sessions: int,
    serial: str,
    os_version: str,
    uptime: int,
) -> None:
    """Add vendor-specific OIDs to the tree."""
    total_mem_kb = 4_194_304  # 4GB in KB

    if vendor in ("cisco_ios", "cisco_nxos"):
        tree[OID_CISCO_CPU_5SEC] = ("gauge", int(cpu + 2))
        tree[OID_CISCO_CPU_1MIN] = ("gauge", int(cpu))
        tree[OID_CISCO_CPU_5MIN] = ("gauge", max(1, int(cpu - 3)))
        used_kb = int(total_mem_kb * mem / 100)
        free_kb = total_mem_kb - used_kb
        tree[OID_CISCO_MEM_NAME] = ("str", "Processor")
        tree[OID_CISCO_MEM_USED] = ("gauge", used_kb * 1024)
        tree[OID_CISCO_MEM_FREE] = ("gauge", free_kb * 1024)

    elif vendor == "cisco_asa":
        tree[OID_CISCO_CPU_5SEC] = ("gauge", int(cpu + 2))
        tree[OID_CISCO_CPU_1MIN] = ("gauge", int(cpu))
        tree[OID_CISCO_CPU_5MIN] = ("gauge", max(1, int(cpu - 3)))
        tree[OID_ASA_CONN_IN_USE] = ("gauge", sessions)
        tree[OID_ASA_CONN_HIGH] = ("gauge", int(sessions * 1.2))
        used_kb = int(total_mem_kb * mem / 100)
        free_kb = total_mem_kb - used_kb
        tree[OID_CISCO_MEM_NAME] = ("str", "System memory")
        tree[OID_CISCO_MEM_USED] = ("gauge", used_kb * 1024)
        tree[OID_CISCO_MEM_FREE] = ("gauge", free_kb * 1024)

    elif vendor == "paloalto":
        tree[OID_PAN_SYS_SW_VERSION] = ("str", os_version)
        tree[OID_PAN_SYS_SERIAL] = ("str", serial)
        tree[OID_PAN_SYS_CPU] = ("gauge", int(cpu))
        tree[OID_PAN_SESS_ACTIVE] = ("gauge", sessions)
        tree[OID_PAN_SESS_MAX] = ("gauge", 2_000_000)  # PA-5250 max
        tree[OID_PAN_GP_ACTIVE_TUNNELS] = ("gauge", max(0, sessions // 100))

    elif vendor == "fortinet":
        tree[OID_FG_SYS_SERIAL] = ("str", serial)
        tree[OID_FG_SYS_CPU] = ("gauge", int(cpu))
        tree[OID_FG_SYS_MEM] = ("gauge", int(mem))
        tree[OID_FG_SYS_DISK] = ("gauge", 25)  # 25% disk
        tree[OID_FG_SYS_SESS_COUNT] = ("gauge", sessions)
        tree[OID_FG_SYS_SES_RATE] = ("gauge", max(1, sessions // 60))
        tree[OID_FG_VD_SESS_CNT] = ("gauge", sessions)


# ─── Helpers ──────────────────────────────────────────────────────

def _parse_speed(speed_str: str) -> int:
    """Parse speed string like '10G', '1G', '100M' to bps."""
    s = speed_str.strip().upper()
    if s.endswith("G"):
        return int(float(s[:-1]) * 1_000_000_000)
    elif s.endswith("M"):
        return int(float(s[:-1]) * 1_000_000)
    elif s.endswith("K"):
        return int(float(s[:-1]) * 1_000)
    try:
        return int(s)
    except ValueError:
        return 1_000_000_000


def _if_type(iface_name: str) -> int:
    """Return ifType based on interface name."""
    name = iface_name.lower()
    if "loopback" in name:
        return 24   # softwareLoopback
    elif "vlan" in name:
        return 136  # l3ipvlan
    elif "tunnel" in name:
        return 131  # tunnel
    elif "management" in name:
        return 6    # ethernetCsmacd
    elif "port-channel" in name or "bond" in name:
        return 161  # ieee8023adLag
    return 6        # ethernetCsmacd


def _fake_mac(hostname: str, if_index: int) -> str:
    """Generate a deterministic MAC address from hostname + ifIndex."""
    h = abs(hash(hostname)) & 0xFFFFFFFF
    b1 = (h >> 24) & 0xFE  # clear multicast bit
    b2 = (h >> 16) & 0xFF
    b3 = (h >> 8) & 0xFF
    b4 = h & 0xFF
    b5 = (if_index >> 8) & 0xFF
    b6 = if_index & 0xFF
    return f"{b1:02x}:{b2:02x}:{b3:02x}:{b4:02x}:{b5:02x}:{b6:02x}"
