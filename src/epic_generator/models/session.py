from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import random
import string
import uuid

from .user import User
from .patient import Patient


SESSION_STATES = ["LOGGED_IN", "IN_CHART", "IDLE", "LOGGED_OUT"]

# State machine transitions with probabilities
# From state -> list of (next_state, probability)
STATE_TRANSITIONS = {
    "LOGGED_IN": [
        ("IN_CHART", 0.60),
        ("IDLE", 0.25),
        ("LOGGED_OUT", 0.15),
    ],
    "IN_CHART": [
        ("IN_CHART", 0.45),     # Stay in chart (next action on same patient)
        ("LOGGED_IN", 0.25),    # Close chart, back to logged in
        ("IDLE", 0.10),
        ("LOGGED_OUT", 0.10),
        ("DISCHARGE", 0.10),    # Discharge patient (triggers ADT^A03)
    ],
    "IDLE": [
        ("IN_CHART", 0.50),
        ("LOGGED_IN", 0.30),
        ("LOGGED_OUT", 0.20),
    ],
    "DISCHARGE": [
        ("IN_CHART", 0.50),
        ("LOGGED_IN", 0.30),
        ("IDLE", 0.10),
        ("LOGGED_OUT", 0.10),
    ],
}


def generate_client_ip(cidr_prefix="10.6.3"):
    """Generate a random IP within the hospital network."""
    return f"{cidr_prefix}.{random.randint(1, 254)}"


def generate_client_name():
    """Generate a Hyperspace workstation name."""
    return f"VPEPCCHI{random.randint(1, 50)}"


@dataclass
class UserSession:
    session_id: str
    user: User
    login_time: datetime
    client_name: str
    client_ip: str
    events: list = field(default_factory=list)
    current_patient: Optional[Patient] = None
    state: str = "LOGGED_IN"
    event_count: int = 0

    @classmethod
    def create(cls, user: User):
        """Create a new session for a user."""
        return cls(
            session_id=str(uuid.uuid4()),
            user=user,
            login_time=datetime.now(),
            client_name=generate_client_name(),
            client_ip=generate_client_ip(),
        )

    def advance_state(self, patient_pool: list):
        """Advance session state machine. Returns the event type to generate."""
        if self.state == "LOGGED_OUT":
            return None

        transitions = STATE_TRANSITIONS.get(self.state, [])
        if not transitions:
            return None

        states, probs = zip(*transitions)
        next_state = random.choices(states, weights=probs, k=1)[0]

        event_type = self._determine_event_type(next_state, patient_pool)
        self.state = next_state
        self.event_count += 1
        return event_type

    def _determine_event_type(self, next_state, patient_pool):
        """Determine which SIEM event type to generate based on state transition."""
        if next_state == "DISCHARGE":
            # Discharge the current patient; DISCHARGE state has its own transitions
            self.current_patient = None
            return "discharge"

        if next_state == "LOGGED_OUT":
            self.current_patient = None
            return "LOGOUT"

        if self.state == "LOGGED_IN" and next_state == "IN_CHART":
            # Opening a chart — pick a patient
            self.current_patient = random.choice(patient_pool) if patient_pool else None
            return "PATIENT_LOOKUP"

        if next_state == "IN_CHART" and self.state == "IN_CHART":
            # Clinical action within chart — pick based on role weights
            return self._pick_clinical_action()

        if next_state == "IDLE":
            return "CONTEXTCHANGE"

        if next_state == "LOGGED_IN" and self.state == "IN_CHART":
            # Closing chart
            self.current_patient = None
            return "CHART_CLOSE"

        if next_state == "IN_CHART" and self.state == "IDLE":
            self.current_patient = random.choice(patient_pool) if patient_pool else None
            return "PATIENT_LOOKUP"

        return "CONTEXTCHANGE"

    def _pick_clinical_action(self):
        """Pick a clinical action based on user role weights."""
        weights = self.user.get_event_weights()
        # Filter to clinical actions only (exclude login)
        clinical = {k: v for k, v in weights.items() if k != "login"}
        if not clinical:
            return "CONTEXTCHANGE"
        actions, probs = zip(*clinical.items())
        return random.choices(actions, weights=probs, k=1)[0]

    @property
    def is_active(self):
        return self.state != "LOGGED_OUT"

    @property
    def is_service_session(self):
        return self.user.is_service_account
