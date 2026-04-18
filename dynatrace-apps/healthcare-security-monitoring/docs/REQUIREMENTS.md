# Healthcare Security Monitoring — Dynatrace App Requirements

**Date:** April 17, 2026
**Version:** 1.0
**Status:** Draft
**App ID:** `my.healthcare.security.monitoring`
**Reference:** Network Insights App v1.4.0 (pattern & architecture baseline)

---

## 1. Purpose

This document defines the requirements for a Dynatrace Platform App that leverages **Epic EHR telemetry** and **network infrastructure data** together to monitor, detect, and investigate security risks across a healthcare environment. The app correlates clinical system audit logs with network traffic patterns to surface threats that neither data source can reveal alone.

The design follows the proven patterns established by the **Network Insights App** — specifically its page architecture (Overview → domain-specific pages → Explore), shared `queries.ts` module, `DqlQueryParamsProvider` for app-wide time control, Strato component usage, and `useDql` hook integration.

---

## 2. Scope

### In Scope

- Real-time security monitoring dashboard combining Epic SIEM + network data
- Anomaly detection configuration leveraging Davis AI (static thresholds, auto-adaptive baselines, seasonal patterns)
- Problem creation for security incidents via metric events
- Cross-correlation of Epic user activity with network traffic patterns
- Threat scenario detection (ransomware, credential stuffing, insider threat, IoMT compromise)
- DQL-based exploration with healthcare security presets

### Out of Scope

- Building OpenPipeline configurations (data assumed pre-parsed)
- Modifying the log generators themselves
- Patient-facing features or PHI display
- SIEM replacement — this is an observability/analytics layer

---

## 3. Data Sources

### 3.1 Epic EHR Telemetry (via `generator.type == "epic-siem"`)

| Log Type | Key Security Fields | Use Case |
|----------|-------------------|----------|
| **SIEM Audit** | `E1Mid`, `EMPid`, `Action`, `IP`, `Flag`, `WorkstationID` | Failed logins, break-the-glass access, privilege escalation |
| **Clinical Events** | `ORDER_TYPE`, `MEDICATION_NAME`, `NOTE_TYPE`, `PROVIDER_ID` | Unauthorized order placement, chart snooping |
| **HL7v2 Messages** | `MSH.9` (message type), `PID.3` (MRN), `PV1.2` (patient class) | Interface abuse, mass data exfiltration attempts |
| **FHIR API Logs** | `method`, `path`, `status`, `client_id`, `category` | API abuse, unauthorized app access, brute-force token requests |
| **MyChart Activity** | `session_id`, `patient_portal_action`, `device_type` | Credential stuffing, account takeover |
| **ETL/Integration** | `job_name`, `source_system`, `records_processed` | Unusual bulk data exports, off-hours integration runs |

### 3.2 Network Infrastructure Telemetry (via `generator.type == "network"`)

| Data Type | Key Security Fields | Use Case |
|-----------|-------------------|----------|
| **Syslog (firewall)** | `network.firewall.action`, `network.firewall.rule`, `src_ip`, `dst_ip` | Blocked connections, deny rule triggers, C2 traffic |
| **IPS/IDS Events** | `network.ips.action`, `network.ips.classification`, `network.ips.impact_level` | Intrusion detection, exploit attempts |
| **IOC Events** | `network.ioc.type`, `network.ioc.value`, `network.ioc.confidence` | Indicator of compromise correlation |
| **Malware Events** | `network.malware.name`, `network.malware.disposition` | Malware detection on network |
| **NetFlow Records** | `network.flow.src_ip`, `network.flow.dst_ip`, `network.flow.bytes`, `network.flow.dst.country` | Lateral movement, data exfiltration, geographic anomalies |
| **SNMP Traps** | `trap_oid`, `trap_name`, `severity` | Unauthorized device changes, link manipulation |

### 3.3 Hospital Sites (Kansas City Geography)

| Site | Code | IP Range | Context |
|------|------|----------|---------|
| Main Campus | `kcrmc-main` | `10.10.x.x` | Primary data center, highest traffic |
| Topeka Clinic | `tpk-clinic` | `10.20.x.x` | Remote clinic |
| Wichita Clinic | `wch-clinic` | `10.30.x.x` | Remote clinic |
| Lawrence Clinic | `lwr-clinic` | `10.40.x.x` | Remote clinic |

---

## 4. App Architecture

### 4.1 Technology Stack (matching Network Insights App pattern)

| Component | Technology | Version |
|-----------|-----------|---------|
| Runtime | Dynatrace AppEngine | — |
| UI Framework | React + TypeScript | 18.x / 5.x |
| Design System | Strato Components | 3.x |
| Data Access | `@dynatrace-sdk/react-hooks` (`useDql`) | 1.6+ |
| Query Language | DQL against Grail | — |
| Routing | `react-router-dom` | 6.x |
| Time Control | `DqlQueryParamsProvider` + `TimeframeSelector` | — |
| Charts | `@dynatrace/strato-components-preview/charts` | 3.x |
| Tables | `@dynatrace/strato-components-preview/tables` (`DataTable`) | 3.x |

### 4.2 App Permissions (app.config.json scopes)

```json
{
  "scopes": [
    { "name": "storage:logs:read", "comment": "Query Epic SIEM and network logs from Grail" },
    { "name": "storage:buckets:read", "comment": "Read log buckets" },
    { "name": "storage:metrics:read", "comment": "Read extracted metrics for anomaly baselines" },
    { "name": "storage:bizevents:read", "comment": "Query enrichment bizevents (threat intel)" },
    { "name": "storage:events:read", "comment": "Read Davis problems and events" },
    { "name": "davis:problems:read", "comment": "Display auto-detected security problems" }
  ]
}
```

### 4.3 File Structure

```
healthcare-security-monitoring/
├── app.config.json
├── package.json
├── tsconfig.json
├── ui/
│   ├── main.tsx
│   ├── app/
│   │   ├── App.tsx                    ← Routes + DqlQueryParamsProvider
│   │   ├── queries.ts                 ← All DQL queries (shared module)
│   │   ├── components/
│   │   │   ├── Header.tsx             ← AppHeader with nav + TimeframeSelector
│   │   │   ├── KpiCard.tsx            ← Reusable SingleValue card
│   │   │   ├── SeverityBadge.tsx      ← Color-coded severity indicator
│   │   │   └── ThreatScoreRing.tsx    ← Circular threat confidence visual
│   │   └── pages/
│   │       ├── Overview.tsx           ← Security posture dashboard
│   │       ├── AccessMonitoring.tsx   ← Epic login/access analysis
│   │       ├── NetworkThreats.tsx     ← Firewall/IPS/IOC/malware
│   │       ├── CrossCorrelation.tsx   ← Epic ↔ network joint analysis
│   │       ├── Incidents.tsx          ← Davis problems + active incidents
│   │       └── Explore.tsx            ← DQL editor with security presets
```

---

## 5. Page Requirements

### 5.1 Overview — Security Posture Dashboard

**Route:** `/`
**Purpose:** Single-pane security health view combining both data sources.
**Reference pattern:** Network Insights `Overview.tsx` (KPI row → chart row → distribution)

#### KPI Cards (top row)

| KPI | DQL Source | Field |
|-----|-----------|-------|
| Total Security Events | Epic SIEM audit events with `Flag != ""` + network `security.event_type` events | `count()` |
| Failed Logins (24h) | Epic SIEM where `Action == "Login Failed"` | `count()` |
| Firewall Denies | Network logs where `network.firewall.action in ("denied","deny","drop")` | `count()` |
| Active IPS Alerts | Network logs where `network.ips.action` is not null | `count()` |
| Suspicious NetFlow | NetFlow to non-US destinations or high-volume single-source | `count()` |
| Open Incidents | `fetch dt.davis.problems \| filter event.status == "ACTIVE"` | `count()` |

#### Visualizations

| Chart | Type | Data |
|-------|------|------|
| Security Events Timeline | `TimeseriesChart` (area, stacked) | Epic security events + network security events by source, 5m bins |
| Threat Category Distribution | `PieChart` | `network.security.event_type` + Epic `Flag` values |
| Top Blocked Source IPs | `CategoricalBarChart` (horizontal) | `src_ip` from firewall denies, top 15 |
| Geographic Threat Map | Custom SVG (from Network Insights `ConnectionMapSVG` pattern) | NetFlow foreign destinations + connection arcs |
| Site Security Score | `CategoricalBarChart` | Composite score per `healthcare.site` combining deny rate + failed logins + IPS hits |

#### Anomaly Indicators

- **Seasonal baseline comparison:** Show current failed-login rate vs. same day-of-week/hour baseline
- **Deviation badge:** Green/amber/red indicator when current rate exceeds 2σ/3σ of historical baseline

---

### 5.2 Access Monitoring — Epic Login & Authorization Analysis

**Route:** `/access`
**Purpose:** Deep dive into Epic EHR access patterns — the clinical side of security.

#### Sections

**A. Authentication Overview**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Login Success vs. Failure Over Time | `TimeseriesChart` | `makeTimeseries` on Epic SIEM logs, split by `Action` (success/fail), 5m interval |
| Failed Login Heatmap by Hour | `CategoricalBarChart` | `summarize` failed logins by `getHour(timestamp)`, grouped by day-of-week |
| Top Failed Login Users | `DataTable` | `summarize count(), by: {EMPid, IP}` where `Action == "Login Failed"`, top 20 |
| Brute Force Detection | `DataTable` + alert badge | Users with >5 failed logins in 10min window |

**B. Authorization & Privilege Events**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Break-the-Glass Access | `DataTable` (highlighted rows) | Epic SIEM where `Flag == "BTG"` or `Action` contains "break" |
| Privilege Escalation | `DataTable` | Epic SIEM where `Action` contains "role change" or "permission grant" |
| After-Hours Access | `TimeseriesChart` | Epic logins outside 6AM-8PM local time, by `EMPid` |
| VIP Patient Access | `DataTable` | Epic SIEM access to flagged patient records |

**C. Seasonal Patterns**
| Insight | Method |
|---------|--------|
| Normal login volume by shift | Davis auto-adaptive baseline on `epic.login.count` metric |
| Day-of-week login patterns | Seasonal baseline comparison (current vs. 4-week average for same weekday) |
| Holiday/weekend anomalies | Static threshold alert when weekend login rate exceeds 150% of baseline |

---

### 5.3 Network Threats — Firewall, IPS, IOC, Malware

**Route:** `/threats`
**Purpose:** Network-side security analysis.
**Reference pattern:** Network Insights `Firewall.tsx` sections (Connection & Traffic → IPS → File Events → Malware → IOC → Detail Table)

#### Sections (mirroring Network Insights Firewall page structure)

**A. Firewall & Connection Security**
- Firewall action distribution (PieChart)
- Connection events over time (TimeseriesChart, area)
- Top blocked IPs (CategoricalBarChart)
- Top triggered deny rules (DataTable)

**B. Intrusion Prevention (IPS)**
- IPS events by impact level (PieChart)
- IPS blocked vs. allowed (CategoricalBarChart)
- IPS events over time (TimeseriesChart)
- IPS by classification (DataTable)

**C. Indicators of Compromise (IOC)**
- IOC by type and category (CategoricalBarChart)
- IOC confidence distribution (PieChart)
- IOC detail table with threat intel enrichment (DataTable)

**D. Malware Detection**
- Malware events by disposition (PieChart)
- Malware over time (TimeseriesChart)
- Malware names and actions (DataTable)

**E. Security Severity Overview**
- Events by severity (CategoricalBarChart)
- Events by classification (DataTable, top 15)

#### Anomaly Detection Integration

| Metric | Strategy | Threshold |
|--------|----------|-----------|
| `network.firewall.deny.rate` | Auto-adaptive | Alert when deny rate exceeds learned baseline by 3σ |
| `network.ips.event.count` | Static | Alert when IPS events > 50/5min |
| `network.ioc.high_confidence.count` | Static | Alert when high-confidence IOCs > 0 |
| `network.malware.detected.count` | Static | Alert immediately on any malware detection |

---

### 5.4 Cross-Correlation — Epic ↔ Network Joint Analysis

**Route:** `/correlation`
**Purpose:** The differentiating page — combines Epic and network data to find threats invisible to either source alone.

#### Correlation Scenarios

**A. Failed Login + Network Anomaly**
| Detection | Method |
|-----------|--------|
| Epic failed logins from IPs also seen in firewall denies | Join Epic SIEM `IP` field with network `src_ip` on firewall deny logs |
| Credential stuffing: many failed logins from same IP + high NetFlow volume | Correlate Epic failed-login IP count with NetFlow bytes from same source |
| Geographic mismatch: user logs in from IP geolocated far from normal | Compare Epic login `IP` geolocation with user's historical login locations |

**B. Insider Threat Detection**
| Detection | Method |
|-----------|--------|
| After-hours Epic access + unusual network traffic | Epic logins outside normal shift hours correlated with same-user workstation network activity |
| Bulk record access + large outbound data transfer | Epic SIEM high record-access count joined with NetFlow large outbound bytes from same subnet |
| Break-the-glass access + data exfiltration | BTG access events followed by outbound traffic to external IPs within 30min window |

**C. Ransomware Indicators**
| Detection | Method |
|-----------|--------|
| Network lateral movement + Epic system errors | NetFlow showing scanning patterns (many dst_ports from single src_ip) + Epic ETL job failures |
| C2 communication + Epic service degradation | Firewall logs showing outbound to known-bad IPs + Epic FHIR API response time increase |
| Encrypted traffic spike + HL7 interface failures | NetFlow byte volume spike with high entropy + HL7 message delivery failures |

**D. IoMT Device Compromise**
| Detection | Method |
|-----------|--------|
| Medical device IP in network threat events | Network IPS/IOC events with `src_ip` in medical device subnet (e.g., `10.x.50.x`) + Epic device integration errors |

#### Visualizations

| Chart | Type | Description |
|-------|------|-------------|
| Correlation Timeline | `TimeseriesChart` (dual-axis) | Epic security events (left axis) overlaid with network threat events (right axis) |
| Threat Actor Table | `DataTable` | IPs appearing in both Epic failed logins AND network deny/IPS events, with combined hit count |
| Attack Chain Diagram | Custom SVG | Visual flow: Initial Access → Lateral Movement → Privilege Escalation → Data Exfiltration, annotated with detected events |
| Risk Score by Site | `CategoricalBarChart` | Per-site composite risk score combining all correlation signals |

---

### 5.5 Incidents — Davis Problems & Active Alerts

**Route:** `/incidents`
**Purpose:** Display Davis AI-detected problems and custom metric event alerts.

#### Sections

**A. Active Problems**
```dql
fetch dt.davis.problems
| filter event.status == "ACTIVE"
| fields event.name, event.status, event.category, event.start, 
         management_zone, affected_entity
| sort event.start desc
```

**B. Problem Timeline**
- `TimeseriesChart` showing problem open/close events over time
- Categorized by `event.category` (AVAILABILITY, ERROR, RESOURCE, CUSTOM)

**C. Custom Metric Events (to be configured)**

| Metric Event Name | Metric Selector | Strategy | Condition |
|-------------------|----------------|----------|-----------|
| Epic Failed Login Spike | `epic.siem.failed_login.count` | Seasonal baseline | Deviation > 3σ from same-weekday/hour average |
| Firewall Deny Storm | `network.firewall.deny.count:splitBy("healthcare.site")` | Auto-adaptive | Exceeds learned per-site baseline |
| After-Hours Epic Access | `epic.siem.login.count` filtered to 20:00-06:00 | Static | > 10 logins between 8PM-6AM |
| Ransomware Lateral Movement | `network.flow.unique_dst_ports:splitBy("network.flow.src_ip")` | Static | > 100 unique dst_ports from single src_ip in 5min |
| IPS Critical Alert | `network.ips.event.count:filter(eq("network.ips.impact_level","critical"))` | Static | > 0 |
| Mass Record Access | `epic.siem.record_access.count:splitBy("EMPid")` | Auto-adaptive | Single user exceeds 3σ of their normal access pattern |
| Data Exfiltration Signal | `network.flow.outbound.bytes:splitBy("healthcare.site")` | Seasonal baseline | Outbound volume exceeds seasonal norm by 2σ |

**D. Seasonality Configuration**

| Pattern | Baseline Window | Season Length | Alert Sensitivity |
|---------|----------------|---------------|-------------------|
| Daily login pattern | 14 days | 24 hours | Medium (2σ) |
| Weekly shift pattern | 8 weeks | 7 days | Medium (2σ) |
| Monthly compliance cycle | 6 months | 30 days | Low (3σ) |

---

### 5.6 Explore — DQL Editor with Security Presets

**Route:** `/explore`
**Purpose:** Free-form DQL exploration with healthcare security-focused preset queries.
**Reference pattern:** Network Insights `Data.tsx` (DQLEditor + preset buttons + table/chart output)

#### Preset Queries

| Label | Query Summary |
|-------|--------------|
| All Epic Security Events | Epic SIEM logs with non-empty `Flag` |
| Failed Logins | Epic SIEM where `Action == "Login Failed"` |
| Break-the-Glass Access | Epic SIEM where `Flag == "BTG"` |
| Epic + Network IP Overlap | Join Epic SIEM IPs with network security IPs |
| Firewall Denies | Network logs with deny/drop actions |
| IPS Alerts | Network IPS events with classification |
| IOC Matches | Network IOC events with confidence scores |
| Malware Detections | Network malware events |
| NetFlow to Foreign Countries | NetFlow with non-US destinations |
| After-Hours Activity | Epic logins outside 6AM-8PM |
| Top Threat IPs | Combined Epic + network threat source IPs |
| SNMP Device Health | SNMP poll logs with device metrics |
| Davis Security Problems | `fetch dt.davis.problems` filtered to security-related |
| Security Events Timeline | Time-binned count of all security events |

---

## 6. Cross-Data Correlation Strategy

### 6.1 Join Patterns

The core differentiator is correlating Epic and network data. Key join strategies:

```
Epic SIEM IP ←→ Network src_ip / dst_ip
  - Failed login source IP appears in firewall deny logs
  - User workstation IP appears in IPS alert logs

Epic Timestamp ←→ Network Timestamp (±window)
  - BTG access followed by large outbound transfer within 30min
  - Epic ETL failure coinciding with network interface flap

Epic Site (healthcare.site) ←→ Network Site (healthcare.site)
  - Site-level risk scoring combining both signal sources
  - Outage impact correlation per facility

Epic User (EMPid) ←→ Network User (via IP/workstation mapping)
  - User behavior profiling across both domains
```

### 6.2 DQL Correlation Examples

**Failed Login + Firewall Deny Correlation:**
```dql
fetch logs
| filter generator.type == "epic-siem" AND Action == "Login Failed"
| summarize epic_fails = count(), by: { ip = IP }
| join [
    fetch logs
    | filter isNotNull(network.firewall.action) 
      AND (network.firewall.action == "deny" OR network.firewall.action == "drop")
    | summarize net_denies = count(), by: { ip = src_ip }
  ], on: { ip }, kind: inner
| fieldsAdd combined_risk = epic_fails + net_denies
| sort combined_risk desc
| limit 20
```

**After-Hours Access + Outbound Data:**
```dql
fetch logs
| filter generator.type == "epic-siem" AND isNotNull(Action)
| filter getHour(timestamp) < 6 OR getHour(timestamp) >= 20
| summarize after_hours_events = count(), by: { site = healthcare.site }
| join [
    fetch logs
    | filter log.source == "netflow"
    | filter getHour(timestamp) < 6 OR getHour(timestamp) >= 20
    | summarize outbound_bytes = sum(toDouble(network.flow.bytes)), by: { site = healthcare.site }
  ], on: { site }, kind: inner
| sort outbound_bytes desc
```

---

## 7. Anomaly Detection & Seasonality Requirements

### 7.1 Davis AI Integration Points

| Capability | How Used |
|-----------|----------|
| **Static thresholds** | Immediate alerts: any malware detection, any critical IPS hit, >100 port scan in 5min |
| **Auto-adaptive baselines** | Per-site, per-metric learned baselines: firewall deny rate, login failure rate, NetFlow volume |
| **Seasonal baselines** | Weekly shift-pattern awareness: Mon-Fri 7AM-7PM = high activity normal; weekends/nights = low baseline |
| **Metric events** | Custom events on extracted metrics triggering Davis problems |
| **Problem correlation** | Davis groups related metric events into single problem (e.g., "Site security degradation") |

### 7.2 Metrics to Extract (via OpenPipeline or generator attributes)

| Metric Key | Source | Dimensions | Purpose |
|-----------|--------|------------|---------|
| `epic.siem.login.count` | Epic SIEM | `healthcare.site`, `Action` (success/fail) | Login volume baseline |
| `epic.siem.btg.count` | Epic SIEM | `healthcare.site` | Break-the-glass frequency |
| `epic.siem.record_access.count` | Epic SIEM | `EMPid`, `healthcare.site` | Per-user access volume |
| `epic.fhir.request.count` | Epic FHIR | `method`, `status`, `client_id` | API usage baseline |
| `epic.mychart.session.count` | Epic MyChart | `healthcare.site`, `device_type` | Portal usage baseline |
| `network.firewall.deny.count` | Network syslog | `healthcare.site`, `network.firewall.rule` | Deny rate baseline |
| `network.ips.event.count` | Network IPS | `healthcare.site`, `network.ips.impact_level` | IPS alert volume |
| `network.flow.outbound.bytes` | NetFlow | `healthcare.site`, `network.flow.dst.country` | Egress traffic baseline |

### 7.3 Seasonality Patterns to Detect

| Pattern | Cycle | Expected Shape | Anomaly Example |
|---------|-------|---------------|-----------------|
| Clinical shift pattern | 24h | Peak at 7AM-7PM (day shift), trough 11PM-5AM | Login spike at 2AM on Tuesday |
| Weekend reduction | 7d | Mon-Fri 100%, Sat 30%, Sun 20% | Sunday volume equal to Monday |
| End-of-month billing | 30d | Spike last 3 days of month (billing cycle) | Large ETL runs mid-month |
| Holiday schedule | Annual | Reduced activity on US holidays | Full volume on Christmas Day |

---

## 8. Threat Scenarios (correlated detection requirements)

### 8.1 Ransomware Attack

| Phase | Epic Signal | Network Signal | Combined Detection |
|-------|-----------|----------------|-------------------|
| Initial Access | FHIR API brute-force (many 401s) | Firewall allows from suspicious IP | Same IP in both streams |
| Lateral Movement | — | NetFlow: single IP scanning many ports | Port scan metric > threshold |
| Privilege Escalation | Break-the-glass access, role changes | — | BTG count spike |
| Data Staging | High record access count | Large internal transfers | Volume anomaly + access anomaly |
| Exfiltration | — | Large outbound to foreign country | Outbound bytes seasonal deviation |
| Impact | ETL failures, HL7 interface errors | Interface flaps, device unreachable | Multi-signal problem creation |

### 8.2 Credential Stuffing (MyChart)

| Phase | Epic Signal | Network Signal | Combined Detection |
|-------|-----------|----------------|-------------------|
| Attack | Many MyChart login failures from varied IPs | High request rate from IP ranges | Login fail rate seasonal deviation |
| Detection | Same `session_id` pattern across failures | NetFlow volume spike to MyChart subnet | Cross-source IP correlation |
| Escalation | Successful logins post-failures | Normal traffic post-auth | Account takeover alert |

### 8.3 Insider Threat

| Phase | Epic Signal | Network Signal | Combined Detection |
|-------|-----------|----------------|-------------------|
| Reconnaissance | User accessing records outside department | Normal traffic | Access pattern anomaly |
| Data Collection | High record access count over days | — | Per-user auto-adaptive baseline breach |
| Exfiltration | — | Large outbound transfers after-hours | After-hours outbound seasonal deviation |
| Detection | BTG access without clinical justification | USB/external device traffic (if monitored) | Combined risk score |

### 8.4 IoMT Device Compromise

| Phase | Epic Signal | Network Signal | Combined Detection |
|-------|-----------|----------------|-------------------|
| Compromise | — | IPS alert from medical device subnet | IPS critical from device IP range |
| C2 Communication | — | Outbound to known-bad IP from device | IOC match from device subnet |
| Impact | Device integration errors in Epic | Interface anomalies | Epic error + network threat correlation |

---

## 9. Navigation & UX

### 9.1 Header Navigation (matching Network Insights pattern)

```
[App Logo] | Overview | Access Monitoring | Network Threats | Correlation | Incidents | Explore | [TimeframeSelector]
```

### 9.2 Timeframe Control

- Global `TimeframeSelector` in `AppHeader.ActionItems` (same as Network Insights)
- Default: `now()-2h`
- All pages respect the shared timeframe via `DqlQueryParamsProvider`
- Presets: Last 30min, Last 2h, Last 6h, Last 24h, Last 7d, Last 30d

### 9.3 Drill-Down Patterns

| From | To | Action |
|------|-----|--------|
| Overview KPI card | Relevant detail page | Click navigates to `/access`, `/threats`, etc. |
| Threat IP in table | Network Insights app (cross-app intent) | Intent link to Network Insights filtered by IP |
| Davis problem | Incidents page filtered | Click filters to specific problem |
| Site risk score | Filtered view for that site | Click adds `healthcare.site` filter |

---

## 10. Non-Functional Requirements

| Requirement | Target | Notes |
|------------|--------|-------|
| Initial page load | < 3 seconds | Limit initial queries to 6 KPI cards + 2 charts |
| Query timeout | 30 seconds max | Use `limit` and time-bounded queries |
| Data freshness | Near-real-time (< 2min lag) | Grail ingestion latency |
| Browser support | Chrome, Edge, Firefox (latest) | Dynatrace AppEngine standard |
| Accessibility | Strato WCAG 2.1 AA compliance | Use Strato components for built-in a11y |
| Bundle size | < 2MB | Tree-shake Strato imports per AGENTS.md guidance |

---

## 11. Implementation Phases

### Phase 1 — Foundation (MVP)
- App scaffolding with `dt-app`
- `queries.ts` with all DQL queries
- Overview page with KPI cards and timelines
- Access Monitoring page (login analysis)
- Network Threats page (firewall/IPS)
- Explore page with presets

### Phase 2 — Correlation & Intelligence
- Cross-Correlation page with join queries
- Geographic threat map (SVG, from Network Insights pattern)
- Threat actor table combining both sources
- Site-level risk scoring

### Phase 3 — Anomaly Detection & Incidents
- Metric event configurations for Davis AI
- Seasonal baseline definitions
- Incidents page with Davis problem display
- Auto-adaptive threshold tuning
- Problem creation for detected scenarios

### Phase 4 — Advanced Scenarios
- Attack chain visualization (custom SVG)
- Ransomware detection workflow
- Insider threat behavioral profiling
- IoMT device security monitoring
- Cross-app intent links to Network Insights app
