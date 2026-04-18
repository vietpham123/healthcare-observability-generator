import datetime
import json
import random
import uuid

from .base import BaseGenerator


class FHIRResourceGenerator(BaseGenerator):
    """Generates synthetic FHIR R4 JSON resources that correspond to log events.

    Produces Patient, Encounter, Observation, and MedicationRequest resources
    using manual JSON templates (no external FHIR library required).
    """

    RESOURCE_TYPES = ["Patient", "Encounter", "Observation", "MedicationRequest"]

    CONDITION_CODES = [
        {"code": "38341003", "display": "Hypertensive disorder", "system": "http://snomed.info/sct"},
        {"code": "44054006", "display": "Type 2 diabetes mellitus", "system": "http://snomed.info/sct"},
        {"code": "195662009", "display": "Acute viral pharyngitis", "system": "http://snomed.info/sct"},
        {"code": "10509002", "display": "Acute bronchitis", "system": "http://snomed.info/sct"},
        {"code": "431855005", "display": "Chronic kidney disease stage 1", "system": "http://snomed.info/sct"},
    ]

    OBSERVATION_CODES = [
        {"code": "8867-4", "display": "Heart rate", "unit": "/min",
         "fn": lambda: random.randint(55, 120)},
        {"code": "8310-5", "display": "Body temperature", "unit": "degF",
         "fn": lambda: round(random.uniform(97.0, 101.5), 1)},
        {"code": "8480-6", "display": "Systolic blood pressure", "unit": "mmHg",
         "fn": lambda: random.randint(90, 180)},
        {"code": "8462-4", "display": "Diastolic blood pressure", "unit": "mmHg",
         "fn": lambda: random.randint(50, 110)},
        {"code": "2710-2", "display": "Oxygen saturation", "unit": "%",
         "fn": lambda: random.randint(88, 100)},
        {"code": "29463-7", "display": "Body weight", "unit": "kg",
         "fn": lambda: round(random.uniform(45.0, 140.0), 1)},
        {"code": "8302-2", "display": "Body height", "unit": "cm",
         "fn": lambda: random.randint(140, 200)},
        {"code": "2345-7", "display": "Glucose", "unit": "mg/dL",
         "fn": lambda: random.randint(70, 250)},
    ]

    MEDICATION_CODES = [
        {"code": "197361", "display": "Acetaminophen 325 MG Oral Tablet",
         "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
        {"code": "310798", "display": "Metoprolol Tartrate 25 MG Oral Tablet",
         "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
        {"code": "847232", "display": "Heparin 5000 UNT/ML QS Injectable Solution",
         "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
        {"code": "312289", "display": "Ondansetron 4 MG Oral Tablet",
         "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
        {"code": "197696", "display": "Amoxicillin 500 MG Oral Capsule",
         "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
        {"code": "311027", "display": "Lisinopril 10 MG Oral Tablet",
         "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    ]

    def generate_event(self, session=None, config=None, event_type=None):
        """Generate a FHIR R4 JSON resource.

        Args:
            session: UserSession for context.
            config: unused.
            event_type: one of "Patient", "Encounter", "Observation", "MedicationRequest",
                        or a session event type that maps to a resource.

        Returns:
            str: JSON string of the FHIR resource.
        """
        resource_type = self._map_event_to_resource(event_type)

        if resource_type == "Patient":
            resource = self._build_patient(session)
        elif resource_type == "Encounter":
            resource = self._build_encounter(session)
        elif resource_type == "Observation":
            resource = self._build_observation(session)
        elif resource_type == "MedicationRequest":
            resource = self._build_medication_request(session)
        else:
            resource = self._build_patient(session)

        return json.dumps(resource)

    def format_output(self, event, environment=None):
        return event

    def _map_event_to_resource(self, event_type):
        mapping = {
            "Patient": "Patient",
            "Encounter": "Encounter",
            "Observation": "Observation",
            "MedicationRequest": "MedicationRequest",
            "PATIENT_LOOKUP": "Patient",
            "chart_review": "Encounter",
            "order_entry": "MedicationRequest",
            "result_review": "Observation",
            "med_admin": "MedicationRequest",
        }
        return mapping.get(event_type, random.choice(self.RESOURCE_TYPES))

    def _build_patient(self, session):
        patient = session.current_patient if session and session.current_patient else None
        resource_id = patient.fhir_id if patient else str(uuid.uuid4())
        return {
            "resourceType": "Patient",
            "id": resource_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": datetime.datetime.now().isoformat(),
                "source": "urn:epic-simulator",
            },
            "identifier": [
                {
                    "use": "usual",
                    "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
                    "system": "urn:oid:1.2.840.114350",
                    "value": patient.mrn if patient else f"MRN-{random.randint(10000, 99999):08d}",
                }
            ],
            "active": True,
            "name": [
                {
                    "use": "official",
                    "family": patient.last_name if patient else "TESTPATIENT",
                    "given": [patient.first_name if patient else "ALPHA"],
                }
            ],
            "gender": {"M": "male", "F": "female", "X": "other"}.get(
                patient.sex if patient else "M", "unknown"
            ),
            "birthDate": patient.dob if patient else "1980-01-01",
        }

    def _build_encounter(self, session):
        patient = session.current_patient if session and session.current_patient else None
        enc_class_map = {
            "ED": {"code": "EMER", "display": "emergency"},
            "INPATIENT": {"code": "IMP", "display": "inpatient encounter"},
            "OUTPATIENT": {"code": "AMB", "display": "ambulatory"},
            "OBSERVATION": {"code": "OBSENC", "display": "observation encounter"},
        }
        enc_type = patient.encounter_type if patient else "INPATIENT"
        enc_class = enc_class_map.get(enc_type, enc_class_map["INPATIENT"])

        return {
            "resourceType": "Encounter",
            "id": str(uuid.uuid4()),
            "meta": {"lastUpdated": datetime.datetime.now().isoformat(), "source": "urn:epic-simulator"},
            "status": random.choice(["in-progress", "in-progress", "in-progress", "finished"]),
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": enc_class["code"],
                "display": enc_class["display"],
            },
            "subject": {
                "reference": f"Patient/{patient.fhir_id}" if patient else f"Patient/{uuid.uuid4()}",
                "display": patient.full_name if patient else "TESTPATIENT, ALPHA",
            },
            "period": {
                "start": (patient.admit_time if patient else datetime.datetime.now()).isoformat(),
            },
            "location": [
                {
                    "location": {
                        "display": patient.department if patient else "UNKNOWN",
                    },
                    "status": "active",
                }
            ],
        }

    def _build_observation(self, session):
        patient = session.current_patient if session and session.current_patient else None
        obs = random.choice(self.OBSERVATION_CODES)
        value = obs["fn"]()

        return {
            "resourceType": "Observation",
            "id": str(uuid.uuid4()),
            "meta": {"lastUpdated": datetime.datetime.now().isoformat(), "source": "urn:epic-simulator"},
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": obs["code"],
                        "display": obs["display"],
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{patient.fhir_id}" if patient else f"Patient/{uuid.uuid4()}",
            },
            "effectiveDateTime": datetime.datetime.now().isoformat(),
            "valueQuantity": {
                "value": value,
                "unit": obs["unit"],
                "system": "http://unitsofmeasure.org",
                "code": obs["unit"],
            },
        }

    def _build_medication_request(self, session):
        patient = session.current_patient if session and session.current_patient else None
        med = random.choice(self.MEDICATION_CODES)
        requester = session.user if session else None

        return {
            "resourceType": "MedicationRequest",
            "id": str(uuid.uuid4()),
            "meta": {"lastUpdated": datetime.datetime.now().isoformat(), "source": "urn:epic-simulator"},
            "status": random.choice(["active", "active", "active", "completed", "cancelled"]),
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": med["system"],
                        "code": med["code"],
                        "display": med["display"],
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{patient.fhir_id}" if patient else f"Patient/{uuid.uuid4()}",
            },
            "authoredOn": datetime.datetime.now().isoformat(),
            "requester": {
                "reference": f"Practitioner/{requester.numeric_id}" if requester else "Practitioner/unknown",
                "display": requester.display_name if requester else "UNKNOWN",
            },
        }

    def generate_sample(self, n=10, config=None):
        for rtype in self.RESOURCE_TYPES:
            event = self.generate_event(config=config, event_type=rtype)
            print(event)
            print()
