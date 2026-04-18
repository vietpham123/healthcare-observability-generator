import datetime
import random
import uuid

from .base import BaseGenerator


# HL7v2 message templates — we build these as raw strings rather than depending
# on hl7apy, so the generator works without external dependencies.
# If hl7apy is available, it will be used for validation.

SEGMENT_SEPARATOR = "\r"
FIELD_SEPARATOR = "|"
COMPONENT_SEPARATOR = "^"
ENCODING_CHARS = "^~\\&"

MESSAGE_TYPES = {
    "ADT_A01": {"type": "ADT", "trigger": "A01", "desc": "Admit/Visit Notification"},
    "ADT_A02": {"type": "ADT", "trigger": "A02", "desc": "Transfer a Patient"},
    "ADT_A03": {"type": "ADT", "trigger": "A03", "desc": "Discharge/End Visit"},
    "ADT_A08": {"type": "ADT", "trigger": "A08", "desc": "Update Patient Information"},
    "ORM_O01": {"type": "ORM", "trigger": "O01", "desc": "Order Message"},
    "ORU_R01": {"type": "ORU", "trigger": "R01", "desc": "Observation Result"},
}

# Event type mappings to HL7 message types
EVENT_TO_HL7 = {
    "PATIENT_LOOKUP": "ADT_A08",
    "discharge": "ADT_A03",
    "order_entry": "ORM_O01",
    "result_review": "ORU_R01",
    "chart_review": "ADT_A08",
    "med_admin": "ORM_O01",
}

RECEIVING_FACILITIES = [
    "LAB_SYSTEM",
    "RADIOLOGY_RIS",
    "PHARMACY_SYSTEM",
    "BILLING_SYSTEM",
    "HIE_GATEWAY",
]

OBSERVATION_IDS = [
    {"id": "2823-3", "name": "Potassium", "unit": "mmol/L",
     "fn": lambda: f"{random.uniform(3.0, 5.5):.1f}"},
    {"id": "2951-2", "name": "Sodium", "unit": "mmol/L",
     "fn": lambda: f"{random.randint(135, 148)}"},
    {"id": "2160-0", "name": "Creatinine", "unit": "mg/dL",
     "fn": lambda: f"{random.uniform(0.5, 2.0):.2f}"},
    {"id": "6690-2", "name": "WBC", "unit": "10*3/uL",
     "fn": lambda: f"{random.uniform(4.0, 12.0):.1f}"},
    {"id": "718-7", "name": "Hemoglobin", "unit": "g/dL",
     "fn": lambda: f"{random.uniform(10.0, 17.0):.1f}"},
    {"id": "777-3", "name": "Platelets", "unit": "10*3/uL",
     "fn": lambda: f"{random.randint(150, 400)}"},
    {"id": "2345-7", "name": "Glucose", "unit": "mg/dL",
     "fn": lambda: f"{random.randint(70, 250)}"},
]


def _ts(fmt="%Y%m%d%H%M%S"):
    return datetime.datetime.now().strftime(fmt)


def _control_id():
    return str(random.randint(100000000, 999999999))


class HL7Generator(BaseGenerator):
    """Generates HL7v2 messages (ADT, ORM, ORU) as pipe-delimited strings."""

    def __init__(self, sending_facility="EPIC", processing_id="P"):
        self.sending_facility = sending_facility
        self.processing_id = processing_id  # P=Production, T=Training, D=Debug

    def generate_event(self, session=None, config=None, event_type=None):
        """Generate an HL7v2 message string.

        Args:
            session: UserSession with patient context.
            config: unused for HL7.
            event_type: session event type to map to HL7 message type.

        Returns:
            str: HL7v2 message as pipe-delimited string.
        """
        hl7_type_key = EVENT_TO_HL7.get(event_type, "ADT_A08")
        msg_info = MESSAGE_TYPES[hl7_type_key]

        segments = [self._build_msh(msg_info)]

        if session and session.current_patient:
            segments.append(self._build_pid(session.current_patient))
            segments.append(self._build_pv1(session))

        if hl7_type_key == "ORM_O01":
            segments.append(self._build_orc(session))
            segments.append(self._build_obr())

        if hl7_type_key == "ORU_R01":
            segments.append(self._build_orc(session))
            segments.append(self._build_obr())
            # Add 1-3 observation segments
            for _ in range(random.randint(1, 3)):
                segments.append(self._build_obx())

        return SEGMENT_SEPARATOR.join(segments)

    def format_output(self, event, environment=None):
        """HL7 messages are output as-is (MLLP framing done by output layer)."""
        return event

    def _build_msh(self, msg_info):
        recv_fac = random.choice(RECEIVING_FACILITIES)
        return (
            f"MSH|{ENCODING_CHARS}|{self.sending_facility}|"
            f"{self.sending_facility}|{recv_fac}|{recv_fac}|"
            f"{_ts()}||{msg_info['type']}^{msg_info['trigger']}^{msg_info['type']}_{msg_info['trigger']}|"
            f"{_control_id()}|{self.processing_id}|2.5.1"
        )

    def _build_pid(self, patient):
        dob = patient.dob.replace("-", "")
        sex_map = {"M": "M", "F": "F", "X": "U"}
        sex = sex_map.get(patient.sex, "U")
        return (
            f"PID|1||{patient.mrn}^^^EPIC^MR~{patient.fhir_id}^^^FHIR^ANON||"
            f"{patient.last_name}^{patient.first_name}||{dob}|{sex}|||"
            f"123 TEST ST^^FAKETOWN^IL^60601^USA||^PRN^PH^5551234567||||||||"
            f"{patient.csn}"
        )

    def _build_pv1(self, session):
        patient = session.current_patient
        enc_map = {
            "ED": "E", "INPATIENT": "I", "OUTPATIENT": "O", "OBSERVATION": "B",
        }
        patient_class = enc_map.get(patient.encounter_type, "I") if patient else "I"
        dept = patient.department if patient else "UNKNOWN"
        attending = session.user.display_name if session else ""
        admit = patient.admit_time.strftime("%Y%m%d%H%M%S") if patient else _ts()
        return (
            f"PV1|1|{patient_class}|{dept}^^^EPIC||||"
            f"{session.user.numeric_id}^{attending}|||||||||||"
            f"{session.session_id}|||||||||||||||||||||||||"
            f"{admit}"
        )

    def _build_orc(self, session):
        order_control = random.choice(["NW", "NW", "NW", "CA", "XO"])
        placer_id = f"ORD-{random.randint(100000, 999999)}"
        filler_id = f"FIL-{random.randint(100000, 999999)}"
        provider = ""
        if session:
            provider = f"{session.user.numeric_id}^{session.user.display_name}"
        return (
            f"ORC|{order_control}|{placer_id}|{filler_id}||CM|||"
            f"{_ts()}|||{provider}"
        )

    def _build_obr(self):
        obs = random.choice(OBSERVATION_IDS)
        return (
            f"OBR|1|||{obs['id']}^{obs['name']}^LN|||{_ts()}||||||||"
            f"|||||||{_ts()}|||F"
        )

    def _build_obx(self):
        obs = random.choice(OBSERVATION_IDS)
        value = obs["fn"]()
        return (
            f"OBX|{random.randint(1, 10)}|NM|{obs['id']}^{obs['name']}^LN||"
            f"{value}|{obs['unit']}|||||F|||{_ts()}"
        )

    def generate_sample(self, n=10, config=None):
        for msg_type_key in list(MESSAGE_TYPES.keys()):
            msg_info = MESSAGE_TYPES[msg_type_key]
            event = self.generate_event(config=config, event_type=None)
            print(event)
            print("---")
            if n <= 0:
                break
            n -= 1
