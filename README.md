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

### Why 78% Is the Right Number (and 90% Isn't Worth It)

The generator scores **78% overall realism** — and that is a deliberate engineering decision, not a shortcoming. Here's the core argument:

**The last 12% lives in areas your audience doesn't care about.** The two weakest dimensions — event volume ratios (55%) and clinical content coherence (implied in HL7/FHIR) — only matter to clinical informaticists and Clarity DBAs. Neither group is in the room when a hospital CTO decides to buy Dynatrace. For the actual buyer audience, effective accuracy is **85-90%**.

**Getting to 90% has terrible ROI:**

| Gap to Close | Effort | Benefit to Demo | Verdict |
|-------------|--------|-----------------|---------|
| Clinically coherent HL7/FHIR (ICD-10 → CPT → medication chains) | **Massive** — requires a medical knowledge base, drug interaction tables, and a clinical state machine | Zero for security/ops audiences; marginal for clinical informatics demos | Not worth it |
| Realistic event volume ratios (millions/day) | **Moderate** code change, but **expensive** — 10-50× DT ingest cost increase | Slightly more realistic dashboards, but same patterns at any scale | Not worth it for a demo environment |
| Larger device topology (100-500 devices) | **Low** effort — config file expansion | Marginally more impressive; same architecture demonstrated with 29 | Nice-to-have, easy win |
| ETL batch timing (hourly Clarity runs) | **Low** effort — scheduling change | Minor realism gain; current continuous flow better for live demos | Counterproductive — demo windows are 30-60 min |
| FHIR resource-level OpenPipeline extraction | **Low** effort — pipeline config update | Enables deeper FHIR drill-down in the app | Worth doing |

**The bottom line**: Two of the five gaps are actively counterproductive for live demos (higher volume = higher cost; batch ETL = dead air during the demo). The clinical coherence gap requires a medical domain engine that has nothing to do with Dynatrace's value proposition.

### The Real Selling Points (What 78% Gets You)

The generator is purpose-built for a specific sales motion: **"Dynatrace can be the single pane of glass for healthcare IT operations."** Every design choice optimizes for that message:

| Design Choice | Why It's Built This Way | Customer Impact |
|---------------|------------------------|-----------------|
| **Real DT APIs** (Log Ingest v2, MINT, Events v2) | Customer cannot dismiss this as a mockup. "This is how your data would actually flow." | Eliminates the "but can it really ingest our data?" objection |
| **Cross-system correlation** (Epic + Network + HL7 + FHIR in one view) | Most hospitals run Splunk for SIEM, SolarWinds for network, Mirth dashboard for HL7 — three separate panes. Unified view is genuinely novel. | The single strongest demo moment. "You've never seen these together before." |
| **OpenPipeline field extraction** | Shows DT can parse proprietary Epic XML, HL7 segments, and vendor-specific syslog without custom code — just pipeline config. | Positions DT as operationally lightweight vs competitors that need agents everywhere |
| **Vendor-specific network syslog** (7 vendors, 40+ templates) | Hospital network architects immediately recognize their own vendor's log format. Builds instant credibility. | "You already know what a Palo Alto threat log looks like. Here it is in Dynatrace." |
| **Scenario-driven storytelling** (ransomware, insider threat, HL7 failure) | Live attack simulation in a 30-min demo window. Health indicators go red in real-time. | Emotional impact. CISOs and CTOs react to watching an attack unfold, not to static dashboards. |
| **97-98% login baseline** | Matches real hospital environments exactly. When ransomware drops it to 65%, the audience feels the severity because the baseline was credible. | Anchoring effect — realistic baseline makes anomalies impactful |
| **Compressed timeline** (events every 5s vs hourly batch in production) | Live demos are 30-60 minutes. Batch latency would mean showing a static dashboard. Continuous flow keeps the audience engaged. | Intentional tradeoff: demo pacing > temporal accuracy |
| **6 sites with realistic IP addressing** | Hub-and-spoke topology mirrors real regional health systems. Per-site drill-down shows DT handles multi-site at scale. | "Each of your clinics gets its own view. Same platform, zero additional tooling." |
| **Synthetic data only** (no real PHI, no real credentials) | HIPAA-safe by design. Can be demoed anywhere, shipped to any prospect, run on any environment. | Removes the "we can't show real patient data" blocker that kills most healthcare demos |
| **Same ingestion path** as production | Every API call, every OpenPipeline rule, every DQL query would work identically on real data. Only the data source changes. | "When you're ready, swap the generator for your real Epic export. Everything else stays." |

### The Conversation This Enables

A hospital CTO watching this demo doesn't think "the ICD-10 codes don't match the CPT codes." They think:

> *"I've never seen my Epic audit trail, my Palo Alto firewall, my Mirth channels, and my network switches in one dashboard before. And you're telling me the APIs are the same ones I'd use in production? What do I need to do to get this for real?"*

The answer — which is the entire point of the demo — is: **"Get your Epic team to approve the Audit Log Export data flow. Everything else is standard Dynatrace."** That shifts the conversation from "can Dynatrace do this?" (yes, proven) to "will your organization approve the data sharing?" (a business/governance question, not a technology question).

**That conversation is worth more than 12 percentage points of clinical content accuracy.**

### 10-Factor Realism Scorecard

| # | Factor | Weight | Score | Grade | What's Right | What's Missing | Demo Impact |
|---|--------|--------|-------|-------|-------------|----------------|-------------|
| 1 | Epic Audit XML | 15% | 90% | A | `E1Mid` event types, XML envelope, 30+ `<Mnemonic>` fields — recognizable to Epic admins | Epic version-specific headers (EpicSN) | **HIGH** — this is what Epic analysts look for first |
| 2 | HL7 v2.x Messages | 10% | 85% | B+ | MSH/PID/OBR/OBX segments, correct message types (ADT^A01, ORU^R01) | Clinical content not coherent (random ICD-10 + CPT) | **MEDIUM** — structure sells; payload rarely inspected in demos |
| 3 | FHIR R4 API | 8% | 80% | B | Correct resource types, realistic endpoint patterns | `resourceType`/`fhir_endpoint` not yet extracted in OpenPipeline | **MEDIUM** — shows modern interop capability |
| 4 | Network Syslog | 15% | 92% | A | 7 vendors, correct log formats, 6 event types, 40+ templates | Could add more vendors (Juniper, Meraki) | **HIGH** — network architects recognize their own vendor instantly |
| 5 | Multi-Site Topology | 10% | 88% | B+ | 6 sites, 29 devices, proper IP per site, WAN transit, hub-and-spoke | Clinic sites have 2 devices each (real: 4-8) | **HIGH** — multi-site view is a key differentiator |
| 6 | Login & Temporal Curves | 10% | 95% | A | 97-98% baseline, diurnal volume curve, site-distributed failures | Evening MyChart peak could be more pronounced | **CRITICAL** — credible baseline makes anomalies impactful |
| 7 | Event Volume Ratios | 8% | 55% | D | Correct event types present | ~5K/hr vs millions; 85% login-dominated vs 40-50% in production | **LOW** — nobody counts events during a demo |
| 8 | Scenario Attack Patterns | 10% | 85% | B+ | 4-phase ransomware, insider BTG, HL7 cascade, core switch failure | Recovery is instant (pod restart) vs hours in reality | **CRITICAL** — scenario storytelling is the demo centerpiece |
| 9 | Cross-System Correlation | 8% | 90% | A | All 5 data types correlated by time and site; unified in one platform | Could add more cross-references (IP linkage between SIEM and firewall) | **CRITICAL** — the #1 reason a CTO would buy |
| 10 | Ingestion Pathway | 6% | 95% | A | Same DT APIs, same OpenPipeline rules; production-grade pipeline | — | **CRITICAL** — proves "this isn't a mockup" |

**Overall: 78% (raw weighted: 86.3%, expert-scrutiny-adjusted)**

### Audience-Specific Accuracy

| Audience | Effective Accuracy | What They Notice | What They Don't |
|----------|-------------------|-----------------|-----------------|
| **CTO / IT Director** | ~90% | Unified dashboard, attack scenarios, multi-site view | Event volumes, clinical content details |
| **Dynatrace SE / Pre-sales** | ~85% | Real API paths, OpenPipeline, DQL queries, scenario storytelling | — (this is their tool) |
| **CISO / Security Director** | ~85% | Ransomware kill chain, BTG audit, login analysis, compliance view | HL7/FHIR payload details |
| **Epic Analyst / Clarity DBA** | ~70% | XML structure, mnemonic fields | Random clinical combinations, compressed volume, missing EpicSN |
| **Mirth/HL7 Engineer** | ~75% | Message types, channel names, queue metrics | Volume ratios, lack of per-channel routing detail |
| **Network Architect** | ~80% | Vendor-specific syslog, topology, IP addressing | 29 devices is low for 500 beds; missing Juniper/Meraki |
| **Clinical Informaticist** | ~55% | — | Random ICD-10 + CPT pairings immediately. Frame as "synthetic test data." |

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
| SIEM XML | `EMPID` | Last hex digit: 0,1,2,a,b → kcrmc-main; 3,4,c → tpk; 5,6,d → wch; 7,8,9,e,f → lwr |
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
- [Dynatrace Assets](docs/DYNATRACE_ASSETS.md) — OpenPipeline, Davis alerts, DQL queries, deployment checklist
- [Prompting Insights](docs/PROMPTING_INSIGHTS.md) — AI-assisted development analysis

---

## License

Internal — Dynatrace SE use only.
