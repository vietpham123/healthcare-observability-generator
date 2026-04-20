import datetime
import json
import random
import uuid

from .base import BaseGenerator


# FHIR API paths that map to Epic Interconnect endpoints
FHIR_ENDPOINTS = [
    {"method": "GET", "path": "/api/FHIR/R4/Patient", "category": "Patient"},
    {"method": "POST", "path": "/api/FHIR/R4/Patient/$match", "category": "Patient"},
    {"method": "GET", "path": "/api/FHIR/R4/Patient/{id}", "category": "Patient"},
    {"method": "GET", "path": "/api/FHIR/R4/Encounter", "category": "Encounter"},
    {"method": "GET", "path": "/api/FHIR/R4/Encounter/{id}", "category": "Encounter"},
    {"method": "GET", "path": "/api/FHIR/R4/Observation", "category": "Observation"},
    {"method": "GET", "path": "/api/FHIR/R4/Observation/{id}", "category": "Observation"},
    {"method": "GET", "path": "/api/FHIR/R4/MedicationRequest", "category": "MedicationRequest"},
    {"method": "POST", "path": "/api/FHIR/R4/MedicationRequest", "category": "MedicationRequest"},
    {"method": "GET", "path": "/api/FHIR/R4/DiagnosticReport", "category": "DiagnosticReport"},
    {"method": "GET", "path": "/api/FHIR/R4/Condition", "category": "Condition"},
    {"method": "GET", "path": "/api/FHIR/R4/AllergyIntolerance", "category": "AllergyIntolerance"},
    {"method": "GET", "path": "/api/FHIR/R4/Immunization", "category": "Immunization"},
    {"method": "GET", "path": "/api/FHIR/R4/Procedure", "category": "Procedure"},
    {"method": "GET", "path": "/api/FHIR/R4/DocumentReference", "category": "DocumentReference"},
    {"method": "POST", "path": "/api/FHIR/R4/Bundle", "category": "Bundle"},
    {"method": "GET", "path": "/api/FHIR/R4/Schedule", "category": "Schedule"},
    {"method": "GET", "path": "/api/FHIR/R4/Slot", "category": "Slot"},
    {"method": "POST", "path": "/api/FHIR/R4/Appointment", "category": "Appointment"},
    {"method": "GET", "path": "/api/FHIR/R4/Coverage", "category": "Coverage"},
]

# Status code distribution: (code, weight)
STATUS_DISTRIBUTION = [
    (200, 80),
    (201, 10),
    (400, 3),
    (401, 2),
    (403, 1),
    (404, 2),
    (500, 1),
    (503, 1),
]

CLIENT_IDS = [
    "MYCHART_MOBILE",
    "MYCHART_WEB",
    "HAIKU_IOS",
    "CANTO_ANDROID",
    "ROVER_IOS",
    "INTERCONNECT_INTERNAL",
    "THIRD_PARTY_LAB",
    "HIE_EXCHANGE",
    "TELEHEALTH_PLATFORM",
]

INSTANCES = [
    "PRD-IC-01",
    "PRD-IC-02",
    "PRD-IC-03",
    "PRD-IC-04",
]

LOG_LEVELS_DISTRIBUTION = [
    ("INFO", 85),
    ("WARN", 8),
    ("ERROR", 5),
    ("DEBUG", 2),
]


def _generate_latency():
    """Generate realistic API latency in ms (normal distribution)."""
    latency = random.gauss(80, 40)
    return max(5, min(5000, int(latency)))


class FHIRGenerator(BaseGenerator):
    """Generates Epic Interconnect-style FHIR API logs in both text and JSON formats."""

    def __init__(self, output_format="text"):
        """
        Args:
            output_format: "text" for single-line log, "json" for structured JSON.
        """
        self.output_format = output_format
        self.error_bias = 0.0  # 0.0 = normal distribution, >0 = force errors

    def generate_event(self, session=None, config=None, event_type=None):
        """Generate a FHIR Interconnect API log entry.

        Returns:
            str: either a single-line text log or a JSON string.
        """
        now = datetime.datetime.now()
        endpoint = random.choice(FHIR_ENDPOINTS)
        method = endpoint["method"]

        # Replace {id} placeholders with realistic IDs
        path = endpoint["path"]
        if "{id}" in path:
            if session and session.current_patient:
                path = path.replace("{id}", session.current_patient.fhir_id)
            else:
                path = path.replace("{id}", str(uuid.uuid4()))

        # Status code — error_bias overrides normal distribution during scenarios
        if self.error_bias > 0 and random.random() < self.error_bias:
            status = random.choice([500, 502, 503, 504])
        else:
            codes, weights = zip(*STATUS_DISTRIBUTION)
            status = random.choices(codes, weights=weights, k=1)[0]

        # Latency
        latency = _generate_latency()
        # Errors tend to be slower
        if status >= 500:
            latency = max(latency, random.randint(500, 3000))

        # Correlation ID
        correlation_id = str(uuid.uuid4())[:12]

        # Instance
        instance = random.choice(INSTANCES)
        thread_num = random.randint(1, 200)

        # Client
        client_id = random.choice(CLIENT_IDS)
        source_ip = f"10.6.3.{random.randint(1, 254)}"
        if session:
            source_ip = session.client_ip

        # Level
        if status >= 500:
            level = "ERROR"
        elif status >= 400:
            level = "WARN"
        else:
            levels, lweights = zip(*LOG_LEVELS_DISTRIBUTION)
            level = random.choices(levels, weights=lweights, k=1)[0]

        ts = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "-05:00"

        if self.output_format == "json":
            entry = {
                "timestamp": ts,
                "level": level,
                "service": "Interconnect",
                "instance": instance,
                "thread": f"interconnect-web-{thread_num}",
                "method": method,
                "path": path,
                "status": status,
                "latency_ms": latency,
                "correlation_id": correlation_id,
                "client_id": client_id,
                "source_ip": source_ip,
                "category": endpoint["category"],
            }
            if session and session.current_patient:
                entry["patient_fhir_id"] = session.current_patient.fhir_id
            if session:
                entry["user_id"] = session.user.username
            return json.dumps(entry)
        else:
            return (
                f"{ts} {level:<5} [{instance}/interconnect-web-{thread_num}] "
                f"{method} {path} {status} {latency}ms "
                f"correlationId={correlation_id} client={client_id} src={source_ip}"
            )

    def format_output(self, event, environment=None):
        """FHIR logs are already fully formatted."""
        return event

    def generate_sample(self, n=10, config=None):
        for _ in range(n):
            event = self.generate_event(config=config)
            print(event)
