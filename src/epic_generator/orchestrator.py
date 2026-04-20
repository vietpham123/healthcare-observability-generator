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
from mirth_metrics import MirthMetricsEmitter
from scheduler import Scheduler


MAX_CONCURRENT_SESSIONS = 20
BASE_NEW_SESSION_PROBABILITY = 0.3
SERVICE_EVENT_PROBABILITY = 0.2

# Clinical event types that should also produce correlated HL7 messages
HL7_CORRELATED_EVENTS = {"order_entry", "med_admin", "result_review", "discharge", "PATIENT_LOOKUP", "chart_review", "LOGIN"}
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

        # Anomaly injection state
        self._anomaly_config = self.scheduler.get_scenario_config().get("anomaly", {})
        self._anomaly_tick = 0
        self._anomaly_active = bool(self._anomaly_config)
        self._anomaly_phase_index = 0
        self._anomaly_seq_index = 0
        if self._anomaly_active:
            atype = self._anomaly_config.get("type", "unknown")
            dur = self._anomaly_config.get("duration_ticks", 0)
            phases = self._anomaly_config.get("phases", [])
            if phases:
                total = sum(p.get("duration_ticks", 0) for p in phases)
                print(f"[anomaly] ACTIVE: type={atype}, phases={len(phases)}, total_ticks={total}")
            else:
                print(f"[anomaly] ACTIVE: type={atype}, duration_ticks={dur}, events_per_tick={self._anomaly_config.get('events_per_tick', 0)}")

        # Apply generator_overrides from scenario config
        overrides = self.scheduler.get_scenario_config().get("generator_overrides", {})
        if overrides:
            if "fhir_error_bias" in overrides:
                self.fhir_gen.error_bias = overrides["fhir_error_bias"]
                self.fhir_json_gen.error_bias = overrides["fhir_error_bias"]
                print(f"[override] FHIR error_bias={overrides['fhir_error_bias']}")
            if "etl_failure_bias" in overrides:
                self.etl_gen.failure_bias = overrides["etl_failure_bias"]
                print(f"[override] ETL failure_bias={overrides['etl_failure_bias']}")
            if overrides.get("hl7_disabled"):
                self.enabled.discard("hl7")
                print("[override] HL7 generation disabled")

        # Mirth metrics emitter (None until __main__ wires it up)
        self._mirth_emitter = None
        self._mirth_scenario = overrides.get("mirth_scenario")

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
                    if self.scheduler.should_generate_hl7_event(base_probability=0.8):
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
        """Generate ETL job events with jitter and batch variation."""
        if "etl" not in self.enabled:
            return

        self._etl_tick_counter += 1
        # Jitter: fire between 15-45 ticks instead of fixed 30
        if not hasattr(self, '_etl_next_fire'):
            self._etl_next_fire = random.randint(15, 45)
        if self._etl_tick_counter >= self._etl_next_fire:
            self._etl_tick_counter = 0
            self._etl_next_fire = random.randint(15, 45)
            # Batch variation: 1-3 job pairs per fire, scaled by volume
            multiplier = self._get_volume_multiplier()
            batch_size = random.choices([1, 2, 3, 4], weights=[30, 40, 20, 10], k=1)[0]
            # Scale batch by volume multiplier (more jobs during peak hours)
            if multiplier > 0.7:
                batch_size = min(batch_size + 1, 5)
            for _ in range(batch_size):
                start, complete = self.etl_gen.generate_job_pair()
                self._emit_generic(start, "ETL")
                self._emit_generic(complete, "ETL")

    def _maybe_generate_standalone_hl7(self):
        """Generate standalone HL7 ADT messages (admits, transfers, discharges).

        These are independent of clinical session state and add variety to
        the HL7 message type distribution (ADT^A01, ADT^A02, ADT^A03).
        """
        if "hl7" not in self.enabled:
            return

        if self.scheduler.should_generate_standalone_hl7():
            session = random.choice(self.active_sessions) if self.active_sessions else None
            hl7_event = self.hl7_gen.generate_standalone(session=session, config=self.config)
            self._emit_hl7(hl7_event)

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


    def _inject_anomaly_events(self):
        """Inject scenario-specific anomaly events if an anomaly is configured."""
        if not self._anomaly_active:
            return

        anom = self._anomaly_config
        atype = anom.get("type", "")
        phases = anom.get("phases", [])

        # Phase-based anomaly (ransomware)
        if phases:
            tick_in_scenario = self._anomaly_tick
            cumulative = 0
            current_phase = None
            for i, phase in enumerate(phases):
                phase_dur = phase.get("duration_ticks", 10)
                if tick_in_scenario < cumulative + phase_dur:
                    current_phase = phase
                    self._anomaly_phase_index = i
                    break
                cumulative += phase_dur
            if current_phase is None:
                # All phases completed — restart for continuous demo
                self._anomaly_tick = 0
                self._anomaly_phase_index = 0
                print(f"[anomaly] Restarting {atype} cycle")
                return

            phase_name = current_phase.get("name", f"phase-{self._anomaly_phase_index}")
            event_types = current_phase.get("event_types", ["FAILEDLOGIN"])
            events_per_tick = anom.get("events_per_tick", 10)

            if self._anomaly_tick % 60 == 0:
                print(f"[anomaly] Phase: {phase_name}, tick={self._anomaly_tick}, events/tick={events_per_tick}")

            for _ in range(events_per_tick):
                etype = random.choice(event_types)
                self._emit_anomaly_event(etype, anom)

        else:
            # Simple anomaly (brute_force, hipaa_audit, insider_threat, privacy_breach)
            duration = anom.get("duration_ticks", 60)
            if self._anomaly_tick >= duration:
                # Restart anomaly for continuous demo
                self._anomaly_tick = 0
                self._anomaly_seq_index = 0
                print(f"[anomaly] Restarting {atype} cycle")
                return

            events_per_tick = anom.get("events_per_tick", 5)
            event_types = anom.get("event_types", [])
            event_sequence = anom.get("event_sequence", [])

            if self._anomaly_tick % 60 == 0:
                print(f"[anomaly] {atype}: tick={self._anomaly_tick}/{duration}, events/tick={events_per_tick}")

            for _ in range(events_per_tick):
                if event_sequence:
                    # Use ordered sequence (insider_threat, privacy_breach)
                    etype = event_sequence[self._anomaly_seq_index % len(event_sequence)]
                    self._anomaly_seq_index += 1
                elif event_types:
                    etype = random.choice(event_types)
                else:
                    etype = "FAILEDLOGIN"
                self._emit_anomaly_event(etype, anom)

        self._anomaly_tick += 1

    def _emit_anomaly_event(self, event_type, anom):
        """Generate and emit a single anomaly event."""
        if "siem" not in self.enabled:
            return

        # Use perpetrator or target usernames
        perp = anom.get("perpetrator_username")
        target_users = anom.get("target_usernames", [])
        if perp:
            matching = [u for u in self.users if u.username == perp]
            if matching:
                user = matching[0]
            else:
                user = random.choice(self.human_users) if self.human_users else None
        elif target_users:
            username = random.choice(target_users)
            matching = [u for u in self.users if u.username == username]
            user = matching[0] if matching else (random.choice(self.human_users) if self.human_users else None)
        else:
            user = random.choice(self.human_users) if self.human_users else None

        if user:
            session = UserSession.create(user)
            session.state = "LOGGED_IN"
            # Assign a patient for chart access events
            if self.patients:
                session.current_patient = random.choice(self.patients)
            # Override source IP if attacker range specified
            attacker_range = anom.get("attacker_ip_range", "")
            if attacker_range and "." in attacker_range:
                base = attacker_range.rsplit(".", 1)[0]
                session.source_ip = f"{base}.{random.randint(1, 254)}"
        else:
            session = None

        try:
            siem_event = self.siem_gen.generate_event(
                session=session, config=self.config, event_type=event_type
            )
            self._emit_siem(siem_event)
        except Exception as e:
            # Fallback: use a known working type
            try:
                siem_event = self.siem_gen.generate_event(
                    session=session, config=self.config, event_type="FAILEDLOGIN"
                )
                self._emit_siem(siem_event)
            except Exception:
                pass

    def _maybe_generate_login_events(self):
        """Generate standalone login success/failure events per tick."""
        if "siem" not in self.enabled:
            return
        login_count = random.randint(1, 3)
        for _ in range(login_count):
            if random.random() < 0.85:
                event_type = "LOGIN"
            else:
                event_type = random.choice(["FAILEDLOGIN", "FAILEDLOGIN",
                                           "WPSEC_LOGIN_FAIL", "LOGIN_BLOCKED"])
            session = random.choice(self.active_sessions) if self.active_sessions else None
            siem_xml = self.siem_gen.generate_event(
                session=session, config=self.config, event_type=event_type)
            self._emit_siem(siem_xml)

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
                self._maybe_generate_standalone_hl7()
                self._maybe_generate_login_events()
                self._inject_anomaly_events()

                # Mirth metrics (every tick)
                if self._mirth_emitter:
                    self._mirth_emitter.tick(scenario=self._mirth_scenario)

                tick += 1
                if tick % 30 == 0:  # Log every 30 ticks
                    print(f"[tick {tick}] sessions={len(self.active_sessions)}")
                # Flush DT output buffer after each tick
                if hasattr(self.output, 'flush'):
                    try:
                        self.output.flush()
                    except Exception as e:
                        print(f"[tick {tick}] flush error: {e}")
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


class MultiOutput:
    """Fan-out wrapper that writes to multiple output backends."""
    def __init__(self, outputs):
        self.outputs = outputs
    def write(self, data):
        for o in self.outputs:
            o.write(data)
    def flush(self):
        for o in self.outputs:
            if hasattr(o, "flush"):
                o.flush()
    def close(self):
        for o in self.outputs:
            if hasattr(o, "flush"):
                o.flush()
            o.close()


if __name__ == "__main__":
    config_dir = os.environ.get(
        "EPIC_CONFIG_DIR",
        os.path.join(os.path.dirname(__file__), "config"),
    )
    output_dir = os.environ.get("OUTPUT_DIR", "/app/output")
    frequency = float(os.environ.get("TICK_INTERVAL_EPIC", "10"))
    scenario = os.environ.get("EPIC_SCENARIO", None)
    output_mode = os.environ.get("EPIC_OUTPUT_MODE", "file").lower()

    os.makedirs(output_dir, exist_ok=True)
    outputs = []

    if output_mode in ("file", "both"):
        output_file = os.path.join(output_dir, "epic-siem.log")
        outputs.append(FileOutput(filename=output_file))

    if output_mode in ("dynatrace", "both"):
        from outputs.otlp_output import OTLPOutput
        dt_endpoint = os.environ.get("DT_ENDPOINT", "").rstrip("/")
        dt_token = os.environ.get("DT_API_TOKEN", "")
        if dt_endpoint and dt_token:
            dt_output = OTLPOutput(
                endpoint=f"{dt_endpoint}/api/v2/logs/ingest",
                api_token=dt_token,
                mode="dynatrace",
                batch_size=5,
                default_attributes={
                    "dt.source.generator": "healthcare-obs-gen-v2",
                    "generator.type": "epic-siem",
                    "generator.version": "2.0.0",
                },
            )
            outputs.append(dt_output)
            print(f"Dynatrace output enabled: {dt_endpoint}/api/v2/logs/ingest")
        else:
            print("WARNING: DT_ENDPOINT or DT_API_TOKEN not set, skipping Dynatrace output")

    if not outputs:
        output_file = os.path.join(output_dir, "epic-siem.log")
        outputs.append(FileOutput(filename=output_file))

    output = outputs[0] if len(outputs) == 1 else MultiOutput(outputs)

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

    # Wire up Mirth metrics emitter if DT credentials available
    dt_endpoint = os.environ.get("DT_ENDPOINT", "").rstrip("/")
    dt_token = os.environ.get("DT_API_TOKEN", "")
    if dt_endpoint and dt_token:
        orch._mirth_emitter = MirthMetricsEmitter(dt_endpoint, dt_token)
        print(f"Mirth metrics emitter enabled: {dt_endpoint}/api/v2/metrics/ingest")
    else:
        print("Mirth metrics emitter disabled (no DT credentials)")

    print(f"Epic SIEM Generator starting - mode={output_mode}, frequency={frequency}s")
    orch.run(frequency=frequency)
