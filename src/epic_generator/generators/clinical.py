import xml.etree.ElementTree as ET
import datetime
import random
import uuid

from .base import BaseGenerator


# Clinical event types and their E1Mid values
CLINICAL_E1MID = {
    "chart_review": "CHART_ACCESS",
    "order_entry": "ORDER_ENTRY",
    "med_admin": "MED_ADMIN",
    "note_sign": "NOTE_SIGN",
    "result_review": "RESULT_REVIEW",
    "flowsheet": "FLOWSHEET_UPDATE",
    "discharge": "DISCHARGE",
    "order_verify": "ORDER_VERIFY",
}

ORDER_TYPES = [
    {"type": "LAB", "name": "CBC with Differential", "code": "LAB-0012"},
    {"type": "LAB", "name": "Basic Metabolic Panel", "code": "LAB-0034"},
    {"type": "LAB", "name": "Comprehensive Metabolic Panel", "code": "LAB-0056"},
    {"type": "LAB", "name": "Troponin I", "code": "LAB-0078"},
    {"type": "LAB", "name": "Urinalysis", "code": "LAB-0091"},
    {"type": "LAB", "name": "Blood Culture", "code": "LAB-0103"},
    {"type": "LAB", "name": "Prothrombin Time", "code": "LAB-0115"},
    {"type": "MED", "name": "Acetaminophen 650mg PO", "code": "MED-1001"},
    {"type": "MED", "name": "Metoprolol 25mg PO", "code": "MED-1023"},
    {"type": "MED", "name": "Heparin 5000 units SubQ", "code": "MED-1045"},
    {"type": "MED", "name": "Ondansetron 4mg IV", "code": "MED-1067"},
    {"type": "MED", "name": "Morphine 2mg IV", "code": "MED-1089"},
    {"type": "MED", "name": "Normal Saline 1000mL IV", "code": "MED-1112"},
    {"type": "MED", "name": "Amoxicillin 500mg PO", "code": "MED-1134"},
    {"type": "MED", "name": "Insulin Lispro 5 units SubQ", "code": "MED-1156"},
    {"type": "IMAGING", "name": "Chest X-Ray PA/Lateral", "code": "IMG-2001"},
    {"type": "IMAGING", "name": "CT Head without Contrast", "code": "IMG-2023"},
    {"type": "IMAGING", "name": "CT Abdomen/Pelvis with Contrast", "code": "IMG-2045"},
    {"type": "IMAGING", "name": "MRI Brain with/without Contrast", "code": "IMG-2067"},
    {"type": "IMAGING", "name": "Ultrasound Abdomen Complete", "code": "IMG-2089"},
]

MEDICATIONS = [
    {"name": "Acetaminophen", "dose": "650mg", "route": "PO", "frequency": "Q6H PRN"},
    {"name": "Metoprolol Tartrate", "dose": "25mg", "route": "PO", "frequency": "BID"},
    {"name": "Heparin", "dose": "5000 units", "route": "SubQ", "frequency": "Q8H"},
    {"name": "Ondansetron", "dose": "4mg", "route": "IV", "frequency": "Q6H PRN"},
    {"name": "Morphine Sulfate", "dose": "2mg", "route": "IV", "frequency": "Q4H PRN"},
    {"name": "Normal Saline", "dose": "1000mL", "route": "IV", "frequency": "Continuous"},
    {"name": "Vancomycin", "dose": "1g", "route": "IV", "frequency": "Q12H"},
    {"name": "Insulin Lispro", "dose": "5 units", "route": "SubQ", "frequency": "AC"},
    {"name": "Furosemide", "dose": "40mg", "route": "IV", "frequency": "Q12H"},
    {"name": "Potassium Chloride", "dose": "20mEq", "route": "PO", "frequency": "Daily"},
]

NOTE_TYPES = [
    {"type": "H&P", "name": "History and Physical"},
    {"type": "PROGRESS", "name": "Progress Note"},
    {"type": "DISCHARGE", "name": "Discharge Summary"},
    {"type": "CONSULT", "name": "Consultation Note"},
    {"type": "PROCEDURE", "name": "Procedure Note"},
    {"type": "NURSING", "name": "Nursing Assessment"},
    {"type": "ADDENDUM", "name": "Addendum"},
]

RESULT_TYPES = [
    {"type": "LAB", "name": "CBC", "value": "WBC 7.2, Hgb 14.1, Plt 245"},
    {"type": "LAB", "name": "BMP", "value": "Na 140, K 4.1, Cl 102, CO2 24, BUN 15, Cr 0.9, Glu 105"},
    {"type": "LAB", "name": "Troponin I", "value": "< 0.04 ng/mL"},
    {"type": "LAB", "name": "Prothrombin Time", "value": "INR 1.1, PT 12.5 sec"},
    {"type": "IMAGING", "name": "Chest X-Ray", "value": "No acute cardiopulmonary process"},
    {"type": "IMAGING", "name": "CT Head", "value": "No acute intracranial abnormality"},
    {"type": "IMAGING", "name": "CT Abdomen", "value": "No acute abdominal pathology"},
]

DISCHARGE_DISPOSITIONS = [
    "Home",
    "Home with Home Health",
    "Skilled Nursing Facility",
    "Rehabilitation Facility",
    "Against Medical Advice",
    "Transferred to Another Facility",
    "Expired",
]

FLOWSHEET_ROWS = [
    {"name": "Temperature", "value_fn": lambda: f"{random.uniform(97.0, 101.5):.1f} F"},
    {"name": "Heart Rate", "value_fn": lambda: f"{random.randint(55, 120)} bpm"},
    {"name": "Blood Pressure", "value_fn": lambda: f"{random.randint(90, 180)}/{random.randint(50, 110)} mmHg"},
    {"name": "Respiratory Rate", "value_fn": lambda: f"{random.randint(12, 28)} /min"},
    {"name": "SpO2", "value_fn": lambda: f"{random.randint(88, 100)}%"},
    {"name": "Pain Scale", "value_fn": lambda: f"{random.randint(0, 10)}/10"},
    {"name": "Weight", "value_fn": lambda: f"{random.uniform(45.0, 140.0):.1f} kg"},
]


class ClinicalGenerator(BaseGenerator):
    """Generates clinical workflow EventLog XML entries with extended mnemonics."""

    def generate_event(self, session=None, config=None, event_type=None):
        """Generate a clinical EventLog XML string.

        Args:
            session: UserSession with current patient context.
            config: dict for fallback values.
            event_type: one of the clinical event types.

        Returns:
            str: XML string of the EventLog element.
        """
        config = config or {}
        now = datetime.datetime.now()
        log_entry = ET.Element("EventLog")

        e1mid = CLINICAL_E1MID.get(event_type, "IC_SERVICE_AUDIT")

        ET.SubElement(log_entry, "E1Mid").text = e1mid
        ET.SubElement(log_entry, "EventCnt").text = str(session.event_count if session else 1)

        emp_id = session.user.emp_id if session else "99001^EPIC, HYPERSPACE^EPICHYPERSPACE"
        ET.SubElement(log_entry, "EMPid").text = emp_id

        ET.SubElement(log_entry, "Source").text = random.choice(config.get("Source", ["PROD"]))
        ET.SubElement(log_entry, "LWSid").text = random.choice(config.get("LWSid", ["CLISUP"]))
        ET.SubElement(log_entry, "Action").text = self._action_for_event(event_type)
        ET.SubElement(log_entry, "Date").text = now.strftime("%d/%b/%Y")
        ET.SubElement(log_entry, "Time").text = now.strftime("%H:%M:%S")
        ET.SubElement(log_entry, "Flag").text = "Clinical"

        mnemonics_el = ET.SubElement(log_entry, "Mnemonics")

        # Patient context
        if session and session.current_patient:
            p = session.current_patient
            self._add_mn(mnemonics_el, "PATIENT_MRN", p.mrn)
            self._add_mn(mnemonics_el, "PATIENT_CSN", p.csn)
            self._add_mn(mnemonics_el, "PATIENT_NAME", p.full_name)
            self._add_mn(mnemonics_el, "DEPARTMENT", p.department)
            self._add_mn(mnemonics_el, "ENCOUNTER_TYPE", p.encounter_type)

        # Session context
        if session:
            self._add_mn(mnemonics_el, "CLIENTNAME", session.client_name)
            self._add_mn(mnemonics_el, "IP", session.client_ip)
            self._add_mn(mnemonics_el, "SESSION_ID", session.session_id)

        # Event-specific mnemonics
        self._add_event_specific_mnemonics(mnemonics_el, event_type, session)

        return ET.tostring(log_entry, encoding="unicode")

    def format_output(self, event, environment=None):
        """Clinical events use the same syslog format as SIEM."""
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

    def _action_for_event(self, event_type):
        actions = {
            "chart_review": "Read",
            "order_entry": "Create",
            "med_admin": "Update",
            "note_sign": "Sign",
            "result_review": "Read",
            "flowsheet": "Update",
            "discharge": "Update",
            "order_verify": "Verify",
        }
        return actions.get(event_type, "Query")

    def _add_event_specific_mnemonics(self, parent, event_type, session):
        if event_type == "order_entry":
            order = random.choice(ORDER_TYPES)
            self._add_mn(parent, "ORDER_TYPE", order["type"])
            self._add_mn(parent, "ORDER_NAME", order["name"])
            self._add_mn(parent, "ORDER_CODE", order["code"])
            self._add_mn(parent, "ORDER_ID", str(uuid.uuid4()))
            if session:
                self._add_mn(parent, "ORDERING_PROVIDER", session.user.display_name)

        elif event_type == "med_admin":
            med = random.choice(MEDICATIONS)
            self._add_mn(parent, "MEDICATION_NAME", med["name"])
            self._add_mn(parent, "MEDICATION_DOSE", med["dose"])
            self._add_mn(parent, "MEDICATION_ROUTE", med["route"])
            self._add_mn(parent, "MEDICATION_FREQUENCY", med["frequency"])
            self._add_mn(parent, "MAR_ACTION", random.choice(["Given", "Given", "Given", "Held", "Refused"]))
            if session:
                self._add_mn(parent, "ADMINISTERING_USER", session.user.display_name)

        elif event_type == "note_sign":
            note = random.choice(NOTE_TYPES)
            self._add_mn(parent, "NOTE_TYPE", note["type"])
            self._add_mn(parent, "NOTE_TITLE", note["name"])
            self._add_mn(parent, "NOTE_ID", str(uuid.uuid4()))
            if session:
                self._add_mn(parent, "AUTHOR", session.user.display_name)

        elif event_type == "result_review":
            result = random.choice(RESULT_TYPES)
            self._add_mn(parent, "RESULT_TYPE", result["type"])
            self._add_mn(parent, "RESULT_NAME", result["name"])
            self._add_mn(parent, "RESULT_VALUE", result["value"])
            if session:
                self._add_mn(parent, "REVIEWING_PROVIDER", session.user.display_name)

        elif event_type == "discharge":
            disposition = random.choice(DISCHARGE_DISPOSITIONS)
            self._add_mn(parent, "DISCHARGE_DISPOSITION", disposition)
            self._add_mn(parent, "DISCHARGE_TIME", datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))

        elif event_type == "flowsheet":
            row = random.choice(FLOWSHEET_ROWS)
            self._add_mn(parent, "FLOWSHEET_ROW", row["name"])
            self._add_mn(parent, "FLOWSHEET_VALUE", row["value_fn"]())
            self._add_mn(parent, "FLOWSHEET_TIME", datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))

        elif event_type == "chart_review":
            self._add_mn(parent, "ACCESS_REASON", random.choice([
                "Direct Care", "Care Coordination", "Quality Review",
                "Training", "Administrative",
            ]))

        elif event_type == "order_verify":
            order = random.choice(ORDER_TYPES)
            self._add_mn(parent, "ORDER_TYPE", order["type"])
            self._add_mn(parent, "ORDER_NAME", order["name"])
            self._add_mn(parent, "ORDER_CODE", order["code"])
            self._add_mn(parent, "VERIFY_ACTION", random.choice(["Verified", "Verified", "Rejected"]))

    def _add_mn(self, parent, name, value):
        mn = ET.SubElement(parent, "Mnemonic", Name=name)
        ET.SubElement(mn, "Value").text = value

    def generate_sample(self, n=10, config=None):
        for event_type in list(CLINICAL_E1MID.keys())[:n]:
            event = self.generate_event(config=config, event_type=event_type)
            print(self.format_output(event))
