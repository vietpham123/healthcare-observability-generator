from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import random
import uuid


@dataclass
class Patient:
    mrn: str
    csn: str
    fhir_id: str
    first_name: str
    last_name: str
    dob: str
    sex: str
    department: str
    encounter_type: str
    admit_time: datetime = field(default_factory=datetime.now)
    attending_id: str = ""

    @property
    def full_name(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def emp_style_name(self):
        """Format like Epic EMPid patient reference."""
        return f"{self.mrn}^{self.last_name}, {self.first_name}"

    def to_dict(self):
        return {
            "mrn": self.mrn,
            "csn": self.csn,
            "fhir_id": self.fhir_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "dob": self.dob,
            "sex": self.sex,
            "department": self.department,
            "encounter_type": self.encounter_type,
            "admit_time": self.admit_time.isoformat(),
            "attending_id": self.attending_id,
        }

    @classmethod
    def from_dict(cls, data):
        admit_time = data.get("admit_time")
        if isinstance(admit_time, str):
            admit_time = datetime.fromisoformat(admit_time)
        elif admit_time is None:
            admit_time = datetime.now()
        return cls(
            mrn=data["mrn"],
            csn=data["csn"],
            fhir_id=data["fhir_id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            dob=data["dob"],
            sex=data["sex"],
            department=data["department"],
            encounter_type=data["encounter_type"],
            admit_time=admit_time,
            attending_id=data.get("attending_id", ""),
        )


DEPARTMENTS = [
    "EMERGENCY",
    "MED-SURG 4W",
    "MED-SURG 5E",
    "ICU-EAST",
    "ICU-WEST",
    "NICU",
    "L&D",
    "OR-MAIN",
    "PACU",
    "CARDIOLOGY",
    "ONCOLOGY",
    "RADIOLOGY",
    "ORTHOPEDICS",
    "NEUROLOGY",
    "PEDIATRICS",
    "PSYCHIATRY",
    "REHAB",
    "OUTPATIENT CLINIC A",
    "OUTPATIENT CLINIC B",
    "URGENT CARE",
]

ENCOUNTER_TYPES = ["ED", "INPATIENT", "OUTPATIENT", "OBSERVATION"]


def generate_patient_pool(count=75):
    """Generate a pool of synthetic patients with clearly fake names."""
    first_names = [
        "ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF",
        "HOTEL", "INDIA", "JULIET", "KILO", "LIMA", "MIKE", "NOVEMBER",
        "OSCAR", "PAPA", "QUEBEC", "ROMEO", "SIERRA", "TANGO", "UNIFORM",
        "VICTOR", "WHISKEY", "XRAY", "YANKEE", "ZULU", "ASH", "BIRCH",
        "CEDAR", "DUNE", "ELM", "FERN", "GLEN", "HAZEL", "IVY", "JADE",
        "KELP", "LARK", "MOSS", "NOEL", "OAK", "PINE", "QUILL", "REED",
        "SAGE", "THORN", "URN", "VALE", "WREN", "YEW",
    ]
    last_names = [
        "TESTPATIENT", "SIMULATED", "SYNTHETIC", "PRACTICE", "TRAINING",
        "DEMO", "SAMPLE", "FAKERSON", "NOTREAL", "TESTCASE",
        "PLACEHOLDER", "SPECIMEN", "MOCKDATA", "EXERCISE", "DRILL",
    ]

    patients = []
    for i in range(count):
        mrn = f"MRN-{10000 + i:08d}"
        csn = f"CSN-{200000 + random.randint(0, 99999):08d}"
        fhir_id = str(uuid.uuid4())
        first = random.choice(first_names)
        last = random.choice(last_names)
        year = random.randint(1940, 2020)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        dob = f"{year:04d}-{month:02d}-{day:02d}"
        sex = random.choice(["M", "F", "X"])
        dept = random.choice(DEPARTMENTS)
        enc_type = random.choice(ENCOUNTER_TYPES)
        admit_offset_hours = random.randint(0, 72)
        admit_time = datetime.now() - timedelta(hours=admit_offset_hours)

        patients.append(Patient(
            mrn=mrn,
            csn=csn,
            fhir_id=fhir_id,
            first_name=first,
            last_name=last,
            dob=dob,
            sex=sex,
            department=dept,
            encounter_type=enc_type,
            admit_time=admit_time,
        ))

    return patients


def load_patients(config_path):
    """Load patients from a JSON file."""
    with open(config_path, "r") as f:
        data = json.load(f)
    return [Patient.from_dict(p) for p in data]


def save_patients(patients, config_path):
    """Save patient pool to JSON file."""
    data = [p.to_dict() for p in patients]
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
