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
    "LOGIN": "BCA_LOGIN_SUCCESS",
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
    # Direct E1Mid pass-through for anomaly injection
    "FAILEDLOGIN": "FAILEDLOGIN",
    "LOGIN_BLOCKED": "LOGIN_BLOCKED",
    "WPSEC_LOGIN_FAIL": "WPSEC_LOGIN_FAIL",
    "btg_access": "AC_BREAK_THE_GLASS_ACCESS",
    "btg_failed": "AC_BREAK_THE_GLASS_FAILED_ACCESS",
    "btg_inappropriate": "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT",
    "2fa": "WPSEC_2FACTOR_AUTHENTICATION",
    "secure": "SECURE",
    "BCA_LOGIN_SUCCESS": "BCA_LOGIN_SUCCESS",
    "HKU_LOGIN": "HKU_LOGIN",
    "CTO_LOGIN": "CTO_LOGIN",
    "PUL_SEARCH_AUDIT": "PUL_SEARCH_AUDIT",
    "IC_SERVICE_AUDIT": "IC_SERVICE_AUDIT",
    "CHART_ACCESS": "SECURE",
    "WPSEC_PATIENT_LOOKUP_ATTEMPT": "WPSEC_PATIENT_LOOKUP_ATTEMPT",
    "AC_BREAK_THE_GLASS_ACCESS": "AC_BREAK_THE_GLASS_ACCESS",
    "AC_BREAK_THE_GLASS_FAILED_ACCESS": "AC_BREAK_THE_GLASS_FAILED_ACCESS",
    "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT": "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT",
    "WPSEC_2FACTOR_AUTHENTICATION": "WPSEC_2FACTOR_AUTHENTICATION",
}

# Mnemonic sets vary by E1Mid event type
LOGIN_MNEMONICS = [
    "CLIENT_TYPE", "INTERNET_AREA", "IP", "LOGINERROR",
    "LOGIN_CLIENT_ID", "LOGIN_CONTEXT", "LOGIN_DEVICE",
    "LOGIN_LDAP_ID", "LOGIN_REVAL", "SOURCE", "UID",
    "LOGIN_CONTEXTS", "PERIM_AUTH_ST", "HYP_ACCESS_ID", "REMOTE_IP",
]

WORKSTATION_IDS = [
    "CLISUP", "GHM4021MED3", "GHM2015SURG1", "GHM6032ICU2",
    "GHM1108RAD1", "GHM3244ORTH2", "GHM7401ENDO1", "GHM5518PEDS4",
    "RSC9003FAM1", "RSC8100ONC2", "RSC1215CARD1", "VPN80032INF1",
    "HFM6024NURS3", "HFM4417PSYC1", "DOC3302PFS1", "DOC5501HIM2",
    "WHC1108CLIN4", "WHC2030FRON1", "LAB6010PATH1", "LAB7201MICRO2",
    "PHR4415DISP1", "EMR9900ADMIN", "OPS5510TECH3", "BIO2233PULM1",
]

LOGIN_ERRORS = ["ELDAP_FAIL_SBIND", "E_BAD_NAME", "E_LOCKED_OUT",
                "E_EXPIRED_PW", "E_DISABLED"]

LOGIN_CONTEXTS = [
    "Login [0]", "Medication Administration [26]",
    "E-Prescribing Controlled Medications - First Context [41]",
    "Chart Review [3]", "Order Entry [5]",
]

CLIENT_TYPES = [
    "Registered Hyperdrive [2]", "Hyperspace Client [1]",
    "Mobile Haiku [4]", "Mobile Canto [5]",
]

LOGIN_SOURCE_TYPES = [
    "Hyperspace Web Standalone / Hyperdrive [13]",
    "Text [2]", "Haiku [4]", "Canto [5]",
]

HYP_ACCESS_IDS = [
    "100007^Hyperspace Internal Hyperdrive [COMPILED RECORD] [HYPERSPACE ACCESS OVERRIDE DEFAULT]",
    "100008^Hyperspace External Web [COMPILED RECORD]",
    "100009^Hyperspace Mobile Haiku [COMPILED RECORD]",
]

# Full set of SIEM event types for random/legacy mode
DEFAULT_E1MID_VALUES = [
    "IC_SERVICE_AUDIT",
    "BCA_LOGIN_SUCCESS",
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
        """Generate a SIEM EventLog XML string with event-specific mnemonics."""
        config = config or {}
        now = datetime.datetime.now()
        log_entry = ET.Element("EventLog")

        # E1Mid
        e1mid_el = ET.SubElement(log_entry, "E1Mid")
        if event_type and event_type in EVENT_TYPE_TO_E1MID:
            e1mid_el.text = EVENT_TYPE_TO_E1MID[event_type]
        elif "E1Mid" in config:
            e1mid_el.text = random.choice(config["E1Mid"])
        else:
            e1mid_el.text = random.choice(DEFAULT_E1MID_VALUES)
        e1mid_value = e1mid_el.text

        is_login_event = e1mid_value in (
            "FAILEDLOGIN", "WPSEC_LOGIN_FAIL", "LOGIN_BLOCKED",
            "BCA_LOGIN_SUCCESS", "HKU_LOGIN", "CTO_LOGIN",
        )

        # EventCnt
        ET.SubElement(log_entry, "EventCnt").text = str(session.event_count) if session else "1"

        # EMPid - sometimes empty for failed logins
        empid_el = ET.SubElement(log_entry, "EMPid")
        if is_login_event and e1mid_value == "FAILEDLOGIN" and random.random() < 0.3:
            empid_value = ""
        elif session:
            empid_value = session.user.emp_id
        elif "EMPid" in config:
            empid_value = random.choice(config["EMPid"])
        else:
            empid_value = "990001^EPIC, HYPERSPACE^EPICHYPERSPACE"
        empid_el.text = empid_value
        is_service = empid_value.startswith("990") or empid_value.startswith("901")

        # Source - lowercase prd like real Epic
        ET.SubElement(log_entry, "Source").text = random.choice(["prd", "prd", "prd", "prd", "SUP"])

        # LWSid - expanded workstation IDs
        ET.SubElement(log_entry, "LWSid").text = random.choice(WORKSTATION_IDS)

        # Action
        ET.SubElement(log_entry, "Action").text = "Query"

        # Date/Time - real Epic format: M/D/YYYY, 12-hour with leading space
        date_el = ET.SubElement(log_entry, "Date")
        date_el.text = f"{now.month}/{now.day}/{now.year}"
        time_el = ET.SubElement(log_entry, "Time")
        h12 = now.hour % 12 or 12
        ampm = "AM" if now.hour < 12 else "PM"
        time_el.text = f" {h12}:{now.strftime('%M:%S')} {ampm}"

        # Flag - ^^ delimiters like real Epic
        flag_el = ET.SubElement(log_entry, "Flag")
        flag_el.text = "^^Workflow Logging" if is_login_event else "Access History^^"

        # Mnemonics - different set per event type
        mnemonics_el = ET.SubElement(log_entry, "Mnemonics")
        mnemonic_config = config.get("Mnemonics", {})
        if is_login_event:
            self._build_login_mnemonics(mnemonics_el, session, e1mid_value, empid_value)
        else:
            self._build_service_mnemonics(mnemonics_el, mnemonic_config, session, is_service)

        return ET.tostring(log_entry, encoding="unicode")

    def _build_login_mnemonics(self, parent, session, e1mid_value, empid_value):
        """Build login-specific mnemonics (FAILEDLOGIN, BCA_LOGIN_SUCCESS)."""
        ip = session.client_ip if session else _random_ip()
        remote_ip = _random_ip()
        is_failed = e1mid_value in ("FAILEDLOGIN", "WPSEC_LOGIN_FAIL", "LOGIN_BLOCKED")
        self._add_mnemonic(parent, {}, "CLIENT_TYPE", override=random.choice(CLIENT_TYPES))
        self._add_mnemonic(parent, {}, "INTERNET_AREA", override=random.choice(["Internal [1]", "Internal [1]", "External [2]"]))
        self._add_mnemonic(parent, {}, "IP", override=f"{ip}\\{remote_ip}")
        self._add_mnemonic(parent, {}, "LOGINERROR", override=random.choice(LOGIN_ERRORS) if is_failed else "")
        self._add_mnemonic(parent, {}, "LOGIN_CLIENT_ID", override=str(uuid.uuid4()))
        self._add_mnemonic(parent, {}, "LOGIN_CONTEXT", override=random.choice(LOGIN_CONTEXTS))
        self._add_mnemonic(parent, {}, "LOGIN_DEVICE", override="0^Default Login")
        ldap_id = ""
        if empid_value and "^" in empid_value:
            parts = empid_value.split("^")
            ldap_id = parts[-1] if len(parts) > 2 else ""
        self._add_mnemonic(parent, {}, "LOGIN_LDAP_ID", override=ldap_id)
        self._add_mnemonic(parent, {}, "LOGIN_REVAL", override=random.choice(["", "", "Yes [1]"]))
        self._add_mnemonic(parent, {}, "SOURCE", override=random.choice(LOGIN_SOURCE_TYPES))
        uid = ""
        if empid_value and "^" in empid_value:
            parts = empid_value.split("^")
            uid = f"{parts[0]}^{parts[1]}" if len(parts) > 1 else empid_value
        self._add_mnemonic(parent, {}, "UID", override=uid)
        self._add_mnemonic(parent, {}, "LOGIN_CONTEXTS", override=random.choice(LOGIN_CONTEXTS))
        self._add_mnemonic(parent, {}, "PERIM_AUTH_ST", override=random.choice(["No Perimeter [4]", "No Perimeter [4]", ""]))
        self._add_mnemonic(parent, {}, "HYP_ACCESS_ID", override=random.choice(HYP_ACCESS_IDS))
        self._add_mnemonic(parent, {}, "REMOTE_IP", override=remote_ip)

    def _build_service_mnemonics(self, parent, mnemonic_config, session, is_service):
        """Build service-audit mnemonics (IC_SERVICE_AUDIT, SECURE, etc.)."""
        self._add_mnemonic(parent, mnemonic_config, "APIID", override=_random_apiid())
        self._add_mnemonic(parent, mnemonic_config, "APPLICATIONID", override=_random_application_id())
        self._add_mnemonic(parent, mnemonic_config, "CLIENTNAME", override=session.client_name if session else _random_clientname())
        self._add_mnemonic(parent, mnemonic_config, "HOSTNAME", override=_random_clientname())
        self._add_mnemonic(parent, mnemonic_config, "INSTANCEURN")
        self._add_mnemonic(parent, mnemonic_config, "IP", override=session.client_ip if session else _random_ip())
        self._add_mnemonic(parent, mnemonic_config, "SERVICECATEGORY")
        self._add_mnemonic(parent, mnemonic_config, "SERVICEID", override=_random_service_id())
        self._add_mnemonic(parent, mnemonic_config, "SERVICEMSGID")
        self._add_mnemonic(parent, mnemonic_config, "SERVICENAME")
        self._add_mnemonic(parent, mnemonic_config, "SERVICETYPE")
        if is_service:
            self._add_mnemonic(parent, mnemonic_config, "SERVICE_USER", override="")
            self._add_mnemonic(parent, mnemonic_config, "SERVICE_USERTYP", override="")
        else:
            suser = session.user.get_service_user() if session else None
            sutype = session.user.user_type if session else None
            self._add_mnemonic(parent, mnemonic_config, "SERVICE_USER", override=suser)
            self._add_mnemonic(parent, mnemonic_config, "SERVICE_USERTYP", override=sutype)


    _SYSLOG_PIDS = [20560, 21904, 27632, 33600, 14208, 18440]

    def format_output(self, event, environment=None):
        """Wrap XML event in RFC 5424 syslog header - microsecond precision, variable PIDs."""
        now = datetime.datetime.now()
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.%f") + "-05:00"
        ts_utc = now.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        cidr = "10.6.3.0/24"
        if environment and "ip_range" in environment:
            cidr = environment["ip_range"]
        syslog_ip = _random_ip_from_cidr(cidr)
        pid = random.choice(self._SYSLOG_PIDS)
        header = (
            f'{ts},<85>1 {ts_utc} {syslog_ip} Epic {pid} - '
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
