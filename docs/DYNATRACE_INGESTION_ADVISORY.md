# Dynatrace Ingestion Architecture Advisory

## Healthcare Observability Generator — Data Ingestion & Management Strategy

> **Purpose**: Step-by-step guidance for ingesting Epic SIEM + Network generator data into Dynatrace with proper segmentation, OpenPipeline configuration, Grail storage buckets, and querying best practices.

---

## 1. Data Source Inventory

### 1.1 Epic Generator — 6 Log Types

| Log Type | Format | Volume Estimate (10s tick) | Key Attributes |
|----------|--------|---------------------------|----------------|
| **SIEM Audit** | XML inside syslog wrapper | ~20-50 events/tick | `E1Mid`, `EMPid`, `Action`, `IP`, `Flag` |
| **Clinical Events** | XML (orders, meds, notes, results, discharge, flowsheets) | ~10-30 events/tick | `ORDER_TYPE`, `MEDICATION_NAME`, `NOTE_TYPE` |
| **HL7v2 Messages** | Pipe-delimited segments (ADT, ORM, ORU, MDM) | ~5-15 messages/tick | `MSH.9` (message type), `PID.3` (MRN), `PV1.2` (class) |
| **FHIR API Logs** | JSON access logs | ~10-40 entries/tick | `method`, `path`, `status`, `client_id`, `category` |
| **MyChart Activity** | JSON session/interaction logs | ~5-20 events/tick | `session_id`, `patient_portal_action`, `device_type` |
| **ETL/Integration** | JSON batch job logs | ~2-5 events/tick | `job_name`, `source_system`, `records_processed` |

### 1.2 Network Generator — 4 Data Types

| Data Type | Dynatrace API | Volume Estimate (60s tick) | Key Attributes |
|-----------|---------------|---------------------------|----------------|
| **Syslog Events** | Log Ingest v2 | ~40-80 events/tick (4 sites × 10-20 devices) | `network.device.*`, `event_type`, `log_source`, `vendor` |
| **Interface/Device Metrics** | Metrics Ingest v2 (MINT) | ~200-400 lines/tick | `if.traffic.in.bytes`, `device.cpu.utilization`, device/site dims |
| **SNMP Traps** | Events Ingest v2 | ~0-5 events/tick (scenario-dependent) | `trap_oid`, `trap_name`, `severity`, device info |
| **NetFlow Records** | Log Ingest v2 (as flow logs) | ~20-100 records/tick | `network.flow.*` (src/dst IP, port, protocol, bytes, geo) |

---

## 2. Segmentation Strategy — Isolating from Legacy Generators

### 2.1 The Problem

You have existing data from previous standalone versions:
- **Old Epic Log Generator** → likely ingested as generic `log.source: "epic-simulator"` logs
- **Old Network Log Generator** → likely ingested with `log.source: "netflow"`, `"syslog_cisco"`, etc.

The combined generator will produce data with the same `log.source` values, creating query ambiguity.

### 2.2 Solution: Multi-Layer Segmentation

**Layer 1 — Attribute Tagging (Source of Truth)**

Add a discriminator attribute to EVERY record at the generator level:

```
dt.source.generator = "healthcare-obs-gen-v2"
dt.source.generator.version = "2.0.0"
dt.source.deployment = "aks-healthcare-gen"
```

This requires a small code change in both output adapters. These attributes travel with the data through OpenPipeline and into Grail, enabling precise filtering.

**Layer 2 — Dedicated Grail Storage Bucket**

Create a separate bucket so old and new data don't share the same storage:

```
Bucket: healthcare_obs_gen
Retention: 35 days (default) or as needed
Table: logs
Table: events
```

Metrics go into the default metrics bucket (Grail doesn't support custom metric buckets yet), but dimension-based filtering handles segmentation.

**Layer 3 — OpenPipeline Routing**

Route data tagged with `dt.source.generator == "healthcare-obs-gen-v2"` into the dedicated bucket via OpenPipeline rules.

---

## 3. Grail Storage Bucket Configuration

### 3.1 Create the Bucket

**Via Settings UI**: Settings → Log Monitoring → Log storage → Custom buckets → Create bucket

**Via API** (recommended for reproducibility):

```bash
# POST to Grail Bucket Management API
curl -X POST "https://{env-id}.apps.dynatrace.com/platform/storage/management/v1/bucket-definitions" \
  -H "Authorization: Api-Token {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "bucketName": "healthcare_obs_gen",
    "table": "logs",
    "displayName": "Healthcare Observability Generator",
    "retentionDays": 35,
    "status": "active"
  }'
```

### 3.2 Recommended Bucket Layout

| Bucket Name | Table | Purpose | Retention |
|-------------|-------|---------|-----------|
| `healthcare_obs_gen` | `logs` | All Epic SIEM/Clinical/HL7/FHIR + Network syslog + NetFlow logs | 35 days |
| *(default_logs)* | `logs` | Existing data — untouched | Per existing config |

**Why a single custom bucket (not one per generator)?**
- DQL queries can target one bucket with filtered attributes
- Reduces bucket sprawl — Dynatrace has bucket limits per environment
- Cross-generator correlation queries (Epic clinical events ↔ network events) run in a single bucket scan
- If you later need sub-segmentation, add OpenPipeline routing rules to split within the bucket

### 3.3 Metrics Consideration

Grail metrics (via Metrics v2 API) land in the built-in metrics store, not a custom bucket. Segmentation is handled by metric key prefixing:

```
# Network metrics already use clear prefixes:
if.traffic.in.bytes
if.traffic.out.bytes
device.cpu.utilization
device.memory.utilization

# Recommend adding a top-level prefix:
healthcare.network.if.traffic.in.bytes
healthcare.network.device.cpu.utilization
```

This prevents collision with any existing `if.traffic.*` or `device.cpu.*` metrics from real monitoring.

---

## 4. OpenPipeline Configuration

### 4.1 Architecture Overview

```
                    ┌──────────────────────┐
                    │   Dynatrace Cluster   │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                 │
     Log Ingest v2      Metrics v2        Events v2
     /api/v2/logs       /api/v2/metrics   /api/v2/events
              │                │                 │
              ▼                ▼                 ▼
     ┌────────────────┐  ┌──────────┐   ┌──────────────┐
     │  OpenPipeline   │  │  Metric  │   │   Event     │
     │  (Log Processing)│  │  Store   │   │   Store     │
     └───────┬────────┘  └──────────┘   └──────────────┘
             │
    ┌────────┴─────────┐
    │ Routing Rule:     │
    │ dt.source.generator│
    │ == "healthcare-   │
    │    obs-gen-v2"    │
    │                   │
    ▼                   ▼
┌──────────────┐  ┌──────────────┐
│ healthcare_  │  │ default_logs │
│ obs_gen      │  │ (untouched)  │
│ bucket       │  │              │
└──────────────┘  └──────────────┘
```

### 4.2 OpenPipeline — Log Processing Pipeline

Create a **custom processing pipeline** in OpenPipeline for Logs:

**Pipeline: `healthcare-obs-gen-logs`**

**Step 1 — Matching Condition (route entry)**
```
matchesPhrase(dt.source.generator, "healthcare-obs-gen-v2")
```

**Step 2 — Epic SIEM XML Parsing** (for Epic logs that arrive as XML-in-syslog)
```
Condition: matchesPhrase(log.source, "epic-simulator")
Processing:
  - DQL Processing: Parse XML content field to extract E1Mid, EMPid, Action, etc.
  - Add attribute: dt.source.subsystem = "epic-siem"
```

Example DQL processing rule:
```
FIELDS_ADD(
  epic.event.id = EXTRACT(content, "E1Mid>(.*?)<"),
  epic.user.id = EXTRACT(content, "EMPid>(.*?)<"),
  epic.action = EXTRACT(content, "Action>(.*?)<"),
  epic.source.ip = EXTRACT(content, "IP.*?Value>(.*?)<")
)
```

**Step 3 — Network Syslog Classification**
```
Condition: matchesPhrase(log.source, "cisco_ios") OR matchesPhrase(log.source, "paloalto") OR matchesPhrase(log.source, "fortinet") OR matchesPhrase(log.source, "aruba_os")
Processing:
  - Add attribute: dt.source.subsystem = "network-syslog"
  - Add attribute: dt.security.zone based on network.device.role
```

**Step 4 — NetFlow Log Classification**
```
Condition: matchesPhrase(log.source, "netflow")
Processing:
  - Add attribute: dt.source.subsystem = "network-flow"
  - Convert network.flow.bytes to Long type
  - Convert network.flow.packets to Long type
  - Add attribute: network.flow.direction based on src/dst analysis
```

**Step 5 — FHIR API Log Classification**
```
Condition: matchesPhrase(log.source, "epic-fhir") OR content LIKE "%/api/FHIR/R4/%"
Processing:
  - Add attribute: dt.source.subsystem = "epic-fhir-api"
  - Parse JSON fields from content if not already structured
```

**Step 6 — Storage Assignment (critical)**
```
Route ALL matched records → bucket: healthcare_obs_gen
```

### 4.3 OpenPipeline — Metric Attributes (optional enrichment)

For metrics ingested via `/api/v2/metrics/ingest`, OpenPipeline for Metrics can:
- Add `dt.source.generator` dimension to all metrics matching `healthcare.network.*` prefix
- Not strictly required if metric keys are already uniquely prefixed

### 4.4 OpenPipeline — Events Pipeline

For SNMP trap events via `/api/v2/events/ingest`:
- Route events with `network.device.*` properties to the healthcare bucket
- Add `dt.source.subsystem = "network-trap"` for classification

---

## 5. Generator Code Changes Required

### 5.1 Network Generator — DynatraceOutput Enrichment

In `src/network_generator/outputs/dynatrace.py`, the `_log_to_dt()` method needs three additional attributes:

```python
def _log_to_dt(self, event: LogEvent) -> dict:
    record = {
        # ... existing fields ...
        
        # ADD these segmentation attributes:
        "dt.source.generator": "healthcare-obs-gen-v2",
        "dt.source.generator.version": "2.0.0",
        "dt.source.deployment": os.environ.get("DEPLOYMENT_ID", "aks-healthcare-gen"),
    }
    return record
```

Same for `send_flows()` and the trap event payload.

### 5.2 Epic Generator — OTLPOutput Enrichment

In the Epic generator's `OTLPOutput`, add the same attributes as `default_attributes`:

```python
otlp = OTLPOutput(
    endpoint=endpoint,
    api_token=token,
    mode="dynatrace",
    default_attributes={
        "dt.source.generator": "healthcare-obs-gen-v2",
        "dt.source.generator.version": "2.0.0",
        "dt.source.deployment": "aks-healthcare-gen",
    }
)
```

### 5.3 Network Metric Key Prefixing

In `src/network_generator/scenarios/baseline.py`, prefix metric keys:

```python
# Change:
metric_key="if.traffic.in.bytes"
# To:
metric_key="healthcare.network.if.traffic.in.bytes"
```

Or handle it in `DynatraceOutput._metric_to_mint()` with a global prefix.

### 5.4 K8s ConfigMap Updates

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: generator-config
  namespace: healthcare-gen
data:
  DT_ENDPOINT: "https://{env-id}.live.dynatrace.com"  # or .apps.dynatrace.com for Platform
  OUTPUT_DIR: "/app/output"
  EPIC_TICK_INTERVAL: "10"
  NETWORK_TICK_INTERVAL: "60"
  NETWORK_MODE: "realtime"
  LOG_LEVEL: "INFO"
  # NEW: Tell network generator to use Dynatrace output
  NETWORK_OUTPUT: "both"          # "file" + "dynatrace" simultaneously
  EPIC_OUTPUT_MODE: "otlp"        # Switch from stdout to OTLP/DT ingest
  # NEW: Segmentation
  DEPLOYMENT_ID: "aks-healthcare-gen"
  GENERATOR_VERSION: "2.0.0"
```

### 5.5 K8s Secret Updates

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: dt-credentials
  namespace: healthcare-gen
type: Opaque
stringData:
  DT_API_TOKEN: "<actual-token>"   # Needs scopes: logs.ingest, metrics.ingest, events.ingest
```

### 5.6 Required API Token Scopes

The DT API token needs these scopes:

| Scope | Used By | Purpose |
|-------|---------|---------|
| `logs.ingest` | Epic (OTLP/DT mode) + Network (DynatraceOutput) | Push log events |
| `metrics.ingest` | Network (DynatraceOutput MINT) | Push SNMP/interface metrics |
| `events.ingest` | Network (SNMP traps as events) | Push custom events |
| `openPipeline.events` | OpenPipeline config (optional) | Manage pipeline via API |
| `storage:buckets:read` | Bucket management (optional) | Verify bucket exists |
| `storage:bucket-definitions:write` | Bucket creation (optional) | Create healthcare bucket |

**Minimum required: `logs.ingest`, `metrics.ingest`, `events.ingest`**

---

## 6. Ingestion Flow — End to End

### 6.1 Epic Generator Path

```
Epic Pod (AKS)
  │
  ├─ SIEM events (XML-in-syslog format)
  ├─ Clinical events (XML)
  ├─ HL7v2 messages (pipe-delimited)
  ├─ FHIR API logs (JSON)
  ├─ MyChart logs (JSON)
  └─ ETL job logs (JSON)
  │
  ▼
OTLPOutput (mode="dynatrace")
  → POST /api/v2/logs/ingest
  → Headers: Api-Token, Content-Type: application/json
  → Payload: Array of {content, log.source, severity, timestamp, epic.*, dt.source.*}
  │
  ▼
OpenPipeline (Logs)
  → Match: dt.source.generator == "healthcare-obs-gen-v2"
  → Parse: XML extraction for SIEM events
  → Classify: dt.source.subsystem based on log.source
  → Route: → healthcare_obs_gen bucket
```

### 6.2 Network Generator Path

```
Network Pod (AKS)
  │
  ├─ Syslog events (LogEvent → JSON)
  ├─ Interface/device metrics (MetricEvent → MINT)
  ├─ SNMP traps (TrapEvent → JSON events)
  └─ NetFlow records (FlowRecord → JSON logs)
  │
  ▼
DynatraceOutput
  ├─ Logs → POST /api/v2/logs/ingest (syslog + flows)
  ├─ Metrics → POST /api/v2/metrics/ingest (MINT protocol)
  └─ Events → POST /api/v2/events/ingest (traps)
  │
  ▼
OpenPipeline (Logs)
  → Match: dt.source.generator == "healthcare-obs-gen-v2"
  → Classify by log.source (cisco_ios, paloalto, netflow, etc.)
  → Type conversions (bytes, packets → Long)
  → Route: → healthcare_obs_gen bucket
```

---

## 7. DQL Querying Strategy

### 7.1 Bucket-Scoped Queries (Critical for Performance)

**Always specify the bucket** to avoid scanning default_logs:

```dql
// All healthcare generator logs
fetch logs, scanLimitGBytes: 500, samplingRatio: 1000
| filter dt.source.generator == "healthcare-obs-gen-v2"
// This is fast because the bucket ONLY contains your data
```

vs. without bucket routing:
```dql
// BAD: Scans entire default_logs table
fetch logs
| filter dt.source.generator == "healthcare-obs-gen-v2"
// Slow — has to scan through ALL logs to find yours
```

### 7.2 Recommended Query Patterns

**Epic SIEM Overview**
```dql
fetch logs, from: healthcare_obs_gen
| filter dt.source.subsystem == "epic-siem"
| summarize count(), by: {epic.event.id, epic.action, bin(timestamp, 5m)}
| sort timestamp desc
```

**Network Device Health**
```dql
fetch logs, from: healthcare_obs_gen
| filter dt.source.subsystem == "network-syslog"
| filter severity == "ERROR" or severity == "CRITICAL"
| summarize count(), by: {`network.device.hostname`, `network.device.site`, bin(timestamp, 5m)}
```

**Cross-Generator Correlation** (why single bucket matters)
```dql
fetch logs, from: healthcare_obs_gen
| filter timestamp > now() - 1h
| summarize 
    epic_events = countIf(dt.source.subsystem == "epic-siem"),
    network_events = countIf(dt.source.subsystem == "network-syslog"),
    flow_events = countIf(dt.source.subsystem == "network-flow"),
    by: bin(timestamp, 5m)
```

**NetFlow Traffic Analysis**
```dql
fetch logs, from: healthcare_obs_gen
| filter dt.source.subsystem == "network-flow"
| summarize 
    total_bytes = sum(toLong(`network.flow.bytes`)),
    total_packets = sum(toLong(`network.flow.packets`)),
    unique_sources = countDistinct(`network.flow.src_ip`),
    by: {`network.device.site`, bin(timestamp, 5m)}
```

**Network Metrics**
```dql
timeseries avg(healthcare.network.device.cpu.utilization), 
    by: {device, site}
| filter site == "kcrmc-main"
```

### 7.3 Query Performance Tips

1. **Always use `from: healthcare_obs_gen`** to scope to your bucket
2. **Filter early** — put `dt.source.subsystem` or `log.source` filters first
3. **Use `bin(timestamp, interval)`** for time-series aggregations instead of raw records
4. **Avoid `fetch logs` without filters** — even in a dedicated bucket, be specific
5. **Use `scanLimitGBytes`** to prevent runaway queries during development
6. **Index attributes** — `dt.source.subsystem`, `network.device.site`, `network.device.hostname` are ideal index candidates if volume is high

---

## 8. Future App Architecture (Dynatrace App)

### 8.1 App Toolkit (AppEngine) Design

If you build a Dynatrace App for this generator:

```
healthcare-obs-app/
├── app.config.ts          # App manifest
├── src/
│   ├── app/
│   │   ├── pages/
│   │   │   ├── Overview.tsx        # Combined dashboard
│   │   │   ├── EpicSiem.tsx        # Epic SIEM drill-down
│   │   │   ├── NetworkHealth.tsx   # Network device health
│   │   │   ├── FlowAnalysis.tsx    # NetFlow traffic analysis
│   │   │   └── Scenarios.tsx       # Active scenario status
│   │   └── components/
│   │       ├── SiteSelector.tsx    # Filter by KC site
│   │       ├── TimeseriesChart.tsx
│   │       └── EventTable.tsx
│   └── api/
│       └── queries.ts             # DQL query library
```

### 8.2 App Query Architecture

**Pre-built query functions** (in `queries.ts`):

```typescript
// All queries target the dedicated bucket
const BUCKET = "healthcare_obs_gen";

export const epicSiemOverview = (timeframe: string) => `
  fetch logs, from: ${BUCKET}
  | filter dt.source.subsystem == "epic-siem"
  | filter timestamp > now() - ${timeframe}
  | summarize count(), by: {epic.event.id, bin(timestamp, 5m)}
`;

export const networkAlerts = (site?: string) => `
  fetch logs, from: ${BUCKET}
  | filter dt.source.subsystem == "network-syslog"
  | filter severity == "ERROR" or severity == "CRITICAL"
  ${site ? `| filter \`network.device.site\` == "${site}"` : ""}
  | sort timestamp desc
  | limit 100
`;
```

### 8.3 App Permissions Model

In `app.config.ts`:
```typescript
export default defineAppConfig({
  environmentUrl: "https://{env-id}.apps.dynatrace.com",
  app: {
    name: "Healthcare Observability Generator",
    version: "1.0.0",
    description: "Monitor and manage synthetic healthcare data generation",
  },
  scopes: [
    "storage:logs:read",           // Read from healthcare_obs_gen bucket
    "storage:metrics:read",        // Read network metrics
    "storage:events:read",         // Read SNMP trap events
    "environment:roles:viewer",    // View topology/entities
  ],
});
```

### 8.4 Dashboard vs. App Decision Matrix

| Criteria | Dashboard | App |
|----------|-----------|-----|
| **Quick visualization** | Yes — faster to build | Overkill |
| **Custom interactions** (toggle scenarios, site selector) | Limited | Full control |
| **API calls to generator** (start/stop scenarios via WebUI) | Not possible | Yes, via fetch() |
| **Sharing with team** | Easy — built-in sharing | Requires app deployment |
| **Maintenance** | Low — JSON export | Medium — TypeScript + AppEngine |
| **Recommendation** | **Start here** | Build when you need interactivity |

---

## 9. Implementation Checklist

### Phase 1 — Bucket & Pipeline Setup (Dynatrace UI)
- [ ] Create Grail bucket `healthcare_obs_gen` (Settings → Log Monitoring → Log storage)
- [ ] Create API token with scopes: `logs.ingest`, `metrics.ingest`, `events.ingest`
- [ ] Create OpenPipeline processing pipeline for logs
  - [ ] Matching rule: `dt.source.generator == "healthcare-obs-gen-v2"`
  - [ ] Storage routing: → `healthcare_obs_gen` bucket
  - [ ] Classification rules for each subsystem
  - [ ] XML parsing for Epic SIEM events

### Phase 2 — Generator Code Changes
- [ ] Add `dt.source.generator`, `dt.source.generator.version`, `dt.source.deployment` to Network `DynatraceOutput`
- [ ] Add same attributes to Epic `OTLPOutput` default_attributes
- [ ] Prefix network metric keys with `healthcare.network.`
- [ ] Update K8s ConfigMap with `DT_ENDPOINT` and output mode settings
- [ ] Update K8s Secret with actual `DT_API_TOKEN`
- [ ] Switch Epic from `stdout` to `otlp` output mode
- [ ] Switch Network from `file` to `both` (file + dynatrace) output mode

### Phase 3 — Deploy & Validate
- [ ] Rebuild all 3 images → push to ACR → restart deployments
- [ ] Verify logs appear in `healthcare_obs_gen` bucket via DQL
- [ ] Verify metrics appear with `healthcare.network.*` prefix
- [ ] Verify SNMP trap events appear in Events
- [ ] Confirm NO data leaks into default_logs bucket
- [ ] Confirm old generator data remains unaffected

### Phase 4 — Querying & Visualization
- [ ] Build initial dashboard with overview tiles
- [ ] Test cross-generator correlation queries
- [ ] Set up metric alerts for network device health
- [ ] (Future) Build Dynatrace App for interactive control

---

## 10. Architecture Decision Records

### ADR-1: Single Bucket vs. Multiple Buckets
**Decision**: Single `healthcare_obs_gen` bucket for all generator data.
**Rationale**: Cross-correlation queries, bucket quota limits, simpler OpenPipeline routing. Subsystem filtering via `dt.source.subsystem` attribute provides logical separation.

### ADR-2: Direct API Ingest vs. OTel Collector
**Decision**: Direct API ingest (Log Ingest v2, Metrics v2, Events v2).
**Rationale**: Generators already have Dynatrace-native output adapters built in. Adding an OTel Collector would add infrastructure complexity for no benefit. The DynatraceOutput adapter handles batching, retries, and auth. If you later need protocol fan-out (send to DT + Splunk simultaneously), add an OTel Collector at that point.

### ADR-3: Metric Key Prefixing
**Decision**: Prefix all network metrics with `healthcare.network.` namespace.
**Rationale**: Prevents collision with real infrastructure metrics (OneAgent-collected `cpu.utilization`, real `if.traffic.*`). Makes it immediately obvious in metric browser that these are synthetic.

### ADR-4: `dt.source.generator` as Segmentation Key
**Decision**: Use `dt.source.generator` attribute (not `log.source`) as the primary discriminator.
**Rationale**: `log.source` values like `"epic-simulator"` and `"cisco_ios"` are semantically meaningful and should remain. The generator version attribute is orthogonal — it answers "which version of the generator produced this?" while `log.source` answers "what kind of data is this?".
