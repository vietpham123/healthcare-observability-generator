# Healthcare Observability Generator

Combined Epic SIEM + Network log generator for **Lawrence Regional Medical Center** — a synthetic healthcare observability data platform built for Dynatrace, with a companion **Dynatrace Platform App** for real-time monitoring and a **Web UI** for scenario orchestration.

## Overview

Generates temporally-correlated logs and metrics across two domains, sending data directly to Dynatrace via API:

| Generator | Data Types | Vendors/Systems | DT Transport |
|-----------|-----------|-----------------|--------------|
| **Epic SIEM** | SIEM audit, Clinical, HL7, FHIR, MyChart, ETL | Epic Hyperspace, Interconnect, Bridges, MyChart | Log Ingest API v2 |
| **Network** | Syslog, SNMP metrics, NetFlow, Traps | Cisco IOS/ASA, Palo Alto, FortiGate, F5, Citrix, Aruba | Log Ingest + Metrics (MINT) + Events v2 |

### Hospital Profile — Lawrence Regional Medical Center

| Site | Code | IP Range | Devices | Description |
|------|------|----------|---------|-------------|
| **Main Campus (Lawrence, KS)** | `kcrmc-main` | `10.10.x.x` | 16 | 500-bed regional medical center (ED, ICU, Med-Surg, OR, L&D, etc.) |
| **Oakley Rural Health** | `oak-clinic` | `10.20.x.x` | 2 | Rural Health & Specialty Outreach |
| **Wellington Care Center** | `wel-clinic` | `10.30.x.x` | 2 | Urgent Care & Family Medicine |
| **Belleville Family Medicine** | `bel-clinic` | `10.40.x.x` | 2 | Primary Care & Pediatrics |
| **HQ Data Center (Olathe, KS)** | `hq-dc` | `10.50.x.x` | 4 | Infrastructure — Compute & Storage |
| **West Branch Office (Dodge City, KS)** | `branch-west` | `10.60.x.x` | 3 | Infrastructure — Remote Office |
| **WAN Transit** | — | `172.16.0.x` | — | MPLS/SD-WAN interconnects |
| **Public-facing** | — | `203.0.113.x` | — | MyChart, Interconnect, VPN |

**Total: 29 devices across 6 sites**

> **Note**: Legacy site codes (`tpk-clinic`, `wch-clinic`, `lwr-clinic`) are aliased to the current codes above via OpenPipeline for backward compatibility.

---

## Dynatrace Platform App — Healthcare Health Monitoring

A custom Dynatrace platform app (`my.healthcare.health.monitoring`) provides real-time visualization of all generated data with health-indicator overlays, auto-refresh, and scenario-aware monitoring.

**Current Version**: v1.18.1

### App Pages

| # | Page | Route | Description |
|---|------|-------|-------------|
| 1 | **Overview** | `/` | Campus map (Kansas geo projection), KPI cards, login health, event distribution |
| 2 | **Security & Compliance** | `/security` | Break-the-glass audit, login analysis, after-hours access — handles Ransomware + Insider Threat |
| 3 | **Integration Health** | `/integration` | Mirth Connect, HL7 delivery, FHIR response times, ETL status — handles HL7 Interface Failure |
| 4 | **Network Health** | `/network` | Device fleet CPU/memory honeycomb, traffic charts, NetFlow — handles Core Switch Failure |
| 5 | **Epic Health** | `/epic` | Login trends, clinical activity, SIEM audit, Interconnect API usage |
| 6 | **MyChart Portal** | `/mychart` | Patient portal login activity, messaging trends, scheduling |
| 7 | **Site View** | `/sites` | Per-site drill-down with 2×3 grid — 4 clinical sites + 2 infrastructure sites |
| 8 | **Explore** | `/explore` | Raw log viewer with pipeline selector + free-form DQL query explorer |

### Section Health Indicators

Every page includes colored health indicators (`SectionHealth` component) that show the real-time status of key metrics:

| Indicator | Page | Metric | Healthy | Warning | Critical | Baseline |
|-----------|------|--------|---------|---------|----------|----------|
| Epic Login Success | Overview, Epic, Security | All Epic login outcomes | ≥65% | ≥45% | <45% | ~97-98% |
| Auth Login Success | Security | BCA_LOGIN_SUCCESS vs FAILEDLOGIN | ≥80% | ≥60% | <60% | ~97-98% |
| FHIR Health Rate | Integration, Overview | FHIR R4 API success rate | ≥85% | ≥70% | <70% | ~95% |
| ETL Success Rate | Integration, Overview | ETL batch job success | ≥88% | ≥70% | <70% | ~95% |
| HL7 Delivery | Integration | HL7 v2.x message delivery | ≥99% | ≥50% | <50% | 100% |
| STAT Order Rate | Epic | STAT orders % of all orders | ≤5% | ≤10% | >10% | ~3% |
| MyChart Login | MyChart | Portal login success rate | ≥95% | ≥80% | <80% | ~95% |
| BTG Total Count | Security | Break-the-Glass event count | ≤200 | ≤400 | >400 | ~20-50 |
| After-Hours BTG | Security | BTG events outside 6 AM–10 PM | ≤50 | ≤100 | >100 | ~0-5 |
| Network CPU | Network, Overview | Average device CPU utilization | ≤40% | ≤60% | >60% | ~25-35% |
| Device Up Ratio | Network | Devices reporting in last 5 min | 100% | ≥95% | <95% | 100% |
| Mirth Channel Health | Integration | Channels actively processing | 100% | ≥80% | <80% | 100% |
| Campus Map Health | Overview, Sites | Per-site login success rate | ≥90% | ≥70% | <70% | ~97-98% |

**Auto-Refresh**: All health indicators poll every **30 seconds** (`refetchInterval: 30_000` on `useDql`), providing near-real-time status updates without manual refresh.

### Campus Map

The Overview page features an interactive Kansas map with:
- Real equirectangular projection (KS boundary, I-70/I-35 highways, reference cities, county grid)
- 6 site icons: hospital icons for 4 clinical sites, server rack icons for 2 infrastructure sites (hq-dc, branch-west)
- Health status coloring (green/amber/red) based on login success rates (clinical) or event activity (infra)
- Live NetFlow animation — particle dots flow between hub (Lawrence) and satellite sites

### Site View — 2×3 Grid Layout

| Top Row | Bottom Row |
|---------|------------|
| Lawrence Regional Medical Center (`kcrmc-main`) | Oakley Rural Health (`oak-clinic`) |
| HQ Data Center (`hq-dc`) | Wellington Care Center (`wel-clinic`) |
| West Branch Office (`branch-west`) | Belleville Family Medicine (`bel-clinic`) |

Each site card shows: site name, bed count (clinical) or description (infra), login rate, active users, event count, and device count.

### Site Filtering

Every page has a site filter toolbar. Selecting a site filters:
- **`fetch logs` queries**: injects `| filter healthcare.site == "..."`
- **`timeseries` queries**: injects `filter: {site == "..."}` into metric aggregations
- **NetFlow queries**: filters on `network.device.site`

Site aliases (tpk→oak, wch→wel, lwr→bel) are automatically expanded so historical data matches.

### Tech Stack

- `dt-app` 1.8.1, React 18, TypeScript 5.9
- Strato components: `TimeseriesChart`, `HoneycombChart`, `DonutChart`, `CategoricalBarChart`, `SingleValue`, `Tooltip`
- DQL via `@dynatrace-sdk/react-hooks` (`useDql`) with `refetchInterval` for auto-refresh
- All charts use `gapPolicy="connect"` for continuous lines

---

## Web UI — Scenario Control Panel

**URL**: `http://<webui-loadbalancer-ip>` (port 80 via K8s LoadBalancer)

The Web UI (FastAPI + HTML/JS) provides:

### Scenario Management
- **Enable/Disable** any of the 5 scenarios via toggle buttons
- Scenarios are mutually exclusive — enabling one disables others
- Changes propagate to both Epic and Network generators via K8s API (environment variable injection + rollout restart)
- Visual feedback with status indicators and countdown timers

### Demo Guide System (v2.4.0)
- **Step-by-step walkthrough** guides for each scenario
- Guided narrative explaining what to observe in the DT app
- Deep links to specific DT app pages for each observation step
- Auto-advance with manual override

### Architecture
- FastAPI backend with K8s API integration (in-cluster `ServiceAccount` with RBAC)
- Injects `ACTIVE_SCENARIO` env var into generator deployments
- Triggers `kubectl rollout restart` for clean scenario transitions
- HTML/JS frontend with real-time status polling

---

## Quick Start

### Local Development

```bash
pip install -r requirements.txt

# Start the Web UI (generator control panel)
uvicorn webui.app:app --host 0.0.0.0 --port 8080
```

### Docker Compose

```bash
cd deploy/docker
export DT_ENDPOINT="https://{your-env-id}.live.dynatrace.com"
export DT_API_TOKEN="dt0c01...."
docker compose up -d
# UI at http://localhost:8080
```

### Kubernetes (AKS)

```bash
# 1. Update deploy/kubernetes/base/configmap.yaml with your DT_ENDPOINT
# 2. Update deploy/kubernetes/base/secret.yaml with your DT_API_TOKEN
kubectl apply -k deploy/kubernetes/overlays/dev/

# Production (higher resource limits):
kubectl apply -k deploy/kubernetes/overlays/prod/
```

### Deploy the DT Platform App

```bash
cd dynatrace-apps/healthcare-health-monitoring
npm install
npx dt-app deploy   # Opens browser for SSO auth
```

> **Note**: `npx dt-app deploy` requires local execution (browser SSO). It does not work via SSH.

---

## Data Realism Assessment — Overall Score: 78%

This section documents how accurately the generated data emulates real healthcare IT telemetry. The overall score accounts for a "would it fool an expert" factor — raw weighted metrics score 86%, discounted for areas where a subject-matter expert would detect synthetic patterns on close inspection.

### Detailed Scoring (10 Dimensions)

| # | Dimension | Weight | Score | Weighted | Assessment |
|---|-----------|--------|-------|----------|------------|
| 1 | **Epic Audit Log XML format** | 15% | 90% | 13.5% | Correct `E1Mid` event types, XML envelope, 30+ `<Mnemonic>` fields. Real Epic admins recognize this format. Missing: Epic version-specific header fields (EpicSN). |
| 2 | **HL7 v2.x message structure** | 10% | 85% | 8.5% | Proper MSH/PID/OBR/OBX segments, correct message types (ADT^A01, ORU^R01, ORM^O01). Clinical content is randomized, not clinically coherent. |
| 3 | **FHIR R4 API patterns** | 8% | 80% | 6.4% | Correct resource types and endpoint patterns. Resource-level detail (resourceType, fhir_endpoint) not yet extracted by OpenPipeline. |
| 4 | **Network syslog per vendor** | 15% | 92% | 13.8% | 7 vendors with correct log format patterns. 6 event types (SYSTEM, SECURITY, INTERFACE, TRAFFIC, ROUTING, THREAT). 40+ parameterized templates. |
| 5 | **Multi-site topology realism** | 10% | 88% | 8.8% | 6 sites, 29 devices, proper IP addressing per site, WAN transit. Deduction: clinic sites have 2 devices each (real: 4-8). |
| 6 | **Login rate & temporal curves** | 10% | 95% | 9.5% | 97-98% baseline matches real hospitals. Time-of-day curve (0.30 night → 1.0 day shift). Login failures distributed across sites. |
| 7 | **Event volume ratios** | 8% | 55% | 4.4% | Compressed scale (~5K SIEM/hr vs millions in production). SIEM dominated by login events (85%) — real: ~40-50% logins, 30% clinical, 20% API. |
| 8 | **Scenario attack patterns** | 10% | 85% | 8.5% | Ransomware kill chain, insider threat, HL7 failure, core switch failure — all real-world threat models. Recovery is instant (pod restart) vs hours in reality. |
| 9 | **Cross-system correlation** | 8% | 90% | 7.2% | Epic + Network + HL7 + FHIR + MyChart correlated temporally and by site. Strongest differentiator — most hospitals use 3-5 separate tools. |
| 10 | **Data ingestion pathway** | 6% | 95% | 5.7% | Same DT APIs (Log Ingest v2, Metrics MINT, Events v2) real customers use. OpenPipeline field extraction is production-grade. |

**Raw weighted total: 86.3% → Adjusted to 78% for expert scrutiny discount**

### What Would Push It to 90%+

1. Clinically coherent HL7/FHIR payloads (matching diagnosis → procedure → medication chains)
2. Realistic event volume ratios (more clinical events relative to logins)
3. Larger device topology (100+ devices for a 500-bed hospital)
4. ETL batch timing patterns (hourly Clarity ETL runs, not random ticks)
5. Extract FHIR `resourceType` and `fhir_endpoint` fields in OpenPipeline

### Audience-Specific Accuracy

| Audience | Effective Accuracy | Notes |
|----------|--------------------|-------|
| **CTO / IT Director** | ~90% | Sees unified dashboard, cross-system correlation, attack scenarios. Convincing. |
| **Dynatrace SE / Pre-sales** | ~85% | Demonstrates real API paths, OpenPipeline, Grail queries. Defensible. |
| **Epic Analyst / Clarity DBA** | ~70% | Recognizes XML structure but spots random clinical combinations and compressed volume. |
| **Mirth/HL7 Engineer** | ~75% | Correct message types and segments, but would notice volume ratios and lack of Mirth channel-level detail. |
| **Network Architect** | ~80% | Vendor-specific syslog is convincing; 29 devices is low for a 500-bed hospital. |
| **Clinical Informaticist** | ~55% | Random ICD-10 + CPT pairings are immediately obvious. Frame as "synthetic test data." |

### Data Fidelity by Source

| Data Source | Realism | Notes |
|-------------|---------|-------|
| **Epic Audit Log XML** | ★★★★½ | XML structure with `E1Mid`, 30+ mnemonic fields. Real Epic admins recognize the format. |
| **HL7 v2.x Messages** | ★★★★☆ | Standard MSH/PID/OBR/OBX segments. Message types correct. Clinical content randomized. |
| **FHIR R4 Resources** | ★★★★☆ | Standard resource types with proper structure. Realistic endpoint patterns. |
| **Mirth Connect Metrics** | ★★★★☆ | Channel names and metric shapes match real Mirth deployments. |
| **Network SNMP/Syslog** | ★★★★★ | Vendor-specific formats (Cisco IOS, Palo Alto, FortiGate, Aruba, Citrix, F5, Cisco ASA) with 6 event types and parameterized templates. |
| **Login Success Rate** | ★★★★★ | ~97-98% baseline with site variation (95-99%). Matches real hospitals. |
| **Scenario Patterns** | ★★★★☆ | Real threat models hospitals train on. Ransomware kill chain is multi-phase. |
| **Clinical Content** | ★★☆☆☆ | Random ICD-10/CPT combinations. Not clinically coherent. |
| **Scale** | ★★☆☆☆ | Thousands of events/hr vs millions in production. Defensible as "condensed for demo." |

### OpenPipeline Site Distribution

All Epic log types are distributed across 4 clinical sites via OpenPipeline `endsWith()` on a per-record field:

| Processor | Field | Distribution |
|-----------|-------|-------------|
| SIEM XML | `EMPID` | Last digit: 0,1,2,a,b → kcrmc-main; 3,4,c → tpk; 5,6,d → wch; 7,8,9,e,f → lwr |
| ETL JSON | `records_processed` | Same digit-based mapping |
| FHIR API | `correlation_id` | Same mapping (hex-aware for UUID fields) |
| HL7 Message | `hl7_msg_control_id` | Same mapping |
| FHIR Resource | `fhir_resource_id` | Same mapping (hex-aware) |

UUID fields (FHIR, correlation IDs) produce hex characters `a-f`; the distribution handles these to prevent skew.

### Real-World Data Ingestion into Dynatrace

The ingestion paths used in this demo are the **same APIs real customers use**:

| Data Source | Real Ingestion Path | Challenge | Notes |
|-------------|-------------------|-----------|-------|
| **Network SNMP metrics** | OneAgent/ActiveGate SNMP extension, or OTel Collector | ★☆☆☆☆ Easy | Standard DT capability. Many hospitals already do this. |
| **Network Syslog** | Fluentd/Fluent Bit/OTel Collector → DT Log Ingest API | ★☆☆☆☆ Easy | Generic log forwarding — standard practice. |
| **Mirth Connect metrics** | JMX extension or custom ActiveGate extension polling Mirth REST API | ★★☆☆☆ | Requires a small custom extension or script. |
| **HL7 message telemetry** | Mirth/Rhapsody logging → DT Log module or OTel Collector | ★★☆☆☆ | Mirth already logs every message. Configuration change only. |
| **FHIR API telemetry** | OpenTelemetry instrumentation on FHIR server, or access log forwarding | ★★☆☆☆ | Standard REST API instrumentation. |
| **Epic Audit Logs** | Epic Audit Log Export → log shipper → DT Log Ingest API | ★★★☆☆ | Feasible but requires Epic admin cooperation and HIPAA governance. |
| **Epic real-time events** | Epic's real-time audit feed (contractual add-on) | ★★★★☆ Hard | Batch exports are hourly/daily. Real-time requires Epic subscription. |

### Key Caveats for Customer Conversations

1. **Epic audit log latency**: Real-world Epic audit exports are batch (hourly/daily), not streaming. The demo shows events every 5 seconds — frame as "condensed timeline."

2. **Data access governance**: Getting permission to export Epic audit logs is an organizational/HIPAA decision, not a technical one. Dynatrace can ingest it; the question is policy approval.

3. **Cross-system correlation**: The unified view across Epic + Network + HL7 + FHIR in one platform is the **strongest demo point**. Most hospitals have these in 3-5 separate tools. Showing them unified in Dynatrace is genuinely novel.

4. **What a hospital CTO would say**: *"I believe you can ingest this. The hard part is getting my Epic team and CISO to agree on the data sharing policy."* — which positions Dynatrace as technically ready.

5. **Clinical content fidelity**: A clinician would notice non-coherent ICD-10 + CPT pairings. For security/ops audiences this is irrelevant; for clinical informatics, frame as "synthetic test data."

---

## Correlated Scenarios

Toggle scenarios via the Web UI to inject anomaly events across **both** generators simultaneously.

| Scenario | DT App Page | Login Impact | Key Mechanism |
|----------|-------------|--------------|---------------|
| **Normal Day Shift** | All (baseline) | ~97-98% | Time-of-day curves, standard clinical activity |
| **Ransomware Attack** | Security | 97% → ~65% | 4-phase kill chain: Recon → Harvest → Lateral → Exfil |
| **Insider Threat** | Security | Minimal | After-hours employee snooping with break-the-glass |
| **HL7 Interface Failure** | Integration | Minimal | Network switch port error on HL7 VLAN cascades to Mirth/FHIR/ETL |
| **Core Switch Failure** | Network | Minimal | Core switch fails, surviving infrastructure overloaded |

### Scenario Testing

| Scenario | Impact Level | Recovery Time |
|----------|-------------|---------------|
| Ransomware Attack | HIGH (Login 97%→65%) | ~50 min |
| Insider Threat | MEDIUM (BTG events) | ~10 min |
| HL7 Interface Failure | HIGH (FHIR/ETL/HL7) | ~10 min |
| Core Switch Failure | HIGH (Network devices) | ~10 min |
| Normal Day Shift | BASELINE | N/A |

### Mirth Connect Integration Engine

Synthetic Mirth Connect channel metrics (5 channels × 6 metrics each) via DT Metrics API v2.
Channels: LAB-RESULTS-IN, ADT-OUT, PHARMACY-ORDERS, RADIOLOGY-RESULTS, SCHEDULING-OUT.
During HL7 Interface Failure: queue depths climb, error rates spike, channels stop delivering.

### Network-Only Scenarios (YAML Playbooks)

BGP WAN Outage, DDoS Attack, DHCP Exhaustion, DNS Failure, STP Broadcast Storm, Link Flap Storm, Firewall HA Failover, VPN Cascade Failure, Wireless AP Mass Disconnect, Ransomware Lateral Movement.

### Scenario Lifecycle
1. **Enable** via WebUI → sets `ACTIVE_SCENARIO` env var on generator deployments
2. **Generators restart** with the new scenario active → anomaly data injected alongside baseline
3. **DT app** health indicators shift from green → amber/red within 30–60 seconds
4. **Disable** via WebUI → generators restart back to baseline-only mode
5. **Recovery** — health indicators return to green within 2–3 minutes

---

## Data Flow to Dynatrace

| Data Type | API Endpoint | Format | Key Attributes |
|-----------|-------------|--------|----------------|
| Epic SIEM logs | `/api/v2/logs/ingest` | DT Log Ingest JSON | `healthcare.pipeline=healthcare-epic`, `healthcare.site` |
| Network syslog/firewall | `/api/v2/logs/ingest` | DT Log Ingest JSON | `healthcare.pipeline=healthcare-network`, `network.device.hostname` |
| SNMP/interface metrics | `/api/v2/metrics/ingest` | MINT line protocol | `healthcare.network.*` prefix, dimensions: `site`, `device`, `vendor` |
| SNMP traps | `/api/v2/events/ingest` | Custom events | `network.trap.severity`, `network.device` |
| NetFlow records | `/api/v2/logs/ingest` | DT Log Ingest JSON | `log.source=netflow`, `network.device.site`, `network.flow.*` |

### DQL Filter Constants (used by the DT app)

```
BUCKET  = dt.system.bucket == "observe_and_troubleshoot_apps_95_days"
EPIC    = ${BUCKET} AND healthcare.pipeline == "healthcare-epic"
NETWORK = ${BUCKET} AND healthcare.pipeline == "healthcare-network"
NETFLOW = log.source == "netflow"
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DT_ENDPOINT` | Yes | — | Dynatrace environment URL |
| `DT_API_TOKEN` | Yes | — | API token with `logs.ingest`, `metrics.ingest`, `events.ingest` scopes |
| `EPIC_OUTPUT_MODE` | No | `file` | `file`, `dynatrace`, or `both` |
| `NETWORK_OUTPUT` | No | `file` | `file`, `dynatrace`, `both`, `syslog`, `kafka`, `http` |
| `OUTPUT_DIR` | No | `/app/output` | Directory for file-based output |
| `EPIC_TICK_INTERVAL` | No | `10` | Seconds between Epic generator ticks |
| `NETWORK_TICK_INTERVAL` | No | `60` | Seconds between network generator ticks |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
| `ACTIVE_SCENARIO` | No | — | Active anomaly scenario (set by WebUI) |

---

## Project Structure

```
├── src/
│   ├── epic_generator/           # Epic SIEM log generator
│   │   ├── generators/           #   SIEM, Clinical, HL7, FHIR, MyChart, ETL
│   │   ├── models/               #   Patient, User, Session models
│   │   ├── outputs/              #   FileOutput, OTLPOutput (DT), API, MLLP, Syslog
│   │   ├── config/               #   Epic scenarios + reference data
│   │   ├── mirth_metrics.py      #   Mirth Connect metrics emitter
│   │   └── orchestrator.py       #   Main entry point with MultiOutput fan-out
│   ├── network_generator/        # Network log generator
│   │   ├── vendors/              #   7 vendor emulators (Cisco IOS/ASA, PA, FortiGate, Aruba, Citrix, F5)
│   │   ├── outputs/              #   DynatraceOutput, File, Syslog, HTTP, Kafka, SNMP, NetFlow
│   │   ├── protocols/            #   DHCP, DNS, NetFlow, SNMP, Wireless
│   │   ├── scenarios/            #   Baseline + engine + 10 YAML playbooks
│   │   ├── core/                 #   Models, topology, clock, random utils
│   │   └── cli.py                #   Click CLI entry point
│   └── shared/                   # Cross-generator coordination
├── webui/                        # FastAPI + HTML/JS control panel
│   ├── app.py                    #   FastAPI backend (K8s API integration, RBAC)
│   ├── static/                   #   Frontend JS, CSS, walkthrough assets
│   └── templates/                #   Jinja2 HTML templates
├── config/
│   ├── hospital/                 # topology.yaml (6 sites, 29 devices) + device_profiles.yaml
│   └── scenarios/                # 5 correlated scenario JSON definitions
├── dynatrace-apps/
│   └── healthcare-health-monitoring/   # DT Platform App (React + TypeScript)
│       ├── ui/app/pages/               #   8 pages: Overview, Epic, Network, Integration,
│       │                               #            Security, MyChart, Sites, Explore
│       ├── ui/app/components/          #   CampusMap, KpiCard, SiteFilter, HealthBadge,
│       │                               #   SiteCard, SectionHealth, Header
│       ├── ui/app/queries.ts           #   All DQL queries + filter functions (v1.5.0)
│       ├── ui/app/utils/               #   chartHelpers, queryHelpers (withSiteFilter)
│       └── app.config.json             #   App manifest + scopes (v1.18.1)
├── deploy/
│   ├── docker/                   # Dockerfiles + docker-compose.yaml
│   └── kubernetes/               # Kustomize: base + dev/staging/prod overlays
├── docs/
│   ├── ARCHITECTURE.md           # Design phases, deployment modes
│   ├── DEMO-FLOW.md              # Step-by-step demo walkthrough
│   ├── DYNATRACE_INGESTION_ADVISORY.md  # Ingestion architecture guidance
│   ├── LESSONS-LEARNED.md        # AI skill development lessons
│   └── PROMPTING_INSIGHTS.md     # AI-assisted development analysis
└── requirements.txt
```

---

## Deployment Architecture (AKS)

```
┌──────────────────────────────────────────────────────────────────┐
│ AKS Cluster (aks-healthcare-gen)                                 │
│                                                                  │
│  namespace: healthcare-gen          namespace: dynatrace          │
│  ┌─────────────────────────┐       ┌──────────────────────────┐  │
│  │ epic-generator  (v1.0.6)│─logs─→│ DT Operator              │  │
│  │ network-gen     (v1.2.0)│─metrics│ ActiveGate (routing +    │  │
│  │ webui           (v2.4.0)│       │   kubernetes-monitoring)  │  │
│  └─────────────────────────┘       └──────────────────────────┘  │
│           │                                    │                  │
│           │ DT Log/Metrics/Events API          │ K8s API watch   │
│           ▼                                    ▼                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Dynatrace Environment (Grail)                   │ │
│  │  Logs ← epic-siem + network + netflow                       │ │
│  │  Metrics ← healthcare.network.* (MINT)                      │ │
│  │  Events ← SNMP traps                                        │ │
│  │  Entities ← K8s cluster, workloads, pods (via Operator)     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  DT Platform App (my.healthcare.health.monitoring)       │
│  v1.18.1 — Auto-refresh (30s) + Tooltips                │
│                                                          │
│  Overview   ──→ Campus Map + KPIs + NetFlow animation    │
│  Epic       ──→ Login trends, audit, clinical events     │
│  Network    ──→ Device fleet, CPU/mem, honeycomb, NetFlow│
│  Integration──→ HL7, FHIR health, ETL, Mirth channels   │
│  Security   ──→ BTG events, failed logins, compliance    │
│  MyChart    ──→ Portal login, messaging, scheduling      │
│  Sites      ──→ 2×3 grid: 4 clinical + 2 infrastructure │
│  Explore    ──→ Raw log viewer + DQL sandbox              │
│                                                          │
│  All pages: SectionHealth (30s auto-refresh, tooltips)   │
│  Site filter toolbar, gapPolicy="connect"                │
│  Data source: DQL queries against Grail (useDql hook)    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Web UI (webui v2.4.0)                                   │
│  http://<LoadBalancer-IP>                                │
│                                                          │
│  Scenario Toggles ──→ K8s API (env var injection)        │
│  Demo Guides      ──→ Step-by-step walkthrough           │
│  Status Monitor   ──→ Real-time pod + scenario status    │
│                                                          │
│  Backend: FastAPI + kubernetes.client (in-cluster RBAC)  │
│  Frontend: HTML + vanilla JS                             │
└─────────────────────────────────────────────────────────┘
```

---

## Container Images

| Image | Tag | Description |
|-------|-----|-------------|
| `vietregistry.azurecr.io/healthcare-gen/epic` | `v1.0.6` | Epic SIEM generator with Mirth metrics + anomaly injection |
| `vietregistry.azurecr.io/healthcare-gen/network` | `v1.2.0` | Network generator with vendor-specific baseline events |
| `vietregistry.azurecr.io/healthcare-gen/webui` | `v2.4.0` | Web UI with K8s API + demo guides |

---

## Version History

| Version | Component | Changes |
|---------|-----------|---------|
| **v1.2.0** | **Network Gen** | **Enhanced baseline: 40+ vendor-specific syslog templates, 6 event types, 3-6 events/device/tick** |
| **v1.18.1** | **DT App** | **SiteView 2×3 grid, 6-site campus map with infra icons, hex-aware OpenPipeline distribution** |
| v1.17.0 | DT App | 6-site support, Invalid Date fix, timeseries conversion fallback |
| v1.16.0 | DT App | SectionHealth auto-refresh (30s), tooltip descriptions, threshold recalibration |
| v1.14.0 | DT App | SectionHealth component, Explore raw-log viewer, Security & Compliance page |
| v2.4.0 | WebUI | Clean up to 5 scenarios, rewrite demo guides |
| v2.3.0 | WebUI | Mirth Connect metrics, 4-scenario consolidation |
| v1.0.6 | Epic Gen | Mirth metrics emitter, login baseline tuning (97-98%), anomaly injection |
| v1.1.0 | Network Gen | Initial 6-site topology (29 devices), hq-dc + branch-west support |
| v1.0.0 | All | Initial release — Epic + Network generators, DT app, WebUI |

---

## SIEM Mnemonic Fields (v1.0.3+)

The Epic generator produces 30+ realistic mnemonic fields per SIEM event:

**Login events** (`BCA_LOGIN_SUCCESS`, `FAILEDLOGIN`):
`CLIENT_TYPE`, `LOGINERROR`, `LOGIN_CONTEXT`, `LOGIN_LDAP_ID`, `INTERNET_AREA`, `HYP_ACCESS_ID`, `REMOTE_IP`, `UID`, `LOGIN_SOURCE`

**Service audit events** (`IC_SERVICE_AUDIT`):
`SERVICECATEGORY`, `SERVICETYPE`, `SERVICENAME`, `HOSTNAME`, `INSTANCEURN`, `SERVICE_USER`, `SERVICE_USERTYP`

**Common fields**: `E1Mid`, `Action`, `Source`, `WorkstationID`, `Flag`, `EMPid`, `IP`, `CLIENTNAME`, `SYSLOG_PID`

---

## Sanitization

All data is synthetic and sanitized — cannot be traced to real systems:
- Employee IDs/names are generated, not from real Epic environments
- Workstation IDs follow realistic hospital patterns but are fabricated
- Service URNs are sanitized versions of real Epic API naming conventions
- IP addresses use non-routable or random ranges
- Patient names use obviously fake patterns (no real PHI)
- No real credentials, tokens, or environment identifiers in generated data

---

## Additional Documentation

- [Architecture & Implementation Guide](docs/ARCHITECTURE.md) — Design phases, deployment modes
- [Demo Flow](docs/DEMO-FLOW.md) — Step-by-step demo walkthrough
- [Dynatrace Ingestion Advisory](docs/DYNATRACE_INGESTION_ADVISORY.md) — OpenPipeline, Grail buckets, querying
- [Lessons Learned](docs/LESSONS-LEARNED.md) — Patterns, pitfalls, and proven strategies
- [Prompting Insights](docs/PROMPTING_INSIGHTS.md) — AI-assisted development analysis

---

## License

Internal — Dynatrace SE use only.
