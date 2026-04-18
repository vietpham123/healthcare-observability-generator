import xml.etree.ElementTree as ET
import datetime
import random
import uuid

from .base import BaseGenerator


MYCHART_EVENTS = {
    "MYCHART_LOGIN": {
        "e1mid": "MYCHART_LOGIN",
        "action": "Login",
        "flag": "MyChart Access",
    },
    "MYCHART_MSG_SEND": {
        "e1mid": "MYCHART_MSG_SEND",
        "action": "Create",
        "flag": "MyChart Messaging",
    },
    "MYCHART_MSG_READ": {
        "e1mid": "MYCHART_MSG_READ",
        "action": "Read",
        "flag": "MyChart Messaging",
    },
    "MYCHART_APPT_SCHEDULE": {
        "e1mid": "MYCHART_APPT_SCHEDULE",
        "action": "Create",
        "flag": "MyChart Scheduling",
    },
    "MYCHART_RESULT_VIEW": {
        "e1mid": "MYCHART_RESULT_VIEW",
        "action": "Read",
        "flag": "MyChart Results",
    },
    "MYCHART_PROXY_ACCESS": {
        "e1mid": "MYCHART_PROXY_ACCESS",
        "action": "Read",
        "flag": "MyChart Proxy",
    },
    "MYCHART_RX_REFILL": {
        "e1mid": "MYCHART_RX_REFILL",
        "action": "Create",
        "flag": "MyChart Pharmacy",
    },
}

MYCHART_EVENT_TYPES = list(MYCHART_EVENTS.keys())

MYCHART_INSTANCE_URNS = [
    "urn:DTU:MyChartMobile",
    "urn:VPC:MyChartMobile",
    "urn:DTU:MyChartWeb",
    "urn:VPC:MyChartWeb",
]

MYCHART_PLATFORMS = [
    "MyChart iOS",
    "MyChart Android",
    "MyChart Web",
]

MESSAGE_SUBJECTS = [
    "Medication Question",
    "Appointment Request",
    "Test Result Question",
    "Prescription Refill",
    "Referral Request",
    "Billing Question",
    "General Health Question",
    "Follow-up Visit Request",
]

APPOINTMENT_TYPES = [
    "Primary Care - New Patient",
    "Primary Care - Follow Up",
    "Cardiology - Consultation",
    "Dermatology - Follow Up",
    "Orthopedics - Follow Up",
    "Lab Work",
    "Radiology - Imaging",
    "Telehealth Visit",
]

RESULT_TYPES_MC = [
    "Complete Blood Count",
    "Basic Metabolic Panel",
    "Lipid Panel",
    "Urinalysis",
    "Chest X-Ray Report",
    "COVID-19 PCR",
    "Hemoglobin A1C",
    "Thyroid Panel",
]

REFILL_MEDICATIONS = [
    "Lisinopril 10mg",
    "Atorvastatin 20mg",
    "Metformin 500mg",
    "Amlodipine 5mg",
    "Omeprazole 20mg",
    "Levothyroxine 50mcg",
    "Sertraline 50mg",
    "Losartan 50mg",
]


class MyChartGenerator(BaseGenerator):
    """Generates MyChart patient portal EventLog XML entries."""

    def generate_event(self, session=None, config=None, event_type=None):
        """Generate a MyChart portal event.

        Args:
            session: UserSession (used for patient context if available).
            config: dict for fallback values.
            event_type: one of the MYCHART_EVENT_TYPES, or None for random.

        Returns:
            str: XML string of the EventLog element.
        """
        config = config or {}
        now = datetime.datetime.now()

        if event_type and event_type in MYCHART_EVENTS:
            evt = MYCHART_EVENTS[event_type]
        else:
            evt_key = random.choice(MYCHART_EVENT_TYPES)
            evt = MYCHART_EVENTS[evt_key]
            event_type = evt_key

        log_entry = ET.Element("EventLog")

        ET.SubElement(log_entry, "E1Mid").text = evt["e1mid"]
        ET.SubElement(log_entry, "EventCnt").text = "1"

        # MyChart events use patient MRN as the identifier instead of employee ID
        if session and session.current_patient:
            ET.SubElement(log_entry, "EMPid").text = session.current_patient.emp_style_name
        else:
            # Generate a fake MyChart patient identifier
            mrn = f"MRN-{random.randint(10000, 99999):08d}"
            ET.SubElement(log_entry, "EMPid").text = f"{mrn}^TESTPATIENT, PORTAL"

        ET.SubElement(log_entry, "Source").text = random.choice(config.get("Source", ["PROD"]))
        ET.SubElement(log_entry, "LWSid").text = "MYCHART"
        ET.SubElement(log_entry, "Action").text = evt["action"]
        ET.SubElement(log_entry, "Date").text = now.strftime("%d/%b/%Y")
        ET.SubElement(log_entry, "Time").text = now.strftime("%H:%M:%S")
        ET.SubElement(log_entry, "Flag").text = evt["flag"]

        mnemonics_el = ET.SubElement(log_entry, "Mnemonics")

        # Common mnemonics
        self._add_mn(mnemonics_el, "INSTANCEURN", random.choice(MYCHART_INSTANCE_URNS))
        self._add_mn(mnemonics_el, "IP", f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}")
        self._add_mn(mnemonics_el, "PLATFORM", random.choice(MYCHART_PLATFORMS))
        self._add_mn(mnemonics_el, "SESSION_ID", str(uuid.uuid4()))
        self._add_mn(mnemonics_el, "SERVICECATEGORY", "MyChartMobile")

        # Patient context
        if session and session.current_patient:
            p = session.current_patient
            self._add_mn(mnemonics_el, "PATIENT_MRN", p.mrn)
            self._add_mn(mnemonics_el, "PATIENT_NAME", p.full_name)

        # Event-specific mnemonics
        self._add_event_mnemonics(mnemonics_el, event_type)

        return ET.tostring(log_entry, encoding="unicode")

    def format_output(self, event, environment=None):
        """MyChart events use the same syslog format."""
        now = datetime.datetime.now()
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "-05:00"
        ts_utc = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        ip = f"10.6.3.{random.randint(1, 254)}"
        if environment and "ip_range" in environment:
            from generators.siem import _random_ip_from_cidr
            ip = _random_ip_from_cidr(environment["ip_range"])

        header = (
            f'{ts},<85>1 {ts_utc} {ip} Epic 33600 - '
            f'[origin software="Security-SIEM" swVersion="11.2.0"] '
        )
        return header + '<?xml version="1.0"?>' + event

    def _add_event_mnemonics(self, parent, event_type):
        if event_type == "MYCHART_LOGIN":
            self._add_mn(parent, "LOGIN_METHOD", random.choice([
                "Password", "Biometric", "SSO", "2FA",
            ]))
            self._add_mn(parent, "DEVICE_TYPE", random.choice([
                "iPhone", "Android Phone", "iPad", "Web Browser",
            ]))

        elif event_type == "MYCHART_MSG_SEND":
            self._add_mn(parent, "MESSAGE_SUBJECT", random.choice(MESSAGE_SUBJECTS))
            self._add_mn(parent, "RECIPIENT_TYPE", random.choice([
                "Primary Care Provider", "Specialist", "Nurse",
            ]))
            self._add_mn(parent, "MESSAGE_ID", str(uuid.uuid4()))

        elif event_type == "MYCHART_MSG_READ":
            self._add_mn(parent, "MESSAGE_ID", str(uuid.uuid4()))
            self._add_mn(parent, "SENDER_TYPE", random.choice([
                "Provider", "System", "Care Team",
            ]))

        elif event_type == "MYCHART_APPT_SCHEDULE":
            self._add_mn(parent, "APPOINTMENT_TYPE", random.choice(APPOINTMENT_TYPES))
            self._add_mn(parent, "APPOINTMENT_ID", str(uuid.uuid4()))
            days_out = random.randint(1, 90)
            appt_date = (datetime.datetime.now() + datetime.timedelta(days=days_out))
            self._add_mn(parent, "APPOINTMENT_DATE", appt_date.strftime("%Y-%m-%d"))

        elif event_type == "MYCHART_RESULT_VIEW":
            self._add_mn(parent, "RESULT_TYPE", random.choice(RESULT_TYPES_MC))
            self._add_mn(parent, "RESULT_STATUS", random.choice([
                "Final", "Final", "Final", "Preliminary",
            ]))
            self._add_mn(parent, "RESULT_DATE",
                         (datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 14))).strftime("%Y-%m-%d"))

        elif event_type == "MYCHART_PROXY_ACCESS":
            self._add_mn(parent, "PROXY_RELATIONSHIP", random.choice([
                "Parent", "Guardian", "Spouse", "Caregiver",
            ]))
            self._add_mn(parent, "PROXY_PATIENT_MRN",
                         f"MRN-{random.randint(10000, 99999):08d}")

        elif event_type == "MYCHART_RX_REFILL":
            self._add_mn(parent, "MEDICATION_NAME", random.choice(REFILL_MEDICATIONS))
            self._add_mn(parent, "PHARMACY", random.choice([
                "CVS Pharmacy #1234", "Walgreens #5678",
                "Hospital Outpatient Pharmacy", "Mail Order Pharmacy",
            ]))
            self._add_mn(parent, "REFILL_ID", str(uuid.uuid4()))

    def _add_mn(self, parent, name, value):
        mn = ET.SubElement(parent, "Mnemonic", Name=name)
        ET.SubElement(mn, "Value").text = value

    def generate_sample(self, n=10, config=None):
        for evt_type in MYCHART_EVENT_TYPES[:n]:
            event = self.generate_event(config=config, event_type=evt_type)
            print(self.format_output(event))
