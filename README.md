# Healthcare Observability Generator

Combined Epic SIEM + Network log generator for **Kansas City Regional Medical Center (KCRMC)** — a synthetic healthcare observability data platform built for Dynatrace.

## Overview

Generates temporally-correlated logs and metrics across two domains, sending data directly to Dynatrace via API:

| Generator | Data Types | Vendors/Systems | DT Transport |
|-----------|-----------|-----------------|--------------|
| **Epic SIEM** | SIEM audit, Clinical, HL7, FHIR, MyChart, ETL | Epic Hyperspace, Interconnect, Bridges, MyChart | Log Ingest API v2 |
| **Network** | Syslog, SNMP metrics, NetFlow, Traps | Cisco IOS/ASA/NX-OS, Palo Alto, FortiGate, F5, Citrix, Aruba | Log Ingest + Metrics (MINT) + Events v2 |

### Hospital Profile — Kansas City Regional Medical Center

| Site | Code | IP Range | Description |
|------|------|----------|-------------|
| **Main Campus** | `kcrmc-main` | `10.10.x.x` | 500-bed regional medical center (ED, ICU, Med-Surg, OR, L&D, etc.) |
| **Topeka Clinic** | `tpk-clinic` | `10.20.x.x` | Cardiology/Oncology + Infusion Center |
| **Wichita Clinic** | `wch-clinic` | `10.30.x.x` | Urgent Care + Family Medicine |
| **Lawrence Clinic** | `lwr-clinic` | `10.40.x.x` | Primary Care + Pediatrics Outpatient |
| **WAN Transit** | — | `172.16.0.x` | MPLS/SD-WAN interconnects |
| **Public-facing** | — | `203.0.113.x` | MyChart, Interconnect, VPN |

## Quick Start

### Local Development

```bash
pip install -r requirements.txt

# Start the Web UI
uvicorn webui.app:app --host 0.0.0.0 --port 8080
```

### Docker Compose

```bash
cd deploy/docker
# Set DT credentials for Dynatrace output
export DT_ENDPOINT="https://{your-env-id}.live.dynatrace.com"
export DT_API_TOKEN="dt0c01...."
docker compose up -d
# UI at http://localhost:8080
```

### Kubernetes (AKS)

```bash
# 1. Update deploy/kubernetes/base/configmap.yaml with your DT_ENDPOINT
# 2. Update deploy/kubernetes/base/secret.yaml with your DT_API_TOKEN
# 3. Apply:
kubectl apply -k deploy/kubernetes/overlays/dev/

# Production (higher resource limits):
kubectl apply -k deploy/kubernetes/overlays/prod/
```

## Dynatrace Integration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DT_ENDPOINT` | Yes | — | Dynatrace environment URL (e.g., `https://{id}.live.dynatrace.com`) |
| `DT_API_TOKEN` | Yes | — | API token with `logs.ingest`, `metrics.ingest`, `events.ingest` scopes |
| `EPIC_OUTPUT_MODE` | No | `file` | `file`, `dynatrace`, or `both` |
| `NETWORK_OUTPUT` | No | `file` | `file`, `dynatrace`, `both`, `syslog`, `kafka`, `http` |
| `OUTPUT_DIR` | No | `/app/output` | Directory for file-based output |
| `EPIC_TICK_INTERVAL` | No | `10` | Seconds between Epic generator ticks |
| `NETWORK_TICK_INTERVAL` | No | `60` | Seconds between network generator ticks |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

### Data Flow to Dynatrace

| Data Type | API Endpoint | Format | Segmentation Attributes |
|-----------|-------------|--------|------------------------|
| Epic SIEM logs | `/api/v2/logs/ingest` | DT Log Ingest JSON | `generator.type=epic-siem`, `dt.source.generator` |
| Network syslog/firewall | `/api/v2/logs/ingest` | DT Log Ingest JSON | `generator.type=network`, `healthcare.site` |
| SNMP/interface metrics | `/api/v2/metrics/ingest` | MINT line protocol | `healthcare.network.*` prefix, `dt.source.generator` dimension |
| SNMP traps | `/api/v2/events/ingest` | Custom events | `network.trap.severity`, `network.device` |
| NetFlow records | `/api/v2/logs/ingest` | DT Log Ingest JSON | `network.flow.*` attributes |

### Recommended DT Settings

Create these via the DT Settings API v2 or UI:

- **Management Zone**: Scope to `KUBERNETES_CLUSTER` entity for the AKS cluster
- **Auto-Tag**: `healthcare-gen` tag on `CLOUD_APPLICATION` in the `healthcare-gen` namespace
- **Log Metric**: `log.healthcare_gen.count` split by `generator.type` and `healthcare.site`
- **Log Event Rule**: Alert on `loglevel="ERROR"` from generator logs
- **Alerting Profile**: Filter to the healthcare MZ

See [docs/DYNATRACE_INGESTION_ADVISORY.md](docs/DYNATRACE_INGESTION_ADVISORY.md) for detailed ingestion architecture, OpenPipeline configuration, and Grail bucket strategy.

## Correlated Scenarios

Toggle scenarios via the Web UI to inject events across **both** generators simultaneously:

| Scenario | Epic Events | Network Events | Key Correlation |
|----------|-------------|----------------|-----------------|
| **Normal Day Shift** | Baseline clinical activity | Baseline traffic | Time-of-day curves match |
| **ED Surge (MCI)** | 15+ simultaneous registrations, STAT orders | ED VLAN saturation, Citrix spike | ED switch utilization ↔ Epic login burst |
| **Ransomware Attack** | Failed logins → break-the-glass → mass lookup | FortiGate IPS → Palo Alto threat → C2 traffic | Satellite IP in both firewall and SIEM |
| **Epic Outage (Network Root Cause)** | Mass login failures → recovery burst | Core switch flap → Citrix VServer down → F5 pool down | Network DOWN precedes Epic failures |
| **HL7 Interface Failure** | HL7 NACKs, queue backup, duplicate orders | Switch port CRC errors → err-disable | Zero HL7 VLAN traffic = err-disable period |
| **IoMT Device Compromise** | Unexpected FHIR API calls from device VLAN | ARP scan, port security, IPS lateral movement | Device IP (10.10.40.x) appears in both |
| **MyChart Credential Stuffing** | 500+ login failures, 8 successes, PHI export | F5 ASM brute force, Citrix overload, PA threat | External → DMZ VIP connection rate |
| **Insider Threat** | After-hours break-the-glass, VIP snooping | *None — pure audit scenario* | Behavioral anomaly only |

### Network-Only Scenarios

| Scenario | Events | Impact |
|----------|--------|--------|
| BGP WAN Outage | BGP peer down, route withdrawal | Site isolation |
| DDoS Attack | SYN flood, connection table exhaustion | Firewall/LB overload |
| DHCP Exhaustion | Pool depletion, NAK storms | New devices can't join |
| DNS Failure | Recursive failure, cache poisoning | Application timeouts |
| STP Broadcast Storm | Topology change, root bridge election | Network loops |
| Link Flap Storm | Interface bouncing, OSPF recalculation | Intermittent connectivity |
| Firewall HA Failover | Primary failure, standby takeover | Brief traffic drop |
| VPN Cascade Failure | Tunnel collapse, crypto errors | Remote site disconnection |
| Wireless AP Mass Disconnect | AP disassociation, rogue detection | Wireless outage |
| Ransomware Lateral Movement | Internal scanning, SMB/RDP lateral | Progressive host compromise |

## Project Structure

```
├── src/
│   ├── epic_generator/           # Epic SIEM log generator
│   │   ├── generators/           #   SIEM, Clinical, HL7, FHIR, MyChart, ETL generators
│   │   ├── models/               #   Patient, User, Session models
│   │   ├── outputs/              #   FileOutput, OTLPOutput (DT), API, MLLP, Syslog
│   │   ├── config/               #   Epic scenarios + reference data
│   │   └── orchestrator.py       #   Main entry point with MultiOutput fan-out
│   ├── network_generator/        # Network log generator
│   │   ├── vendors/              #   12 vendor emulators (Cisco, Palo Alto, FortiGate, etc.)
│   │   ├── outputs/              #   DynatraceOutput, File, Syslog, HTTP, Kafka, SNMP, NetFlow
│   │   ├── protocols/            #   DHCP, DNS, NetFlow, SNMP, Wireless generators
│   │   ├── scenarios/            #   Scenario engine + 10 YAML playbooks
│   │   ├── snmpagent/            #   SNMP agent simulator with MIB profiles
│   │   ├── core/                 #   Models, topology, clock, random utils
│   │   └── cli.py                #   Click CLI entry point
│   └── shared/                   # Cross-generator coordination
├── webui/                        # FastAPI + HTML/JS control panel
├── config/
│   ├── hospital/
│   │   ├── topology.yaml         #   22-device network topology across 4 sites
│   │   └── device_profiles.yaml  #   Hardware profiles per vendor/role
│   └── scenarios/                #   Cross-generator scenario configs (8 scenarios)
├── deploy/
│   ├── docker/                   # Dockerfiles + docker-compose.yaml
│   └── kubernetes/               # Kustomize: base + dev/staging/prod overlays
├── docs/                         # Ingestion advisory, architecture
├── pyproject.toml
└── requirements.txt
```

## IP Scheme

| Range | Purpose | VLAN |
|-------|---------|------|
| `10.10.10.x` | Epic App Tier | 10 |
| `10.10.20.x` | Clinical Workstations | 20 |
| `10.10.25.x` | ED Workstations | 25 |
| `10.10.30.x` | HL7 Interface Engines | 30 |
| `10.10.40.x` | IoMT / Medical Devices | 40 |
| `10.10.50.x` | DMZ (MyChart, VPN) | 50 |
| `10.10.60.x` | Radiology / PACS | 60 |
| `10.10.90.x` | Server Infrastructure | 90 |
| `10.20.x.x` | Topeka Clinic | per-VLAN |
| `10.30.x.x` | Wichita Clinic | per-VLAN |
| `10.40.x.x` | Lawrence Clinic | per-VLAN |

## Deployment Architecture (AKS)

The recommended deployment is on AKS with Dynatrace Operator for K8s monitoring:

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
```

- **No OneAgent injection** — generators send data directly to DT APIs
- **Operator + ActiveGate** provides kubernetes-monitoring (cluster/node/pod/container entities) and API routing
- All generator pods read `DT_ENDPOINT` and `DT_API_TOKEN` from a ConfigMap + Secret

## License

Internal — Dynatrace SE use only.
