# Healthcare Observability Generator

Combined Epic SIEM + Network log generator for **Kansas City Regional Medical Center (KCRMC)** — a synthetic healthcare observability data platform built for Dynatrace.

## Overview

Generates temporally-correlated logs across two domains:

| Generator | Data Types | Vendors/Systems |
|-----------|-----------|-----------------|
| **Epic SIEM** | SIEM audit, Clinical, HL7, FHIR, MyChart, ETL | Epic Hyperspace, Interconnect, Bridges, MyChart |
| **Network** | Syslog, SNMP, NetFlow, Traps | Cisco IOS/ASA/NX-OS, Palo Alto, FortiGate, F5, Citrix, Aruba |

### Hospital Profile — Kansas City Regional Medical Center

- **Main Campus** (`kcrmc-main`, `10.10.x.x`) — 500-bed regional medical center
  - ED, ICU, Med-Surg, OR, L&D, Pediatrics, Cardiology, Oncology, Radiology, Lab, Pharmacy
- **Topeka Clinic** (`tpk-clinic`, `10.20.x.x`) — Cardiology/Oncology + Infusion Center
- **Wichita Clinic** (`wch-clinic`, `10.30.x.x`) — Urgent Care + Family Medicine
- **Lawrence Clinic** (`lwr-clinic`, `10.40.x.x`) — Primary Care + Pediatrics Outpatient
- **WAN Transit** (`172.16.0.x`) — MPLS/SD-WAN interconnects
- **Public-facing** (`203.0.113.x`) — MyChart, Interconnect, VPN

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Start the Web UI
uvicorn webui.app:app --host 0.0.0.0 --port 8080

# Open http://localhost:8080
```

### Docker Compose

```bash
cd deploy/docker
docker compose up -d
# UI at http://localhost:8080
```

### Kubernetes (AKS)

```bash
# Dev
kubectl apply -k deploy/kubernetes/overlays/dev/

# Production
kubectl apply -k deploy/kubernetes/overlays/prod/
```

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

## Project Structure

```
├── src/
│   ├── epic_generator/      # Epic SIEM log generator
│   ├── network_generator/   # Network log generator
│   └── shared/              # Coordination layer
├── webui/                   # FastAPI + HTML/JS control panel
├── config/
│   ├── hospital/topology.yaml  # Full network topology (24 devices)
│   └── scenarios/              # Cross-generator scenario configs
├── deploy/
│   ├── docker/              # Dockerfiles + compose
│   └── kubernetes/          # Kustomize base + overlays
└── docs/                    # MRD, URD, build guide
```

## IP Scheme (Strategic for Dynatrace Anomaly Detection)

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
| `10.20.x.x` | Satellite West | per-VLAN |
| `10.30.x.x` | Satellite North | per-VLAN |
| `10.40.x.x` | Satellite South | per-VLAN |

## Dynatrace Integration

Configure via environment variables:

```bash
export DT_ENDPOINT="https://{id}.live.dynatrace.com"
export DT_API_TOKEN="dt0c01...."
```

Supported outputs: Log Ingest API, Metrics (MINT), Events v2, Bizevents, Syslog, SNMP, NetFlow.

> **Note:** Do not build OpenPipelines, dashboards, or other Dynatrace assets — this project focuses solely on the generator and proper configuration.

## License

Internal — Dynatrace SE use only.
