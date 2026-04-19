import json
import os
import random
from datetime import datetime


# Default shift-based volume curve: hour -> multiplier (0.0 - 1.0)
DEFAULT_SHIFT_CURVE = {
    0: 0.30, 1: 0.30, 2: 0.30, 3: 0.30, 4: 0.30, 5: 0.35,
    6: 0.60,
    7: 1.00, 8: 1.00,
    9: 0.85, 10: 0.85, 11: 0.85,
    12: 0.70,
    13: 0.85, 14: 0.85,
    15: 1.00,
    16: 0.70, 17: 0.70, 18: 0.70,
    19: 0.50, 20: 0.50, 21: 0.50, 22: 0.45,
    23: 0.35,
}


class Scheduler:
    """Temporal pattern engine for controlling event volume based on time-of-day
    and scenario overrides.

    Provides methods to determine event rates and session start probabilities
    based on realistic hospital shift patterns.
    """

    def __init__(self, base_curve=None, scenario=None, scenario_dir=None):
        """
        Args:
            base_curve: dict mapping hour (0-23) to multiplier (0.0-1.0).
                        Defaults to DEFAULT_SHIFT_CURVE.
            scenario: str name of a scenario to load (e.g., "ed_surge").
            scenario_dir: path to directory containing scenario JSON files.
        """
        self.base_curve = base_curve or DEFAULT_SHIFT_CURVE.copy()
        self.scenario_overrides = {}
        self.scenario_config = {}

        if scenario and scenario_dir:
            self._load_scenario(scenario, scenario_dir)

    def _load_scenario(self, scenario_name, scenario_dir):
        """Load scenario overrides from a JSON file.

        Checks the given scenario_dir first, then falls back to the shared
        config/scenarios/ directory (used by the coordinator/WebUI).
        """
        json_path = os.path.join(scenario_dir, f"{scenario_name}.json")

        # Fallback: check the shared config/scenarios dir
        if not os.path.exists(json_path):
            shared_dir = os.environ.get(
                "SHARED_SCENARIO_DIR",
                "/app/config/scenarios",
            )
            alt_path = os.path.join(shared_dir, f"{scenario_name}.json")
            if os.path.exists(alt_path):
                json_path = alt_path

        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                self.scenario_config = json.load(f)
            self.scenario_overrides = self.scenario_config.get("curve_overrides", {})

    def get_volume_multiplier(self, hour=None):
        """Get the current event volume multiplier.

        Args:
            hour: Hour of day (0-23). Defaults to current hour.

        Returns:
            float: Volume multiplier between 0.0 and 2.0+
        """
        if hour is None:
            hour = datetime.now().hour

        base = self.base_curve.get(hour, 0.5)

        # Apply scenario overrides (stored as str keys in JSON)
        override = self.scenario_overrides.get(str(hour))
        if override is not None:
            return float(override)

        # Apply scenario multiplier if set
        scenario_mult = self.scenario_config.get("volume_multiplier", 1.0)
        return base * scenario_mult

    def get_events_per_minute(self, hour=None, base_rate=6.0):
        """Return expected event rate based on time of day and scenario.

        Args:
            hour: Hour of day (0-23). Defaults to current hour.
            base_rate: Base events per minute at multiplier 1.0.

        Returns:
            float: Expected events per minute.
        """
        return base_rate * self.get_volume_multiplier(hour)

    def should_start_session(self, max_sessions=20, current_sessions=0,
                             base_probability=0.3):
        """Probabilistic decision on whether to start a new user session.

        Args:
            max_sessions: Maximum concurrent sessions allowed.
            current_sessions: Current active session count.
            base_probability: Base probability at multiplier 1.0.

        Returns:
            bool: True if a new session should start.
        """
        if current_sessions >= max_sessions:
            return False

        multiplier = self.get_volume_multiplier()
        prob = base_probability * multiplier

        # Reduce probability as we approach max sessions
        capacity_ratio = 1.0 - (current_sessions / max_sessions)
        prob *= capacity_ratio

        return random.random() < prob

    def should_generate_mychart_event(self, base_probability=0.25):
        """Decide if a MyChart portal event should fire this tick.

        MyChart traffic peaks in evening hours (patients checking results
        after work) and has a different curve than clinical traffic.
        """
        hour = datetime.now().hour
        mychart_curve = {
            0: 0.25, 1: 0.25, 2: 0.20, 3: 0.20, 4: 0.20, 5: 0.25,
            6: 0.35, 7: 0.40, 8: 0.45,
            9: 0.50, 10: 0.50, 11: 0.50,
            12: 0.55, 13: 0.50, 14: 0.50,
            15: 0.50, 16: 0.60, 17: 0.70,
            18: 0.85, 19: 0.90, 20: 1.00,  # Peak — patients home from work
            21: 0.90, 22: 0.70,
            23: 0.40,
        }
        mult = mychart_curve.get(hour, 0.3)
        scenario_mult = self.scenario_config.get("mychart_multiplier", 1.0)
        return random.random() < (base_probability * mult * scenario_mult)

    def should_generate_fhir_event(self, base_probability=0.45):
        """Decide if a FHIR/Interconnect API event should fire this tick."""
        multiplier = self.get_volume_multiplier()
        return random.random() < (base_probability * multiplier)

    def should_generate_hl7_event(self, base_probability=0.35):
        """Decide if an HL7 message should be generated this tick.

        HL7 messages correlate with clinical actions (admits, orders,
        results) so they follow the clinical curve.
        """
        multiplier = self.get_volume_multiplier()
        return random.random() < (base_probability * multiplier)

    def should_generate_standalone_hl7(self, base_probability=0.20):
        """Decide if a standalone HL7 message (ADT admit/transfer/discharge) should fire.

        These are independent of clinical session events and produce ADT^A01,
        ADT^A02, ADT^A03 messages to add message type variety.
        """
        multiplier = self.get_volume_multiplier()
        return random.random() < (base_probability * multiplier)

    def get_scenario_config(self):
        """Return the full scenario configuration dict."""
        return self.scenario_config
