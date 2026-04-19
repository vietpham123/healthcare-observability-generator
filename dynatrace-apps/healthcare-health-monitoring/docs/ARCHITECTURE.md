# Healthcare Health Monitoring — Architecture (v1.6.0)

## Overview

A Dynatrace Platform App for monitoring healthcare infrastructure: Epic EHR,
HL7/FHIR integrations, network devices, MyChart patient portal, and security
compliance.

## Pages

| Page | Route | Purpose |
|------|-------|---------|
| Overview | `/` | Campus map, top-level KPIs, cross-system correlation |
| Epic Health | `/epic` | EHR login analytics, clinical orders, SIEM audit events |
| Network Health | `/network` | Device CPU/memory, traffic, NetFlow, honeycomb map |
| Integration Health | `/integration` | HL7, FHIR API, ETL pipeline health |
| Security & Compliance | `/security` | Break-the-glass, failed logins, after-hours audit |
| MyChart Portal | `/mychart` | Patient portal activity, messaging, scheduling |
| Site View | `/site/:id` | Per-site drill-down with all metrics |
| Walkthrough | `/walkthrough` | Interactive scenario guide |

## Key Components

### KpiCard (`components/KpiCard.tsx`)
Reusable KPI display with color-coded health thresholds.
- `thresholds: { green, amber }` — threshold values
- `invertThresholds?: boolean` — when true, lower values are better (CPU, error rates)
- `format: "number" | "percent" | "bytes"`

### Chart Helpers (`utils/chartHelpers.ts`)
- `toTimeseries(data)` — convert DQL results to Timeseries[]
- `toTimeseriesWithThresholds(data, thresholds)` — append constant-value threshold reference lines
- `toDonutData(records)` / `toBarData(records)` — format for Donut/Bar charts

### Queries (`queries.ts`)
Central DQL query repository. All queries use shared filter constants:
- `EPIC_FILTER` — healthcare-epic pipeline
- `NETWORK_FILTER` — healthcare-network pipeline  
- `NETFLOW_FILTER` — netflow log source

## Detection Capabilities

### Threshold-Aware KPIs (v1.6.0)
| KPI | Page | Thresholds | Mode |
|-----|------|------------|------|
| Epic Login Success | Overview, Epic | green:90% amber:70% | Higher=better |
| HL7 Delivery Rate | Overview, Integration | green:95% amber:80% | Higher=better |
| FHIR API Health | Overview, Integration | green:95% amber:85% | Higher=better |
| ETL Success | Overview, Integration | green:95% amber:80% | Higher=better |
| Avg Device CPU | Overview, Network | green:60% amber:80% | **Lower=better** |
| Avg Device Memory | Network | green:70% amber:85% | **Lower=better** |
| FHIR Error Rate | Integration | green:5% amber:15% | **Lower=better** |
| Network Critical Events | Overview | green:0 amber:3 | **Lower=better** |
| Port Security Violations | Network | green:0 amber:1 | **Lower=better** |
| STAT Order % | Epic | green:15% amber:30% | **Lower=better** |
| After-Hours BTG | Security | green:2 amber:5 | **Lower=better** |
| HL7 Volume/5min | Integration | green:50 amber:10 | Higher=better |

### Timeseries Threshold Lines
Reference lines injected as constant-value series on key charts:
- **Device CPU** — Warning 70%, Critical 90%
- **Device Memory** — Warning 80%, Critical 95%
- **FHIR Response Percentiles** — SLA 500ms
- **HL7 Volume** — Minimum expected 10/interval

### Detection Queries (v1.6.0)
- `networkBySeverity` — group network logs by severity level
- `networkCriticalEvents` — count critical/emergency/alert events
- `hl7ByMessageType` — timeseries by HL7 MSH.9 (ADT, ORM, ORU)
- `portSecurityViolations` — detect port security violations
- `lateralScanDetection` — flag hosts scanning >15 unique IPs
- `rapidPatientAccess` — users accessing >10 patients (insider threat)
- `statOrderRate` — STAT order percentage (ED surge indicator)
- `firewallEvents` — deny/block/drop events from network logs
- `afterHoursBtgCount` — break-the-glass events outside 6am-10pm
- `hl7RecentVolume` — HL7 volume in last 5 minutes

## Data Flow

```
Log Generators → OTLP → Dynatrace Grail
                              ↓
              DT Platform App (DQL queries)
                              ↓
                    Strato UI Components
```

## Deployment

```bash
cd /tmp/healthcare-app
npx dt-app build
npx dt-app deploy   # Opens browser for SSO
```

Then rsync back to VM:
```bash
rsync -avz /tmp/healthcare-app/ azureuser@52.248.43.42:~/healthcare-observability-generator/dynatrace-apps/healthcare-health-monitoring/ --exclude node_modules --exclude dist
```
