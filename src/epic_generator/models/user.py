from dataclasses import dataclass
import json
import random


ROLE_EVENT_WEIGHTS = {
    "PHYSICIAN": {
        "chart_review": 0.30,
        "order_entry": 0.25,
        "note_sign": 0.20,
        "login": 0.10,
        "result_review": 0.15,
    },
    "NURSE": {
        "chart_review": 0.20,
        "med_admin": 0.30,
        "flowsheet": 0.25,
        "login": 0.10,
        "order_entry": 0.15,
    },
    "ADMIN": {
        "login": 0.30,
        "report_access": 0.30,
        "user_mgmt": 0.20,
        "patient_lookup": 0.20,
    },
    "PHARMACIST": {
        "order_verify": 0.35,
        "chart_review": 0.25,
        "med_admin": 0.20,
        "login": 0.10,
        "result_review": 0.10,
    },
    "TECH": {
        "chart_review": 0.20,
        "flowsheet": 0.35,
        "login": 0.15,
        "result_review": 0.15,
        "patient_lookup": 0.15,
    },
    "SYSTEM": {
        "api_call": 0.80,
        "login": 0.10,
        "service_audit": 0.10,
    },
}

ROLE_TO_SERVICE_USER = {
    "PHYSICIAN": ["PHYSICIAN", "RESIDENT", "ICU PHYSICIAN", "OR SURGEON"],
    "NURSE": ["OR NURSE", "ICU NURSE", "ONCBCN INFUSION NURSE"],
    "ADMIN": ["Admin"],
    "PHARMACIST": ["PHARMACIST"],
    "TECH": ["RIS IPTECH"],
    "SYSTEM": [],
}

ROLE_TO_USER_TYPE = {
    "PHYSICIAN": "Physician",
    "NURSE": "Nurse",
    "ADMIN": "Admin",
    "PHARMACIST": "Physician",
    "TECH": "Nurse",
    "SYSTEM": "System",
}


@dataclass
class User:
    emp_id: str
    username: str
    role: str
    department: str
    user_type: str
    is_service_account: bool = False

    @property
    def display_name(self):
        """Extract display name from emp_id format '1001^PHAM, VIET^VPHAM'."""
        parts = self.emp_id.split("^")
        return parts[1] if len(parts) > 1 else self.emp_id

    @property
    def numeric_id(self):
        """Extract numeric ID from emp_id."""
        return self.emp_id.split("^")[0]

    def get_service_user(self):
        """Return a random SERVICE_USER value appropriate for this role."""
        options = ROLE_TO_SERVICE_USER.get(self.role, [])
        if not options or self.is_service_account:
            return ""
        return random.choice(options)

    def get_event_weights(self):
        """Return event probability weights for this user's role."""
        return ROLE_EVENT_WEIGHTS.get(self.role, ROLE_EVENT_WEIGHTS["ADMIN"])

    def to_dict(self):
        return {
            "emp_id": self.emp_id,
            "username": self.username,
            "role": self.role,
            "department": self.department,
            "user_type": self.user_type,
            "is_service_account": self.is_service_account,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            emp_id=data["emp_id"],
            username=data["username"],
            role=data["role"],
            department=data["department"],
            user_type=data["user_type"],
            is_service_account=data.get("is_service_account", False),
        )


def load_users(config_path):
    """Load users from a JSON file."""
    with open(config_path, "r") as f:
        data = json.load(f)
    return [User.from_dict(u) for u in data]


def save_users(users, config_path):
    """Save user pool to JSON file."""
    data = [u.to_dict() for u in users]
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
