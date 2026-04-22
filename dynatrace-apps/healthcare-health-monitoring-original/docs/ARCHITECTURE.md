# Healthcare Health Monitoring — Architecture (v1.14.3)

## Overview

A Dynatrace Platform App for monitoring healthcare infrastructure: Epic EHR,
HL7/FHIR integrations, network devices, MyChart patient portal, and security
compliance. Features auto-refreshing health indicators, interactive tooltips,
and scenario-aware anomaly detection.

## Pages

| Page | Route | Purpose |
|------|-------|---------|
| Overview | `/` | Campus map, top-level KPIs, cross-system correlation, section health |
| Epic Health | `/epic` | EHR login analytics, clinical orders, SIEM audit, STAT order rate |
| Network Health | `/network` | Device CPU/memory honeycomb, traffic, NetFlow, vendor distribution |
| Integration Health | `/integration` | HL7 delivery, FHIR API health, ETL pipeline status |
| Security & Compliance | `/security` | Break-the-glass, failed logins, after-hours audit, BTG counts |
| MyChart Portal | `/mychart` | Patient portal login, messaging, scheduling, device breakdown |
| Site View | `/sites` | Per-site drill-down with site cards |
| Explore | `/explore` | Raw log viewer (pipeline selector) + free-form DQL sandbox |
| Walkthrough | `/walkthrough` | Interactive scenario guide with step-by-step narrative |

## Key Components

### SectionHealth (`components/SectionHealth.tsx`)
Real-time health indicator with auto-refresh and tooltips.
- `query: string` — DQL query returning a single numeric value
- `label: string` — display name
- `thresholds: { green, amber }` — threshold values
- `invertThresholds?: boolean` — when true, lower values are better
- `format: "number" | "percent"` — value display format
- `description?: string` — tooltip text explaining the metric
- Auto-refreshes every 30 seconds via `useDql` `refetchInterval: 30_000`
- Tooltip shows: status, description, threshold breakdown with color indicators, current value
- Uses native `<div>` wrapper for Strato `<Tooltip>` ref forwarding

### KpiCard (`components/KpiCard.tsx`)
Reusable KPI display with color-coded health thresholds.
- `thresholds: { green, amber }` — threshold values
- `invertThresholds?: boolean` — when true, lower values are better
- `format: "number" | "percent" | "bytes"`

### Chart Helpers (`utils/chartHelpers.ts`)
- `toTimeseries(data)` — convert DQL results to Timeseries[]
- `toTimeseriesWithThresholds(data, thresholds)` — append constant-value threshold reference lines
- `toDonutData(records)` / `toBarData(records)` — format for Donut/Bar charts

### Queries (`queries.ts`)
Central DQL query repository. All queries use shared filter constants:
- `BUCKET` — `dt.system.bucket == "observe_and_troubleshoot_apps_95_days"`
- `EPIC_FILTER` — `healthcare.pipeline == "healthcare-epic"`
- `NETWORK_FILTER` — `healthcare.pipeline == "healthcare-network"`
- `NETFLOW_FILTER` — `log.source == "netflow"`

## Health Indicator Thresholds (v1.14.3)

### Higher-is-better (standard mode)
| KPI | Page(s) | Green | Amber | Critical |
|-----|---------|-------|-------|----------|
| Epic Login Success | Overview, Epic, Security | ≥65% | ≥45% | <45% |
| Auth Login Success | Auth, Security | ≥80% | ≥60% | <60% |
| FHIR API Health | Integration, Overview | ≥85% | ≥70% | <70% |
| ETL Success Rate | Integration, Overview | ≥88% | ≥70% | <70% |
| HL7 Delivery Rate | Integration | ≥95% | ≥80% | <80% |
| MyChart Login | MyChart | ≥95% | ≥80% | <80% |
| Device Up Ratio | Network | ≥95% | ≥80% | <80% |

### Lower-is-better (inverted mode)
| KPI | Page(s) | Green | Amber | Critical |
|-----|---------|-------|-------|----------|
| Avg Device CPU | Network, Overview | ≤60% | ≤80% | >80% |
| STAT Order Rate | Epic | ≤15% | ≤25% | >25% |
| BTG Total Count | Security | ≤200 | ≤400 | >400 |
| After-Hours BTG | Security | ≤50 | ≤100 | >100 |
| Failed Login Count | Auth, Security | ≤200 | ≤500 | >500 |

### Threshold Design Rationale
Thresholds are calibrated against **baseline** data patterns:
- Epic login success: ~83% baseline (includes LOGIN_BLOCKED & WPSEC_LOGIN_FAIL)
- Auth login: ~93% baseline (BCA-specific, ~7% failure rate)
- FHIR: ~90% baseline (~10% error rate in normal operations)
- ETL: ~85% baseline (RUNNING jobs excluded; SUCCESS_WITH_WARNINGS counted as success)
- BTG: ~50/hr baseline (emergency access events are normal in hospital operations)
- MyChart: Volume-based metric (100% when events flowing, 0% when not)

## Detection Capabilities

### Detection Queries
| Query | Purpose |
|-------|---------|
| `networkBySeverity` | Group network logs by severity level |
| `networkCriticalEvents` | Count critical/emergency/alert events |
| `hl7ByMessageType` | Timeseries by HL7 MSH.9 (ADT, ORM, ORU) |
| `portSecurityViolations` | Detect port security violations |
| `lateralScanDetection` | Flag hosts scanning >15 unique IPs |
| `rapidPatientAccess` | Users accessing >10 patients (insider threat) |
| `statOrderRate` | STAT order percentage (ED surge indicator) |
| `firewallEvents` | Deny/block/drop events from network logs |
| `afterHoursBtgCount` | Break-the-glass events outside 6am-10pm |
| `hl7RecentVolume` | HL7 volume in last 5 minutes |

### Timeseries Threshold Lines
Reference lines injected as constant-value series on key charts:
- **Device CPU** — Warning 70%, Critical 90%
- **Device Memory** — Warning 80%, Critical 95%
- **FHIR Response Percentiles** — SLA 500ms
- **HL7 Volume** — Minimum expected 10/interval

## Data Flow

```
Log Generators → OTLP → Dynatrace Grail
                              ↓
              DT Platform App (DQL queries, 30s refresh)
                              ↓
                    Strato UI Components
                    (SectionHealth + KpiCard + Charts)
```

## Auto-Refresh Architecture

```
useDql(query, { refetchInterval: 30_000 })
         │
         ▼
    DQL → Grail ──→ records[]
         │
         ▼
    SectionHealth component
    ├── Compute health color (green/amber/red)
    ├── Render status pill with color
    └── Tooltip (status + description + thresholds + value)
```

Each `SectionHealth` instance makes its own independent DQL query every 30 seconds.
This provides near-real-time monitoring without page reload.

## Deployment

```bash
# Local deploy (requires browser SSO)
cd /tmp/healthcare-app
npx dt-app build
npx dt-app deploy

# Sync back to VM
rsync -avz --exclude node_modules --exclude dist --exclude .dt-app \
  /tmp/healthcare-app/ \
  <user>@<vm-ip>:~/healthcare-observability-generator/dynatrace-apps/healthcare-health-monitoring/ \
  -e "ssh -i ~/.ssh/key.pem"
```

## Version History

| Version | Changes |
|---------|---------|
| 1.14.3 | SectionHealth auto-refresh (30s), tooltip descriptions, threshold recalibration |
| 1.14.0 | SectionHealth component, Explore raw-log viewer, Security & Compliance page, MyChart page |
| 1.9.0 | Anomaly injection, threshold fixes, brute-force scenario |
| 1.6.0 | Threshold-aware KPIs, detection queries, alert thresholds |
| 1.4.8 | Canvas alignment fix, multiline timeseries filter detection |
| 1.4.7 | Hub moved to Lawrence KS, removed fake netflow |
| 1.4.0 | Fixed netflow queries, wired live netflow to map |
| 1.3.0 | Site filter buttons, per-page filtering |
| 1.2.0 | SiteView drill-down, Explore page |
| 1.1.0 | Epic Health, Network Health, Integration Health pages |
| 1.0.0 | Initial app — Overview with static map, basic KPIs |
