import json
import os
import random
from datetime import datetime


# Default shift-based volume curve: hour -> multiplier (0.0 - 1.0)
DEFAULT_SHIFT_CURVE = {
    0: 0.10, 1: 0.10, 2: 0.10, 3: 0.10, 4: 0.10, 5: 0.10,
    6: 0.50,
    7: 1.00, 8: 1.00,
    9: 0.80, 10: 0.80, 11: 0.80,
    12: 0.60,
    13: 0.80, 14: 0.80,
    15: 1.00,
    16: 0.60, 17: 0.60, 18: 0.60,
    19: 0.30, 20: 0.30, 21: 0.30, 22: 0.30,
    23: 0.15,
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
        """Load scenario overrides from a JSON file."""
        # Try .json first, then .yaml stub
        json_path = os.path.join(scenario_dir, f"{scenario_name}.json")
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

    def should_generate_mychart_event(self, base_probability=0.15):
        """Decide if a MyChart portal event should fire this tick.

        MyChart traffic peaks in evening hours (patients checking results
        after work) and has a different curve than clinical traffic.
        """
        hour = datetime.now().hour
        mychart_curve = {
            0: 0.05, 1: 0.03, 2: 0.02, 3: 0.02, 4: 0.02, 5: 0.05,
            6: 0.15, 7: 0.20, 8: 0.25,
            9: 0.30, 10: 0.30, 11: 0.30,
            12: 0.40, 13: 0.35, 14: 0.30,
            15: 0.30, 16: 0.40, 17: 0.50,
            18: 0.70, 19: 0.80, 20: 1.00,  # Peak — patients home from work
            21: 0.80, 22: 0.50,
            23: 0.20,
        }
        mult = mychart_curve.get(hour, 0.3)
        scenario_mult = self.scenario_config.get("mychart_multiplier", 1.0)
        return random.random() < (base_probability * mult * scenario_mult)

    def should_generate_fhir_event(self, base_probability=0.25):
        """Decide if a FHIR/Interconnect API event should fire this tick."""
        multiplier = self.get_volume_multiplier()
        return random.random() < (base_probability * multiplier)

    def should_generate_hl7_event(self, base_probability=0.10):
        """Decide if an HL7 message should be generated this tick.

        HL7 messages correlate with clinical actions (admits, orders,
        results) so they follow the clinical curve.
        """
        multiplier = self.get_volume_multiplier()
        return random.random() < (base_probability * multiplier)

    def get_scenario_config(self):
        """Return the full scenario configuration dict."""
        return self.scenario_config
