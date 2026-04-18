import json
import os
import random
import sys
import time
from datetime import datetime

from models.patient import Patient, load_patients, generate_patient_pool, save_patients
from models.user import User, load_users, save_users
from models.session import UserSession
from generators.siem import SIEMGenerator
from generators.clinical import ClinicalGenerator
from generators.hl7 import HL7Generator
from generators.fhir import FHIRGenerator
from generators.mychart import MyChartGenerator
from generators.fhir_resources import FHIRResourceGenerator
from generators.etl import ETLGenerator
from outputs.file_output import FileOutput
from scheduler import Scheduler


MAX_CONCURRENT_SESSIONS = 20
BASE_NEW_SESSION_PROBABILITY = 0.3
SERVICE_EVENT_PROBABILITY = 0.2

# Clinical event types that should also produce correlated HL7 messages
HL7_CORRELATED_EVENTS = {"order_entry", "med_admin", "result_review", "discharge"}
# Clinical event types that should also produce FHIR resources
FHIR_CORRELATED_EVENTS = {"PATIENT_LOOKUP", "order_entry", "result_review", "med_admin", "chart_review"}


class Orchestrator:
    """Main simulation engine that manages sessions and generates correlated logs
    across all Epic subsystems (SIEM, Clinical, HL7, FHIR, MyChart, ETL)."""

    def __init__(self, config=None, config_dir=None, output=None, environment=None,
                 scenario=None, generators_enabled=None):
        """Initialize the orchestrator.

        Args:
            config: dict from legacy config.json (optional).
            config_dir: path to config/ directory with users.json, patients.json (optional).
            output: an output instance (e.g., FileOutput). If None, prints to stdout.
            environment: dict with environment-specific values (ip_range, source, etc.).
            scenario: str name of scenario to load from config/scenarios/.
            generators_enabled: list of generator names to enable. None = all.
                                Options: "siem", "clinical", "hl7", "fhir", "mychart",
                                         "fhir_resources", "etl"
        """
        self.config = config or {}
        self.environment = environment
        self.output = output

        # Initialize all generators
        self.siem_gen = SIEMGenerator()
        self.clinical_gen = ClinicalGenerator()
        self.hl7_gen = HL7Generator()
        self.fhir_gen = FHIRGenerator(output_format="text")
        self.fhir_json_gen = FHIRGenerator(output_format="json")
        self.mychart_gen = MyChartGenerator()
        self.fhir_resource_gen = FHIRResourceGenerator()
        self.etl_gen = ETLGenerator()

        # Determine which generators are active
        all_generators = {"siem", "clinical", "hl7", "fhir", "mychart", "fhir_resources", "etl"}
        if generators_enabled:
            self.enabled = set(generators_enabled) & all_generators
        else:
            self.enabled = all_generators

        self.users = []
        self.patients = []
        self.active_sessions = []
        self.service_users = []
        self.human_users = []

        # Initialize scheduler
        scenario_dir = None
        if config_dir:
            scenario_dir = os.path.join(config_dir, "scenarios")
        self.scheduler = Scheduler(scenario=scenario, scenario_dir=scenario_dir)

        self._load_data(config_dir)

        # ETL tick counter (ETL events are less frequent)
        self._etl_tick_counter = 0

    def _load_data(self, config_dir):
        """Load user and patient pools from config directory or generate defaults."""
        if config_dir:
            users_path = os.path.join(config_dir, "users.json")
            patients_path = os.path.join(config_dir, "patients.json")

            if os.path.exists(users_path):
                self.users = load_users(users_path)
            if os.path.exists(patients_path):
                self.patients = load_patients(patients_path)

        # If no users loaded, derive from legacy config EMPid values
        if not self.users and "EMPid" in self.config:
            self.users = self._derive_users_from_legacy()

        # If still no users, generate a minimal set
        if not self.users:
            self.users = self._derive_users_from_legacy()

        # If no patients loaded, generate a pool
        if not self.patients:
            self.patients = generate_patient_pool(75)

        # Separate service accounts
        self.service_users = [u for u in self.users if u.is_service_account]
        self.human_users = [u for u in self.users if not u.is_service_account]

    def _derive_users_from_legacy(self):
        """Create User objects from legacy config EMPid strings."""
        users = []
        roles = ["PHYSICIAN", "NURSE", "ADMIN", "PHARMACIST", "TECH"]
        departments = [
            "EMERGENCY", "MED-SURG 4W", "ICU-EAST", "CARDIOLOGY",
            "ONCOLOGY", "RADIOLOGY", "ORTHOPEDICS", "OUTPATIENT CLINIC A",
        ]

        emp_ids = self.config.get("EMPid", [
            "99001^EPIC, HYPERSPACE^EPICHYPERSPACE",
            "1001^PHAM, VIET^VPHAM",
            "1002^CANNON, DENNY^DCANNON",
        ])

        for emp_id in emp_ids:
            parts = emp_id.split("^")
            numeric_id = parts[0]
            username = parts[2] if len(parts) > 2 else parts[0]

            if "99001" in numeric_id:
                users.append(User(
                    emp_id=emp_id,
                    username=username,
                    role="SYSTEM",
                    department="IT",
                    user_type="System",
                    is_service_account=True,
                ))
            else:
                role = random.choice(roles)
                from models.user import ROLE_TO_USER_TYPE
                users.append(User(
                    emp_id=emp_id,
                    username=username,
                    role=role,
                    department=random.choice(departments),
                    user_type=ROLE_TO_USER_TYPE.get(role, "Admin"),
                ))
        return users

    def _get_volume_multiplier(self):
        """Get current volume multiplier from scheduler."""
        return self.scheduler.get_volume_multiplier()

    def _maybe_start_session(self):
        """Probabilistically start a new user session based on time-of-day curve."""
        if not self.human_users:
            return

        if self.scheduler.should_start_session(
            max_sessions=MAX_CONCURRENT_SESSIONS,
            current_sessions=len(self.active_sessions),
            base_probability=BASE_NEW_SESSION_PROBABILITY,
        ):
            user = random.choice(self.human_users)
            session = UserSession.create(user)
            self.active_sessions.append(session)

            # Generate login event (SIEM)
            if "siem" in self.enabled:
                event = self.siem_gen.generate_event(
                    session=session, config=self.config, event_type="login"
                )
                self._emit_siem(event)

    def _advance_sessions(self):
        """Advance each active session and generate correlated events."""
        still_active = []
        for session in self.active_sessions:
            event_type = session.advance_state(self.patients)
            if event_type:
                # SIEM event
                if "siem" in self.enabled:
                    siem_event = self.siem_gen.generate_event(
                        session=session, config=self.config, event_type=event_type
                    )
                    self._emit_siem(siem_event)

                # Clinical event (for clinical action types)
                if "clinical" in self.enabled and event_type in (
                    "chart_review", "order_entry", "med_admin", "note_sign",
                    "result_review", "flowsheet", "discharge", "order_verify",
                ):
                    clin_event = self.clinical_gen.generate_event(
                        session=session, config=self.config, event_type=event_type
                    )
                    self._emit_clinical(clin_event)

                # Correlated HL7 message
                if "hl7" in self.enabled and event_type in HL7_CORRELATED_EVENTS:
                    if self.scheduler.should_generate_hl7_event(base_probability=0.6):
                        hl7_event = self.hl7_gen.generate_event(
                            session=session, config=self.config, event_type=event_type
                        )
                        self._emit_hl7(hl7_event)

                # Correlated FHIR resource
                if "fhir_resources" in self.enabled and event_type in FHIR_CORRELATED_EVENTS:
                    fhir_res = self.fhir_resource_gen.generate_event(
                        session=session, config=self.config, event_type=event_type
                    )
                    self._emit_generic(fhir_res, "FHIR-R4")

            if session.is_active:
                still_active.append(session)

        self.active_sessions = still_active

    def _maybe_generate_service_event(self):
        """Generate API/service account events (not tied to human sessions)."""
        if not self.service_users:
            return

        multiplier = self._get_volume_multiplier()
        if random.random() < SERVICE_EVENT_PROBABILITY * multiplier:
            service_user = random.choice(self.service_users)
            temp_session = UserSession.create(service_user)
            temp_session.state = "LOGGED_IN"

            if "siem" in self.enabled:
                event = self.siem_gen.generate_event(
                    session=temp_session, config=self.config, event_type="api_call"
                )
                self._emit_siem(event)

    def _maybe_generate_fhir_event(self):
        """Generate standalone FHIR/Interconnect API log events."""
        if "fhir" not in self.enabled:
            return

        if self.scheduler.should_generate_fhir_event():
            # Pick a random active session for context, or None
            session = random.choice(self.active_sessions) if self.active_sessions else None
            fhir_event = self.fhir_gen.generate_event(session=session)
            self._emit_generic(fhir_event, "FHIR-API")

    def _maybe_generate_mychart_event(self):
        """Generate MyChart patient portal events."""
        if "mychart" not in self.enabled:
            return

        if self.scheduler.should_generate_mychart_event():
            # MyChart events can use patient context from active sessions
            session = None
            if self.active_sessions:
                session = random.choice(self.active_sessions)
            mychart_event = self.mychart_gen.generate_event(session=session)
            formatted = self.mychart_gen.format_output(mychart_event, self.environment)
            self._emit_raw(formatted)

    def _maybe_generate_etl_event(self):
        """Generate ETL job events (less frequent — every ~30 ticks)."""
        if "etl" not in self.enabled:
            return

        self._etl_tick_counter += 1
        if self._etl_tick_counter >= 30:
            self._etl_tick_counter = 0
            start, complete = self.etl_gen.generate_job_pair()
            self._emit_generic(start, "ETL")
            self._emit_generic(complete, "ETL")

    def _emit_siem(self, event):
        """Format and write a SIEM event."""
        formatted = self.siem_gen.format_output(event, self.environment)
        self._emit_raw(formatted)

    def _emit_clinical(self, event):
        """Format and write a clinical event."""
        formatted = self.clinical_gen.format_output(event, self.environment)
        self._emit_raw(formatted)

    def _emit_hl7(self, event):
        """Write an HL7 event (already formatted)."""
        formatted = self.hl7_gen.format_output(event, self.environment)
        self._emit_raw(formatted)

    def _emit_generic(self, event, label=""):
        """Write a pre-formatted event."""
        self._emit_raw(event)

    def _emit_raw(self, formatted):
        """Write a formatted event to output."""
        if self.output:
            self.output.write(formatted)
        else:
            print(formatted)

    def run(self, frequency=10.0, duration=None, dry_run=False):
        """Main simulation loop.

        Args:
            frequency: seconds between ticks.
            duration: total seconds to run (None for infinite).
            dry_run: if True, output to stdout regardless of configured output.
        """
        if dry_run:
            self.output = None

        start_time = time.time()
        tick = 0

        try:
            while True:
                if duration and (time.time() - start_time) >= duration:
                    break

                self._maybe_start_session()
                self._advance_sessions()
                self._maybe_generate_service_event()
                self._maybe_generate_fhir_event()
                self._maybe_generate_mychart_event()
                self._maybe_generate_etl_event()

                tick += 1
                time.sleep(frequency)

        except KeyboardInterrupt:
            print(f"\nSimulation stopped after {tick} ticks. "
                  f"Generated events for {len(self.active_sessions)} active sessions.")

        if self.output:
            self.output.close()


def load_legacy_config(filename):
    """Load and validate a legacy config.json file."""
    if not os.path.exists(filename):
        print(f"Error: Config file '{filename}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(filename, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{filename}': {e}", file=sys.stderr)
        sys.exit(1)

    required_keys = ["E1Mid", "EMPid"]
    for key in required_keys:
        if key not in config:
            print(f"Error: Config missing required key '{key}'.", file=sys.stderr)
            sys.exit(1)

    return config


if __name__ == "__main__":
    config_dir = os.environ.get(
        "EPIC_CONFIG_DIR",
        os.path.join(os.path.dirname(__file__), "config"),
    )
    output_dir = os.environ.get("OUTPUT_DIR", "/app/output")
    frequency = float(os.environ.get("TICK_INTERVAL_EPIC", "10"))
    scenario = os.environ.get("EPIC_SCENARIO", None)

    output = FileOutput(output_dir=output_dir)

    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        config_path = "config.json"
    config = load_legacy_config(config_path) if os.path.exists(config_path) else {}

    orch = Orchestrator(
        config=config,
        config_dir=config_dir,
        output=output,
        scenario=scenario,
    )
    print(f"Epic SIEM Generator starting — frequency={frequency}s, output_dir={output_dir}")
    orch.run(frequency=frequency)
