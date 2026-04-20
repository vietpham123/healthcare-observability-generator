# Healthcare Observability Generator — Architecture & Implementation Guide

## Project Goal

Build a comprehensive Epic EHR + hospital network log simulator that generates realistic, correlated telemetry for healthcare IT observability. The simulator produces output suitable for ingestion by Dynatrace, SIEM tools, and HL7/FHIR integration testing.

---

## Implementation Phases

### Phase 1 — Foundation (April 14, 2026)

**Objective:** Consolidate codebase, build data models, introduce correlated sessions.

- Merged diverging codebases (`15APRlog_gen` + `log_generator.py`) into unified structure
- Created `models/patient.py`, `models/user.py`, `models/session.py` data models
- Refactored generators into `generators/base.py` + `generators/siem.py`
- Created `outputs/file_output.py` with file locking
- Built `orchestrator.py` — session state machine with correlated event chains

### Phase 2 — Expanded Log Types (April 15–16, 2026)

**Objective:** Add clinical, HL7, FHIR, MyChart, and ETL generators.

| Generator | Output | Correlation |
|-----------|--------|-------------|
| `generators/clinical.py` | Clinical workflow EventLog XML | Tied to UserSession state |
| `generators/hl7.py` | HL7v2 ADT/ORM/ORU messages | ORDER_ENTRY → ORM^O01 |
| `generators/fhir.py` | FHIR R4 Interconnect API logs | Linked via correlation ID |
| `generators/mychart.py` | MyChart portal EventLog XML | Distinct INSTANCEURN |
| `generators/etl.py` | Caboodle/Clarity ETL job logs | Scheduled job simulation |

### Phase 3 — Infrastructure & Outputs (April 16–17, 2026)

**Objective:** Add transport outputs and multi-instance simulation.

- `outputs/otlp_output.py` — Dynatrace Log Ingest API v2 with batch buffering
- `outputs/syslog_output.py` — RFC 5424 TCP/UDP
- `outputs/mllp_output.py` — HL7 MLLP transport
- `outputs/api_output.py` — Generic REST webhook
- `scheduler.py` — Time-of-day volume curves (shift patterns, lunch dips, overnight lull)
- `config/environments.json` — Multi-environment support (PRD, TST, BLD, SUP)

### Phase 4 — Advanced Features (April 17–18, 2026)

**Objective:** FHIR resources, ETL simulation, compliance scenarios, DT integration.

- FHIR R4 JSON resource generation (Patient, Encounter, Observation, MedicationRequest)
- Pre-built compliance/anomaly scenarios (HIPAA audit, ransomware, insider threat, brute force)
- Network generator with 12 vendor emulators, SNMP agent, NetFlow, scenario engine
- Dynatrace-native output via OTLPOutput with `dt.source.generator` attributes
- Kubernetes microservices deployment with Kustomize overlays

### Phase 5 — Fidelity Gap Repair (April 18–19, 2026)

**Objective:** Close the gap between generated SIEM logs and real Epic SIEM output.

#### Gap Analysis Results

A field-by-field fidelity analysis was conducted comparing generated logs to real Epic SIEM output across 13 categories. Overall fidelity score: **~41%**.

| Category | Gap | Resolution |
|----------|-----|------------|
| E1Mid | Missing `BCA_LOGIN_SUCCESS` | Added to generator + config |
| Login Mnemonics | No CLIENT_TYPE, LOGINERROR, LOGIN_CONTEXT, etc. | Added `_build_login_mnemonics()` (15 fields) |
| Service Mnemonics | No SERVICETYPE, HOSTNAME, INSTANCEURN, etc. | Added `_build_service_mnemonics()` (13 fields) |
| Syslog Header | Wrong PID, wrong timestamp precision | Fixed to realistic PIDs, microsecond precision |
| Date/Time Format | Wrong format in XML body | Fixed to M/D/YYYY and 12-hour with leading space |
| Flag Field | Incorrect values | Fixed to `"^^Workflow Logging"` / `"Access History^^"` |
| Source Field | Missing SUP source | Weighted `["prd","prd","prd","prd","SUP"]` |
| Workstation IDs | Not realistic | 24 sanitized hospital workstation IDs |
| Service Names | Generic | 35 sanitized Epic service URNs |
| Config Data | Could trace to examples | Full sanitization of all identifiers |

#### Generator Patches (v1.0.3)

**`generators/siem.py`:**
- Added `_build_login_mnemonics()` — 15 login-specific mnemonic fields
- Added `_build_service_mnemonics()` — 13 service-audit mnemonic fields
- Module-level constants: `LOGIN_MNEMONICS`, `WORKSTATION_IDS` (24), `LOGIN_ERRORS` (5), `LOGIN_CONTEXTS` (5), `CLIENT_TYPES` (4), `LOGIN_SOURCE_TYPES` (4), `HYP_ACCESS_IDS` (3)
- Fixed syslog PID, timestamp precision, date/time format, Flag, Source

**`config.json`:**
- 17 E1Mid entries including BCA_LOGIN_SUCCESS
- 16 sanitized EMPid entries, 24 workstation IDs
- 9 service categories, 3 service types, 35 service URNs, 8 instance URNs

**`orchestrator.py`:**
- Added `_maybe_generate_login_events()` — 1-3 login events/tick (85% success, 15% failure)
- Added LOGIN to HL7_CORRELATED_EVENTS

#### OpenPipeline Update

Updated the Epic SIEM XML processor to extract 16 new fields from SIEM XML mnemonics:
- Service audit: SERVICETYPE, HOSTNAME, INSTANCEURN, SERVICE_USER, SERVICE_USERTYP
- Login auth: CLIENT_TYPE, LOGINERROR, LOGIN_CONTEXT, LOGIN_LDAP_ID, INTERNET_AREA, HYP_ACCESS_ID, REMOTE_IP, UID, LOGIN_SOURCE
- Syslog: SYSLOG_PID

#### DT App v1.8.0

- **New page: Auth Health** — KPIs (success rate, failed logins, active workstations, LDAP users), login trends, error breakdown, client type/login context/login source, workstation table
- **Enhanced: Epic Health** — Interconnect Service Audit section, Workstation Activity section
- **Enhanced: Security** — Login Failure Analysis section (error types, workstation failures, login context)
- **19 new DQL queries** covering auth health, service audit, workstation analytics

---

## Deployment Architectures

### Monolithic (Single Process)

Runs all generators in one process via the Orchestrator class.

```bash
python orchestrator.py
```

### Kubernetes (AKS) — Current Production

```
AKS Cluster (<your-aks-cluster>, 2× Standard_B2ms)
  namespace: healthcare-gen
  ├── epic-generator (v1.0.3)      → DT Log Ingest API
  ├── network-generator (latest)    → DT Log/Metrics/Events API
  └── webui (v1.0.5)               → Scenario control
  namespace: dynatrace
  └── DT Operator + ActiveGate     → K8s monitoring
```

#### Configuration (ConfigMap)

| Variable | Value | Description |
|----------|-------|-------------|
| `DT_ENDPOINT` | `https://<your-env-id>.live.dynatrace.com` | DT environment |
| `EPIC_OUTPUT_MODE` | `both` | File + Dynatrace |
| `TICK_INTERVAL_EPIC` | `5` | 5-second tick |
| `EPIC_SCENARIO` | `normal_shift` | Default scenario |

### Microservices (Redis Streams) — Designed, Not Deployed

Decomposes monolith into independently scalable pods via Redis Streams consumer groups:
- Orchestrator → Redis `epic.sessions` → SIEM/Clinical/HL7/FHIR/MyChart/ETL workers
- Each worker scales horizontally
- See `services/` directory for entrypoints

---

## OpenPipeline Configuration

**Pipeline:** `Healthcare Observability`

### SIEM XML Processor — Extracted Fields

| Category | Fields |
|----------|--------|
| Core | `E1Mid`, `Action`, `Source`, `WorkstationID`, `Flag` |
| Employee | `EMPID` (numeric), `EMPid` (name), `USERNAME` |
| Network | `IP`, `CLIENTNAME`, `REMOTE_IP` |
| Service Audit | `SERVICENAME`, `SERVICECATEGORY`, `SERVICETYPE`, `HOSTNAME`, `INSTANCEURN`, `SERVICE_USER`, `SERVICE_USERTYP` |
| Login Auth | `CLIENT_TYPE`, `LOGINERROR`, `LOGIN_CONTEXT`, `LOGIN_LDAP_ID`, `INTERNET_AREA`, `HYP_ACCESS_ID`, `UID`, `LOGIN_SOURCE` |
| Clinical | `DEPARTMENT`, `ORDER_TYPE`, `NOTE_TYPE`, `MEDICATION_NAME`, `PATIENT_MRN` |
| Portal | `device_type` (PLATFORM), `SESSION_ID`, `patient_portal_action` |
| Syslog | `SYSLOG_PID` |
| Derived | `healthcare.site` (from IP octet), `epic.log_type` |

---

## Build & Deploy Reference

### Docker Build (on VM)
```bash
cd ~/healthcare-observability-generator
docker build -t <your-acr>.azurecr.io/healthcare-gen/epic:v1.0.3 \
  -t <your-acr>.azurecr.io/healthcare-gen/epic:latest \
  -f deploy/docker/Dockerfile.epic .
docker push <your-acr>.azurecr.io/healthcare-gen/epic:v1.0.3
```

### DT App Deploy (from local machine)
```bash
cd /tmp/healthcare-app && npx dt-app deploy
```

### Rsync App to VM
```bash
rsync -avz --exclude node_modules --exclude dist --exclude .dt-app \
  /tmp/healthcare-app/ \
  <user>@<your-vm-ip>:~/healthcare-observability-generator/dynatrace-apps/healthcare-health-monitoring/ \
  -e "ssh -i ~/.ssh/<your-key>.pem"
```

### OpenPipeline Update (Settings API v2)
```bash
# GET current config
curl -s -H "Authorization: Api-Token $OPERATOR_TOKEN" \
  "$DT_ENV/api/v2/settings/objects?schemaIds=builtin:openpipeline.logs.pipelines"

# POST updated config (upsert — NOT PUT)
curl -X POST -H "Authorization: Api-Token $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  "$DT_ENV/api/v2/settings/objects" \
  -d '[{"schemaId":"builtin:openpipeline.logs.pipelines","objectId":"<id>","value":{...}}]'
```


## Mirth Connect Metrics Emitter (v2.3.0)

The epic-generator now includes a Mirth Connect integration engine metrics emitter
(`mirth_metrics.py`) that sends synthetic channel metrics directly to the Dynatrace
Metrics API v2 (MINT line protocol).

### Channels
- LAB-RESULTS-IN (HL7v2 inbound)
- ADT-OUT (HL7v2 outbound)
- PHARMACY-ORDERS (HL7v2 bidirectional)
- RADIOLOGY-RESULTS (HL7v2 inbound)
- SCHEDULING-OUT (FHIR outbound)

### Metrics (per channel)
- `healthcare.mirth.channel.messages.received` (count, delta)
- `healthcare.mirth.channel.messages.sent` (count, delta)
- `healthcare.mirth.channel.messages.errors` (count, delta)
- `healthcare.mirth.channel.messages.filtered` (count, delta)
- `healthcare.mirth.channel.queue.depth` (gauge)
- `healthcare.mirth.channel.status` (gauge: 1=running, 0=stopped)

### Scenario Integration
The emitter responds to `generator_overrides.mirth_scenario` in scenario configs:
- `hl7_interface_failure`: Escalating degradation (queue depth 0→5000, channels stop)
- `core_switch_failure`: Mild degradation (30% error increase)
- Any other / None: Normal baseline metrics
