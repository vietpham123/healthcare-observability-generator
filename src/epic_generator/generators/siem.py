import xml.etree.ElementTree as ET
import datetime
import ipaddress
import random
import string
import uuid

from .base import BaseGenerator


# Maps high-level session event types to SIEM E1Mid values
EVENT_TYPE_TO_E1MID = {
    "PATIENT_LOOKUP": "PUL_SEARCH_AUDIT",
    "CONTEXTCHANGE": "CONTEXTCHANGE",
    "CHART_CLOSE": "CONTEXTCHANGE",
    "LOGOUT": "HKU_LOGIN",
    "chart_review": "SECURE",
    "order_entry": "IC_SERVICE_AUDIT",
    "note_sign": "IC_SERVICE_AUDIT",
    "result_review": "IC_SERVICE_AUDIT",
    "med_admin": "IC_SERVICE_AUDIT",
    "flowsheet": "IC_SERVICE_AUDIT",
    "report_access": "IC_SERVICE_AUDIT",
    "user_mgmt": "WPSEC_USER_PASSWORD_CHANGE",
    "patient_lookup": "PUL_SEARCH_AUDIT",
    "order_verify": "IC_SERVICE_AUDIT",
    "api_call": "IC_SERVICE_AUDIT",
    "service_audit": "IC_SERVICE_AUDIT",
}

# Full set of SIEM event types for random/legacy mode
DEFAULT_E1MID_VALUES = [
    "IC_SERVICE_AUDIT",
    "AC_BREAK_THE_GLASS_FAILED_ACCESS",
    "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT",
    "AC_BREAK_THE_GLASS_ACCESS",
    "MCMEMEDISA",
    "WPSEC_LOGIN_FAIL",
    "HKU_LOGIN",
    "LOGIN_BLOCKED",
    "FAILEDLOGIN",
    "PUL_SEARCH_AUDIT",
    "WPSEC_2FACTOR_AUTHENTICATION",
    "CONTEXTCHANGE",
    "SECURE",
    "WPSEC_PATIENT_LOOKUP_ATTEMPT",
    "WPSEC_USER_PASSWORD_CHANGE",
    "CTO_LOGIN",
]

_CIDR_CACHE = {}


def _random_ip_from_cidr(cidr):
    """Generate a random IP from a CIDR block. Caches the network for reuse."""
    if cidr not in _CIDR_CACHE:
        network = ipaddress.IPv4Network(cidr)
        net_addr = int(network.network_address)
        num_hosts = network.num_addresses - 2  # exclude network and broadcast
        _CIDR_CACHE[cidr] = (net_addr, num_hosts)
    net_addr, num_hosts = _CIDR_CACHE[cidr]
    if num_hosts <= 0:
        return str(ipaddress.IPv4Address(net_addr + 1))
    offset = random.randint(1, num_hosts)
    return str(ipaddress.IPv4Address(net_addr + offset))


def _random_ip():
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"


def _random_application_id():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=32))


def _random_service_id():
    return str(uuid.uuid4())


def _random_apiid():
    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=22))
    return "0" * 10 + random_part


def _random_clientname():
    return f"VPEPCCHI{random.randint(1, 50)}"


class SIEMGenerator(BaseGenerator):
    """Generates Epic Security-SIEM EventLog XML entries."""

    def __init__(self, syslog_ip_cidr="10.6.3.0/24", sw_version="11.2.0"):
        self.syslog_ip_cidr = syslog_ip_cidr
        self.sw_version = sw_version

    def generate_event(self, session=None, config=None, event_type=None):
        """Generate a SIEM EventLog XML string.

        Args:
            session: UserSession providing correlated context. If None, uses
                     random values from config (legacy mode).
            config: dict with legacy config.json values for fallback.
            event_type: str high-level event type from session state machine.

        Returns:
            str: XML string of the EventLog element.
        """
        config = config or {}
        now = datetime.datetime.now()
        log_entry = ET.Element("EventLog")

        # E1Mid — event type
        e1mid_el = ET.SubElement(log_entry, "E1Mid")
        if event_type and event_type in EVENT_TYPE_TO_E1MID:
            e1mid_el.text = EVENT_TYPE_TO_E1MID[event_type]
        elif "E1Mid" in config:
            e1mid_el.text = random.choice(config["E1Mid"])
        else:
            e1mid_el.text = random.choice(DEFAULT_E1MID_VALUES)

        # EventCnt
        event_cnt_el = ET.SubElement(log_entry, "EventCnt")
        if session:
            event_cnt_el.text = str(session.event_count)
        else:
            event_cnt_el.text = "1"

        # EMPid
        empid_el = ET.SubElement(log_entry, "EMPid")
        if session:
            empid_value = session.user.emp_id
        elif "EMPid" in config:
            empid_value = random.choice(config["EMPid"])
        else:
            empid_value = "99001^EPIC, HYPERSPACE^EPICHYPERSPACE"
        empid_el.text = empid_value

        is_service = "99001" in empid_value

        # Source
        source_el = ET.SubElement(log_entry, "Source")
        if "Source" in config:
            source_el.text = random.choice(config["Source"])
        else:
            source_el.text = "PROD"

        # LWSid
        lwsid_el = ET.SubElement(log_entry, "LWSid")
        if "LWSid" in config:
            lwsid_el.text = random.choice(config["LWSid"])
        else:
            lwsid_el.text = "CLISUP"

        # Action
        action_el = ET.SubElement(log_entry, "Action")
        if "Action" in config:
            action_el.text = random.choice(config["Action"])
        else:
            action_el.text = "Query"

        # Date / Time
        date_el = ET.SubElement(log_entry, "Date")
        date_el.text = now.strftime("%d/%b/%Y")
        time_el = ET.SubElement(log_entry, "Time")
        time_el.text = now.strftime("%H:%M:%S")

        # Flag
        flag_el = ET.SubElement(log_entry, "Flag")
        if "Flag" in config:
            flag_el.text = random.choice(config["Flag"])
        else:
            flag_el.text = "Access History"

        # Mnemonics
        mnemonics_el = ET.SubElement(log_entry, "Mnemonics")
        mnemonic_config = config.get("Mnemonics", {})

        self._add_mnemonic(mnemonics_el, mnemonic_config, "APIID",
                           override=_random_apiid())
        self._add_mnemonic(mnemonics_el, mnemonic_config, "APPLICATIONID",
                           override=_random_application_id())
        self._add_mnemonic(mnemonics_el, mnemonic_config, "CLIENTNAME",
                           override=session.client_name if session else _random_clientname())
        self._add_mnemonic(mnemonics_el, mnemonic_config, "INSTANCEURN")
        self._add_mnemonic(mnemonics_el, mnemonic_config, "IP",
                           override=session.client_ip if session else _random_ip())
        self._add_mnemonic(mnemonics_el, mnemonic_config, "SERVICECATEGORY")
        self._add_mnemonic(mnemonics_el, mnemonic_config, "SERVICEID",
                           override=_random_service_id())
        self._add_mnemonic(mnemonics_el, mnemonic_config, "SERVICEMSGID")
        self._add_mnemonic(mnemonics_el, mnemonic_config, "SERVICENAME")
        self._add_mnemonic(mnemonics_el, mnemonic_config, "SERVICETYPE")

        # SERVICE_USER / SERVICE_USERTYP — blank for service accounts
        if is_service:
            self._add_mnemonic(mnemonics_el, mnemonic_config, "SERVICE_USER",
                               override="")
            self._add_mnemonic(mnemonics_el, mnemonic_config, "SERVICE_USERTYP",
                               override="")
        else:
            service_user_override = None
            service_usertyp_override = None
            if session:
                service_user_override = session.user.get_service_user()
                service_usertyp_override = session.user.user_type
            self._add_mnemonic(mnemonics_el, mnemonic_config, "SERVICE_USER",
                               override=service_user_override)
            self._add_mnemonic(mnemonics_el, mnemonic_config, "SERVICE_USERTYP",
                               override=service_usertyp_override)

        return ET.tostring(log_entry, encoding="unicode")

    def format_output(self, event, environment=None):
        """Wrap XML event in RFC 5424 syslog header.

        Args:
            event: str XML event content.
            environment: optional dict with ip_range, etc.

        Returns:
            str: Full syslog-formatted log line.
        """
        now = datetime.datetime.now()
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "-05:00"
        ts_utc = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        cidr = "10.6.3.0/24"
        if environment and "ip_range" in environment:
            cidr = environment["ip_range"]
        syslog_ip = _random_ip_from_cidr(cidr)

        header = (
            f'{ts},<85>1 {ts_utc} {syslog_ip} Epic 33600 - '
            f'[origin software="Security-SIEM" swVersion="{self.sw_version}"] '
        )
        return header + '<?xml version="1.0"?>' + event

    def _add_mnemonic(self, parent_el, mnemonic_config, name, override=None):
        """Add a Mnemonic sub-element to the Mnemonics parent."""
        mnem_el = ET.SubElement(parent_el, "Mnemonic", Name=name)
        val_el = ET.SubElement(mnem_el, "Value")
        if override is not None:
            val_el.text = override
        elif name in mnemonic_config and mnemonic_config[name]:
            val_el.text = random.choice(mnemonic_config[name])
        else:
            val_el.text = ""

    def generate_sample(self, n=10, config=None):
        """Generate n sample SIEM events to stdout."""
        for _ in range(n):
            event = self.generate_event(session=None, config=config)
            print(self.format_output(event))
