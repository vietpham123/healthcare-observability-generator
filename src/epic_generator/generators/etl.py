import datetime
import json
import random
import uuid

from .base import BaseGenerator


ETL_JOB_TYPES = [
    {"name": "PatientDim", "table": "PatientDim", "type": "Incremental", "avg_rows": 500, "avg_duration_sec": 120},
    {"name": "EncounterFact", "table": "EncounterFact", "type": "Incremental", "avg_rows": 2000, "avg_duration_sec": 300},
    {"name": "OrderFact", "table": "OrderFact", "type": "Incremental", "avg_rows": 5000, "avg_duration_sec": 450},
    {"name": "LabResultFact", "table": "LabResultFact", "type": "Incremental", "avg_rows": 8000, "avg_duration_sec": 600},
    {"name": "MedicationAdminFact", "table": "MedicationAdminFact", "type": "Incremental", "avg_rows": 3000, "avg_duration_sec": 240},
    {"name": "ClinicalNoteFact", "table": "ClinicalNoteFact", "type": "Incremental", "avg_rows": 1500, "avg_duration_sec": 180},
    {"name": "DiagnosisDim", "table": "DiagnosisDim", "type": "Full", "avg_rows": 50000, "avg_duration_sec": 900},
    {"name": "ProviderDim", "table": "ProviderDim", "type": "Full", "avg_rows": 2000, "avg_duration_sec": 60},
    {"name": "DepartmentDim", "table": "DepartmentDim", "type": "Full", "avg_rows": 200, "avg_duration_sec": 15},
    {"name": "FlowsheetFact", "table": "FlowsheetFact", "type": "Incremental", "avg_rows": 12000, "avg_duration_sec": 720},
    {"name": "BillingFact", "table": "BillingFact", "type": "Incremental", "avg_rows": 4000, "avg_duration_sec": 360},
    {"name": "AppointmentFact", "table": "AppointmentFact", "type": "Incremental", "avg_rows": 1000, "avg_duration_sec": 90},
]

ETL_STATUSES = [
    ("SUCCESS", 90),
    ("SUCCESS_WITH_WARNINGS", 5),
    ("FAILED", 3),
    ("TIMEOUT", 2),
]

DATA_SOURCES = ["Clarity", "Caboodle"]


class ETLGenerator(BaseGenerator):
    """Simulates Epic Caboodle/Clarity data warehouse ETL job logs."""

    def __init__(self, data_source="Caboodle"):
        self.data_source = data_source
        self.failure_bias = 0.0  # 0.0 = normal distribution, >0 = force failures

    def generate_event(self, session=None, config=None, event_type=None):
        """Generate an ETL job log entry as a JSON string.

        Args:
            session: unused — ETL jobs are system-level events.
            config: unused.
            event_type: "start" or "complete". If None, generates a complete pair.

        Returns:
            str: JSON string of the ETL log event.
        """
        job = random.choice(ETL_JOB_TYPES)
        job_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now()

        if event_type == "start":
            return self._build_start_event(job, job_id, now)
        elif event_type == "complete":
            return self._build_complete_event(job, job_id, now)
        else:
            # Generate both start and complete as a combined log
            return self._build_complete_event(job, job_id, now)

    def generate_job_pair(self):
        """Generate a matched start/complete ETL job event pair.

        Returns:
            tuple: (start_json, complete_json) strings.
        """
        job = random.choice(ETL_JOB_TYPES)
        job_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now()

        start = self._build_start_event(job, job_id, now)

        # Duration with realistic variance
        base_dur = job["avg_duration_sec"]
        actual_dur = max(1, int(random.gauss(base_dur, base_dur * 0.3)))
        end_time = now + datetime.timedelta(seconds=actual_dur)

        complete = self._build_complete_event(job, job_id, end_time, actual_dur)
        return (start, complete)

    def format_output(self, event, environment=None):
        return event

    def _build_start_event(self, job, job_id, timestamp):
        entry = {
            "timestamp": timestamp.isoformat(),
            "level": "INFO",
            "service": f"Epic-{self.data_source}-ETL",
            "event": "ETL_JOB_START",
            "job_id": f"{self.data_source}-{job_id}",
            "job_name": job["name"],
            "target_table": f"{self.data_source}.dbo.{job['table']}",
            "extract_type": job["type"],
            "data_source": self.data_source,
            "instance": f"ETL-{self.data_source.upper()}-01",
            "status": "RUNNING",
            "job_status": "RUNNING",
        }
        return json.dumps(entry)

    def _build_complete_event(self, job, job_id, timestamp, duration_sec=None):
        if duration_sec is None:
            base_dur = job["avg_duration_sec"]
            duration_sec = max(1, int(random.gauss(base_dur, base_dur * 0.3)))

        # Row count with variance
        base_rows = job["avg_rows"]
        actual_rows = max(0, int(random.gauss(base_rows, base_rows * 0.2)))

        # Status — failure_bias overrides normal distribution during scenarios
        if self.failure_bias > 0 and random.random() < self.failure_bias:
            status = random.choice(["FAILED", "TIMEOUT"])
        else:
            statuses, weights = zip(*ETL_STATUSES)
            status = random.choices(statuses, weights=weights, k=1)[0]

        # Error details for failures
        error_msg = None
        if status == "FAILED":
            error_msg = random.choice([
                "Deadlock detected on target table",
                "Source query timeout after 3600s",
                "Foreign key constraint violation",
                "Insufficient disk space on tempdb",
                "Connection lost to source database",
            ])
        elif status == "TIMEOUT":
            error_msg = f"Job exceeded maximum runtime of {job['avg_duration_sec'] * 3}s"
            duration_sec = job["avg_duration_sec"] * 3

        entry = {
            "timestamp": timestamp.isoformat(),
            "level": "ERROR" if status in ("FAILED", "TIMEOUT") else "INFO",
            "service": f"Epic-{self.data_source}-ETL",
            "event": "ETL_JOB_COMPLETE",
            "job_id": f"{self.data_source}-{job_id}",
            "job_name": job["name"],
            "target_table": f"{self.data_source}.dbo.{job['table']}",
            "extract_type": job["type"],
            "data_source": self.data_source,
            "instance": f"ETL-{self.data_source.upper()}-01",
            "status": status,
            "job_status": status,
            "rows_processed": actual_rows,
            "rows_inserted": actual_rows if status.startswith("SUCCESS") else 0,
            "rows_updated": int(actual_rows * 0.1) if status.startswith("SUCCESS") else 0,
            "duration_seconds": duration_sec,
            "duration_formatted": str(datetime.timedelta(seconds=duration_sec)),
        }

        if error_msg:
            entry["error_message"] = error_msg

        if status == "SUCCESS_WITH_WARNINGS":
            entry["warnings"] = [random.choice([
                f"Skipped {random.randint(1, 10)} rows with null key values",
                "Index rebuild recommended on target table",
                "Source query returned duplicate CSNs — deduplication applied",
            ])]

        return json.dumps(entry)

    def generate_sample(self, n=10, config=None):
        for _ in range(n):
            start, complete = self.generate_job_pair()
            print(start)
            print(complete)
            print()
