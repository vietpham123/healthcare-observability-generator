# Healthcare Observability Generator

Combined Epic SIEM + Network log generator for **Lawrence Regional Medical Center** — a synthetic healthcare observability data platform built for Dynatrace, with a companion **Dynatrace Platform App** for real-time monitoring and a **Web UI** for scenario orchestration.

## Overview

Generates temporally-correlated logs and metrics across two domains, sending data directly to Dynatrace via API:

| Generator | Data Types | Vendors/Systems | DT Transport |
|-----------|-----------|-----------------|--------------|
| **Epic SIEM** | SIEM audit, Clinical, HL7, FHIR, MyChart, ETL | Epic Hyperspace, Interconnect, Bridges, MyChart | Log Ingest API v2 |
| **Network** | Syslog, SNMP metrics, NetFlow, Traps | Cisco IOS/ASA/NX-OS, Palo Alto, FortiGate, F5, Citrix, Aruba | Log Ingest + Metrics (MINT) + Events v2 |

### Hospital Profile — Lawrence Regional Medical Center

| Site | Code | IP Range | Description |
|------|------|----------|-------------|
| **Main Campus (Lawrence, KS)** | `kcrmc-main` | `10.10.x.x` | 500-bed regional medical center (ED, ICU, Med-Surg, OR, L&D, etc.) |
| **Oakley Rural Health** | `oak-clinic` | `10.20.x.x` | Rural Health & Specialty Outreach |
| **Wellington Care Center** | `wel-clinic` | `10.30.x.x` | Urgent Care & Family Medicine |
| **Belleville Family Medicine** | `bel-clinic` | `10.40.x.x` | Primary Care & Pediatrics |
| **WAN Transit** | — | `172.16.0.x` | MPLS/SD-WAN interconnects |
| **Public-facing** | — | `203.0.113.x` | MyChart, Interconnect, VPN |

> **Note**: Legacy site codes (`tpk-clinic`, `wch-clinic`, `lwr-clinic`) are aliased to the current codes above for backward compatibility.

---

## Dynatrace Platform App — Healthcare Health Monitoring

A custom Dynatrace platform app (`my.healthcare.health.monitoring`) provides real-time visualization of all generated data with health-indicator overlays, auto-refresh, and scenario-aware monitoring.

**Current Version**: v2.2.1

### App Pages

| Page | Route | Description |
|------|-------|-------------|
| **Overview** | `/` | Campus map (real Kansas geo projection), KPI cards, login health, event distribution, section health indicators |
| **Epic Health** | `/epic` | Login trends, clinical events, audit timelines, session analysis, STAT order rate |
| **Network Health** | `/network` | Device fleet CPU/memory honeycomb, traffic charts, NetFlow analysis, vendor distribution |
| **Integration Health** | `/integration` | HL7 delivery rates, FHIR response times, ETL pipeline status |
| **Security & Compliance** | `/security` | Break-the-glass events, failed login analysis, after-hours audit, BTG counts |
| **MyChart Portal** | `/mychart` | Patient portal login activity, messaging trends, scheduling, device distribution |
| **Site View** | `/sites` | Per-site drill-down with site cards — bed count, profile, events, devices |
| **Explore** | `/explore` | Raw log viewer with pipeline selector (Epic/Network) + free-form DQL query explorer |
| **Walkthrough** | `/walkthrough` | Interactive demo guide with step-by-step scenario walkthroughs |

### Section Health Indicators

Every page includes colored health indicators (`SectionHealth` component) that show the real-time status of key metrics:

| Indicator | Page | Metric | Healthy | Warning | Critical |
|-----------|------|--------|---------|---------|----------|
| Epic Login Success | Overview, Epic, Security | All Epic login outcomes (SUCCESS, FAILED, BLOCKED) | ≥65% | ≥45% | <45% |
| Auth Login Success | Authentication, Security | BCA_LOGIN_SUCCESS vs FAILEDLOGIN ratio | ≥80% | ≥60% | <60% |
| Failed Login Count | Authentication, Security | Raw failed login count (last 30 min) | ≤200 | ≤500 | >500 |
| FHIR Health Rate | Integration, Overview | FHIR R4 API success rate (HTTP 2xx/3xx) | ≥85% | ≥70% | <70% |
| ETL Success Rate | Integration, Overview | ETL batch job success (excludes RUNNING jobs) | ≥88% | ≥70% | <70% |
| HL7 Delivery | Integration | HL7 v2.x message volume (last 30 min) | ≥95% | ≥80% | <80% |
| STAT Order Rate | Epic | STAT orders as percentage of all orders | ≤15% | ≤25% | >25% |
| MyChart Login | MyChart | MYCHART_LOGIN event flow (volume-based) | ≥95% | ≥80% | <80% |
| BTG Total Count | Security | Break-the-Glass event count | ≤200 | ≤400 | >400 |
| After-Hours BTG | Security | BTG events outside 6 AM–10 PM | ≤50 | ≤100 | >100 |
| Network CPU | Network, Overview | Average network device CPU utilization | ≤60% | ≤80% | >80% |
| Device Up Ratio | Network | Devices seen in last 15 min vs total | ≥95% | ≥80% | <80% |

**Auto-Refresh**: All health indicators poll every **30 seconds** (`refetchInterval: 30_000` on `useDql`), providing near-real-time status updates without manual refresh.

**Tooltips**: Each indicator has a tooltip showing:
- Current status label (Healthy / Warning / Critical)
- Description of what is measured and why
- Threshold breakdown (● Healthy / ● Warning / ● Critical with specific values)
- Current measured value

### Campus Map

The Overview page features an interactive Kansas map with:
- Real equirectangular projection (KS boundary, I-70/I-35 highways, reference cities, county grid)
- Hospital site icons with health status (green/amber/red) based on login success rates
- Live NetFlow animation — particle dots flow between hub (Lawrence) and satellite clinics
- Hub-and-spoke topology: all flows originate from `kcrmc-main` (Lawrence, KS)

### Site Filtering

Every page has a site filter toolbar. Selecting a site filters:
- **`fetch logs` queries**: injects `| filter healthcare.site == "..."`
- **`timeseries` queries**: injects `filter: {site == "..."}` into metric aggregations
- **NetFlow queries**: filters on `network.device.site`

### Explore Page — Raw Log Viewer

The Explore page offers two views:
1. **Raw Logs**: Pipeline selector (Epic SIEM / Network) shows the last 100 log records with all fields in a DataTable
2. **DQL Sandbox**: Free-form DQL input for ad-hoc queries against any Grail data

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
- **Enable/Disable** any of the 4 focused scenarios via toggle buttons
- Scenarios are mutually exclusive — enabling one disables others
- Changes propagate to both Epic and Network generators via K8s API (environment variable injection + rollout restart)
- Visual feedback with status indicators and countdown timers

### Demo Guide System (v2.2.0)
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

### Scenario Testing (April 2026)

All 4 scenarios have been comprehensively tested. See [Scenario Test Report](docs/SCENARIO-TEST-REPORT.md) for detailed results.

| Scenario | Impact Level | Recovery Time |
|----------|-------------|---------------|
| Ransomware Attack | HIGH (Login 83%→44%) | ~50 min |
| Insider Threat | MEDIUM (BTG events) | ~10 min |
| ED Surge | LOW (volume only) | ~5 min |
| Network-only (3 scenarios) | NONE on Epic | ~5 min |
| MyChart Peak | LOW (activity increase) | ~5 min |
| Normal Day Shift | BASELINE | N/A |


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

## Correlated Scenarios

Toggle scenarios via the Web UI to inject anomaly events across **both** generators simultaneously.
v2.3.0 consolidated to 4 focused scenarios, each turning a different DT app page RED:

| Scenario | DT App Page | Primary Indicators | Key Mechanism |
|-----------|------------|-------------------|---------------|
| **Ransomware Attack** | Auth, Security | Login failures spike | 4-phase kill chain: Recon → Harvest → Lateral → Exfil |
| **Insider Threat** | Security | BTG events spike | After-hours employee snooping with break-the-glass |
| **HL7 Interface Failure** | Integration | Mirth queue backup, FHIR errors, ETL failures | Network switch port error on HL7 VLAN cascades to integration engine |
| **Core Switch Failure** | Network | Device up ratio drops, CPU spikes | Core switch fails, surviving infrastructure overloaded |

### Mirth Connect Integration Engine

v2.3.0 adds synthetic Mirth Connect channel metrics (5 channels × 6 metrics each) via DT Metrics API v2.
Channels: LAB-RESULTS-IN, ADT-OUT, PHARMACY-ORDERS, RADIOLOGY-RESULTS, SCHEDULING-OUT.
During HL7 Interface Failure: queue depths climb, error rates spike, channels stop delivering.

| Scenario | Epic Events | Network Events | Key Correlation |
|----------|-------------|----------------|-----------------|
| **Normal Day Shift** | Baseline clinical activity | Baseline traffic | Time-of-day curves match |
| **ED Surge (MCI)** | 15+ simultaneous registrations, STAT orders | ED VLAN saturation, Citrix spike | ED switch utilization ↔ Epic login burst |
| **Ransomware Attack** | Failed logins → break-the-glass → mass lookup | FortiGate IPS → Palo Alto threat → C2 traffic | Satellite IP in both firewall and SIEM |
| **Epic Outage (Network Root Cause)** | Mass login failures → recovery burst | Core switch flap → Citrix VServer down | Network DOWN precedes Epic failures |
| **HL7 Interface Failure** | HL7 NACKs, queue backup, duplicate orders | Switch port CRC errors → err-disable | Zero HL7 VLAN traffic = err-disable period |
| **IoMT Device Compromise** | Unexpected FHIR API calls from device VLAN | ARP scan, port security, IPS lateral movement | Device IP (10.10.40.x) appears in both |
| **MyChart Credential Stuffing** | 500+ login failures, 8 successes, PHI export | F5 ASM brute force, Citrix overload, PA threat | External → DMZ VIP connection rate |
| **Insider Threat** | After-hours break-the-glass, VIP snooping | *None — pure audit scenario* | Behavioral anomaly only |

### Network-Only Scenarios

BGP WAN Outage, DDoS Attack, DHCP Exhaustion, DNS Failure, STP Broadcast Storm, Link Flap Storm, Firewall HA Failover, VPN Cascade Failure, Wireless AP Mass Disconnect, Ransomware Lateral Movement.

### Scenario Lifecycle
1. **Enable** via WebUI → sets `ACTIVE_SCENARIO` env var on generator deployments
2. **Generators restart** with the new scenario active → anomaly data injected alongside baseline
3. **DT app** health indicators shift from green → amber/red within 30–60 seconds
4. **Disable** via WebUI → generators restart back to baseline-only mode
5. **Recovery** — health indicators return to green within 2–3 minutes

---

## Project Structure

```
├── src/
│   ├── epic_generator/           # Epic SIEM log generator
│   │   ├── generators/           #   SIEM, Clinical, HL7, FHIR, MyChart, ETL
│   │   ├── models/               #   Patient, User, Session models
│   │   ├── outputs/              #   FileOutput, OTLPOutput (DT), API, MLLP, Syslog
│   │   ├── config/               #   Epic scenarios + reference data
│   │   └── orchestrator.py       #   Main entry point with MultiOutput fan-out
│   ├── network_generator/        # Network log generator
│   │   ├── vendors/              #   12 vendor emulators
│   │   ├── outputs/              #   DynatraceOutput, File, Syslog, HTTP, Kafka, SNMP, NetFlow
│   │   ├── protocols/            #   DHCP, DNS, NetFlow, SNMP, Wireless
│   │   ├── scenarios/            #   Scenario engine + 10 YAML playbooks
│   │   ├── core/                 #   Models, topology, clock, random utils
│   │   └── cli.py                #   Click CLI entry point
│   └── shared/                   # Cross-generator coordination
├── webui/                        # FastAPI + HTML/JS control panel
│   ├── app.py                    #   FastAPI backend (K8s API integration, RBAC)
│   ├── static/                   #   Frontend JS, CSS, walkthrough assets
│   └── templates/                #   Jinja2 HTML templates
├── config/
│   ├── hospital/                 # topology.yaml (4 sites, 22 devices) + device_profiles.yaml
│   └── scenarios/                # 8 correlated scenario JSON definitions
├── dynatrace-apps/
│   └── healthcare-health-monitoring/   # DT Platform App (React + TypeScript)
│       ├── ui/app/pages/               #   9 pages: Overview, Epic, Network, Integration,
│       │                               #            Security, MyChart, Sites, Explore, Walkthrough
│       ├── ui/app/components/          #   CampusMap, KpiCard, SiteFilter, HealthBadge,
│       │                               #   SiteCard, SectionHealth, Header
│       ├── ui/app/queries.ts           #   All DQL queries + filter functions
│       ├── ui/app/utils/               #   chartHelpers, queryHelpers (withSiteFilter)
│       ├── docs/                       #   ARCHITECTURE.md, REQUIREMENTS.md
│       └── app.config.json             #   App manifest + scopes
├── deploy/
│   ├── docker/                   # Dockerfiles + docker-compose.yaml
│   └── kubernetes/               # Kustomize: base + dev/staging/prod overlays
├── docs/
│   ├── DEMO-FLOW.md              # Step-by-step demo walkthrough
│   ├── DYNATRACE_INGESTION_ADVISORY.md  # Ingestion architecture guidance
│   ├── LESSONS-LEARNED.md        # AI skill development lessons
│   └── PROMPT-ANALYSIS.md        # Comprehensive project appendix
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
│  │ epic-generator  (v1.0.4)│─logs─→│ DT Operator              │  │
│  │ network-generator       │─metrics│ ActiveGate (routing +    │  │
│  │ webui           (v2.2.0)│       │   kubernetes-monitoring)  │  │
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
│  v1.14.3 — Auto-refresh (30s) + Tooltips                │
│                                                          │
│  Overview   ──→ Campus Map + KPIs + NetFlow animation    │
│  Epic       ──→ Login trends, audit, clinical events     │
│  Network    ──→ Device fleet, CPU/mem, honeycomb         │
│  Integration──→ HL7, FHIR health, ETL status             │
│  Security   ──→ BTG events, failed logins, compliance    │
│  MyChart    ──→ Portal login, messaging, scheduling      │
│  Sites      ──→ Per-site drill-down cards                │
│  Explore    ──→ Raw log viewer + DQL sandbox              │
│  Walkthrough──→ Guided demo steps                        │
│                                                          │
│  All pages: SectionHealth (30s auto-refresh, tooltips)   │
│  Site filter toolbar, gapPolicy="connect"                │
│  Data source: DQL queries against Grail (useDql hook)    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Web UI (webui v2.2.0)                                   │
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
| `vietregistry.azurecr.io/healthcare-gen/epic` | `v1.0.4` | Epic SIEM generator with anomaly injection |
| `vietregistry.azurecr.io/healthcare-gen/network` | `latest` | Network infrastructure generator |
| `vietregistry.azurecr.io/healthcare-gen/webui` | `v2.2.0` | Web UI with K8s API + demo guides |

---

## Version History

| Version | Component | Changes |
|---------|-----------|---------|
| v2.2.1 | Docs | Comprehensive 8-scenario validation, scenario test report, recovery time documentation, lessons 13-15 |
| v1.14.3 | DT App | SectionHealth auto-refresh (30s), tooltip descriptions, threshold recalibration |
| v1.14.0 | DT App | SectionHealth component, Explore raw-log viewer, Security & Compliance page |
| v1.9.0 | DT App | Anomaly injection, threshold fixes, brute-force scenario |
| v1.6.0 | DT App | Threshold-aware KPIs, detection queries |
| v1.4.8 | DT App | Canvas alignment fix, multiline timeseries filter |
| v2.2.0 | WebUI | Demo guide walkthrough system, step-by-step scenario narratives |
| v2.1.0 | WebUI | Multi-scenario race condition fix, K8s API integration |
| v1.0.4 | Epic Gen | Anomaly injection via ACTIVE_SCENARIO env var |
| v1.0.0 | All | Initial release — Epic + Network generators, DT app, WebUI |

---

## License

Internal — Dynatrace SE use only.

## SIEM Mnemonic Fields (v1.0.3+)

The Epic generator produces 30+ realistic mnemonic fields per SIEM event, matching real Epic SIEM output structure:

**Login events** (`BCA_LOGIN_SUCCESS`, `FAILEDLOGIN`):
`CLIENT_TYPE`, `LOGINERROR`, `LOGIN_CONTEXT`, `LOGIN_LDAP_ID`, `INTERNET_AREA`, `HYP_ACCESS_ID`, `REMOTE_IP`, `UID`, `LOGIN_SOURCE`

**Service audit events** (`IC_SERVICE_AUDIT`):
`SERVICECATEGORY`, `SERVICETYPE`, `SERVICENAME`, `HOSTNAME`, `INSTANCEURN`, `SERVICE_USER`, `SERVICE_USERTYP`

**Common fields**: `E1Mid`, `Action`, `Source`, `WorkstationID`, `Flag`, `EMPid`, `IP`, `CLIENTNAME`, `SYSLOG_PID`

## Sanitization

All data is synthetic and sanitized — cannot be traced to real systems:
- Employee IDs/names are generated, not from real Epic environments
- Workstation IDs follow realistic hospital patterns but are fabricated
- Service URNs are sanitized versions of real Epic API naming conventions
- IP addresses use non-routable or random ranges
- Patient names use obviously fake patterns (no real PHI)
- No real credentials, tokens, or environment identifiers in generated data

## Additional Documentation

- [Dynatrace Ingestion Advisory](docs/DYNATRACE_INGESTION_ADVISORY.md) — OpenPipeline, Grail buckets, querying
- [Architecture & Implementation Guide](docs/ARCHITECTURE.md) — Design phases, deployment modes, K8s microservices
- [Prompting Insights](docs/PROMPTING_INSIGHTS.md) — AI-assisted development analysis and lessons learned
- [Prompt Appendix](docs/PROMPT_APPENDIX.md) — Sanitized prompt log for thought-process review
- [Scenario Test Report](docs/SCENARIO-TEST-REPORT.md) — Comprehensive 8-scenario validation with recovery tracking
- [Lessons Learned](docs/LESSONS-LEARNED.md) — Patterns, pitfalls, and proven strategies from AI-assisted development
