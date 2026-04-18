# Healthcare Observability Generator

Combined Epic SIEM + Network log generator for **Lawrence Regional Medical Center** — a synthetic healthcare observability data platform built for Dynatrace, with a companion **Dynatrace Platform App** for real-time monitoring.

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

## Dynatrace Platform App — Healthcare Health Monitoring

A custom Dynatrace platform app (`my.healthcare.health.monitoring`) v1.4.8+ provides real-time visualization of all generated data.

### App Pages

| Page | Route | Description |
|------|-------|-------------|
| **Overview** | `/` | Campus map (real Kansas geo projection), KPI cards, login health, event distribution |
| **Epic Health** | `/epic` | Login trends, clinical events, audit timelines, session analysis |
| **Network Health** | `/network` | Device fleet CPU/memory honeycomb, traffic charts, NetFlow analysis, vendor distribution |
| **Integration Health** | `/integration` | HL7 delivery rates, FHIR response times, ETL pipeline status |
| **Site View** | `/sites` | Per-site drill-down with site cards — bed count, profile, events, devices |
| **Explore** | `/explore` | Free-form DQL query explorer |

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

### Tech Stack

- `dt-app` 1.8.1, React 18, TypeScript 5.9
- Strato components: `TimeseriesChart`, `HoneycombChart`, `DonutChart`, `CategoricalBarChart`, `SingleValue`
- DQL via `@dynatrace-sdk/react-hooks` (`useDql`)
- All charts use `gapPolicy="connect"` for continuous lines

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

## Correlated Scenarios

Toggle scenarios via the Web UI to inject events across **both** generators simultaneously:

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
├── config/hospital/              # topology.yaml (4 sites, 22 devices) + device_profiles.yaml
├── dynatrace-apps/
│   └── healthcare-health-monitoring/   # DT Platform App (React + TypeScript)
│       ├── ui/app/pages/               #   6 pages: Overview, Epic, Network, Integration, Sites, Explore
│       ├── ui/app/components/          #   CampusMap, KpiCard, SiteFilter, HealthBadge, SiteCard
│       ├── ui/app/queries.ts           #   All DQL queries + filter functions
│       ├── ui/app/utils/               #   chartHelpers, queryHelpers (withSiteFilter)
│       └── app.config.json             #   App manifest + scopes
├── deploy/
│   ├── docker/                   # Dockerfiles + docker-compose.yaml
│   └── kubernetes/               # Kustomize: base + dev/staging/prod overlays
├── docs/
│   ├── DYNATRACE_INGESTION_ADVISORY.md
│   ├── LESSONS-LEARNED.md        # AI skill development lessons
│   └── DEMO-FLOW.md              # Step-by-step demo walkthrough
└── requirements.txt
```

## Deployment Architecture (AKS)

```
┌──────────────────────────────────────────────────────────────────┐
│ AKS Cluster (aks-healthcare-gen)                                 │
│                                                                  │
│  namespace: healthcare-gen          namespace: dynatrace          │
│  ┌─────────────────────┐           ┌──────────────────────────┐  │
│  │ epic-generator      │──logs──→  │ DT Operator              │  │
│  │ network-generator   │──metrics→ │ ActiveGate (routing +    │  │
│  │ webui               │           │   kubernetes-monitoring)  │  │
│  └─────────────────────┘           └──────────────────────────┘  │
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
│                                                          │
│  Overview ──→ Campus Map + KPIs + NetFlow animation      │
│  Epic     ──→ Login trends, audit, clinical events       │
│  Network  ──→ Device fleet, CPU/mem, traffic, honeycomb  │
│  Integr.  ──→ HL7 delivery, FHIR health, ETL status     │
│  Sites    ──→ Per-site drill-down cards                  │
│  Explore  ──→ Free-form DQL                              │
│                                                          │
│  All pages: site filter toolbar, gapPolicy="connect"     │
│  Data source: DQL queries against Grail (useDql hook)    │
└─────────────────────────────────────────────────────────┘
```

## License

Internal — Dynatrace SE use only.
