# Healthcare Health Monitoring — Dynatrace App Requirements

**Date:** April 17, 2026
**Version:** 1.0
**Status:** Draft
**App ID:** `my.healthcare.health.monitoring`
**Reference:** Network Insights App v1.4.0 (pattern & architecture baseline)

---

## 1. Purpose

This document defines the requirements for a Dynatrace Platform App that leverages **Epic EHR telemetry** and **network infrastructure data** together to monitor and analyze the **operational health** of a healthcare environment. The app provides visibility into clinical system availability, network infrastructure performance, integration pipeline health, and cross-domain impact analysis — enabling proactive identification of degradation before it impacts patient care.

The design follows the proven patterns established by the **Network Insights App** — specifically its page architecture (Overview → domain-specific pages → Explore), shared `queries.ts` module, `DqlQueryParamsProvider` for app-wide time control, Strato component usage, and `useDql` hook integration. The Infrastructure page in Network Insights is the primary UX pattern for this app's multi-vendor, multi-section layout.

---

## 2. Scope

### In Scope

- Real-time operational health dashboard combining Epic EHR + network infrastructure data
- Anomaly detection configuration leveraging Davis AI (static thresholds, auto-adaptive baselines, seasonal patterns)
- Problem creation for health degradation incidents
- Cross-correlation of Epic system health with network infrastructure health
- Scenario-based detection (ED surge, Epic outage, HL7 failure, network link flap)
- DQL-based exploration with healthcare operations presets

### Out of Scope

- Building OpenPipeline configurations (data assumed pre-parsed)
- Modifying the log generators
- Clinical decision support or patient-facing features
- Security monitoring (covered by the companion Security Monitoring app)

---

## 3. Data Sources

### 3.1 Epic EHR Telemetry (via `generator.type == "epic-siem"`)

| Log Type | Key Health Fields | Use Case |
|----------|------------------|----------|
| **SIEM Audit** | `Action`, `WorkstationID`, `IP`, timestamp patterns | Login volume as system activity proxy, workstation availability |
| **Clinical Events** | `ORDER_TYPE`, `MEDICATION_NAME`, `NOTE_TYPE`, `DEPARTMENT` | Clinical workflow throughput, order volume trends |
| **HL7v2 Messages** | `MSH.9` (message type), `MSH.10` (control ID), ACK status | Interface health, message delivery success rate, queue depth |
| **FHIR API Logs** | `method`, `path`, `status`, `response_time_ms`, `client_id` | API response times, error rates, throughput |
| **MyChart Activity** | `session_id`, `patient_portal_action`, `device_type`, `response_time` | Patient portal availability, user experience |
| **ETL/Integration** | `job_name`, `source_system`, `records_processed`, `status`, `duration_seconds` | Batch job success rates, processing times, data pipeline health |

### 3.2 Network Infrastructure Telemetry (via `generator.type == "network"`)

| Data Type | Key Health Fields | Use Case |
|-----------|------------------|----------|
| **Cisco IOS Syslog** | `facility`, `mnemonic`, `severity_name`, `network.interface.name/state` | Interface flaps, routing protocol health, device errors |
| **SNMP Metrics** | `network.snmp.cpu`, `network.snmp.memory`, `network.snmp.sessions` | Device resource utilization trends |
| **SNMP Interface** | `network.snmp.if.in_octets`, `network.snmp.if.out_octets`, `network.snmp.if.utilization` | Bandwidth utilization, saturation detection |
| **NetFlow Records** | `network.flow.bytes`, `network.flow.packets`, `network.flow.protocol` | Traffic volume trends, capacity planning |
| **Firewall Connections** | `network.firewall.action == "built"/"teardown"`, `bytes_recv/sent` | Connection rate health, throughput monitoring |
| **Routing Events** | `network.routing.protocol`, `network.routing.state`, `network.routing.neighbor_ip` | OSPF/BGP neighbor health, routing stability |

### 3.3 Hospital Sites (Kansas City Geography)

| Site | Code | IP Range | Clinical Profile |
|------|------|----------|-----------------|
| Main Campus | `kcrmc-main` | `10.10.x.x` | Level I Trauma, 500 beds, highest volume |
| Topeka Clinic | `tpk-clinic` | `10.20.x.x` | Outpatient, 50 providers |
| Wichita Clinic | `wch-clinic` | `10.30.x.x` | Outpatient + Urgent Care |
| Lawrence Clinic | `lwr-clinic` | `10.40.x.x` | Outpatient, smallest site |

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
    { "name": "storage:logs:read", "comment": "Query Epic and network health logs from Grail" },
    { "name": "storage:buckets:read", "comment": "Read log buckets" },
    { "name": "storage:metrics:read", "comment": "Read device metrics and extracted health metrics" },
    { "name": "storage:bizevents:read", "comment": "Query SNMP inventory bizevents" },
    { "name": "storage:events:read", "comment": "Read Davis problems and events" },
    { "name": "davis:problems:read", "comment": "Display auto-detected health problems" }
  ]
}
```

### 4.3 File Structure

```
healthcare-health-monitoring/
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
│   │   │   ├── HealthBadge.tsx        ← Green/amber/red health indicator
│   │   │   └── SiteCard.tsx           ← Per-site health summary card
│   │   └── pages/
│   │       ├── Overview.tsx           ← Environment health dashboard
│   │       ├── EpicHealth.tsx         ← Epic system health deep dive
│   │       ├── NetworkHealth.tsx      ← Network infrastructure health
│   │       ├── IntegrationHealth.tsx  ← HL7, FHIR, ETL pipeline health
│   │       ├── SiteView.tsx           ← Per-site drill-down
│   │       ├── Problems.tsx           ← Davis problems + health incidents
│   │       └── Explore.tsx            ← DQL editor with health presets
```

---

## 5. Page Requirements

### 5.1 Overview — Environment Health Dashboard

**Route:** `/`
**Purpose:** At-a-glance health status for the entire healthcare environment combining clinical and infrastructure health.
**Reference pattern:** Network Insights `Overview.tsx` (KPI row → timeline → distribution) + Infrastructure & Operations App (data center → host view model)

#### KPI Cards (top row)

| KPI | DQL Source | Field | Health Logic |
|-----|-----------|-------|-------------|
| Epic System Health | Epic SIEM login success rate (last 15min) | `success_rate` | Green > 99%, Amber > 95%, Red ≤ 95% |
| HL7 Interface Status | HL7 message ACK rate | `ack_rate` | Green > 99.5%, Amber > 98%, Red ≤ 98% |
| FHIR API Health | FHIR requests with status < 400 / total | `success_rate` | Green > 99%, Amber > 97%, Red ≤ 97% |
| Network Uptime | SNMP devices with recent poll / total devices | `up_ratio` | Green = 100%, Amber ≥ 90%, Red < 90% |
| Avg Device CPU | Average `network.snmp.cpu` across all devices | `avg_cpu` | Green < 60%, Amber < 80%, Red ≥ 80% |
| Active Problems | `fetch dt.davis.problems \| filter event.status == "ACTIVE"` | `count()` | Green = 0, Amber ≤ 2, Red > 2 |

#### Visualizations

| Chart | Type | Data |
|-------|------|------|
| System Activity Timeline | `TimeseriesChart` (area, stacked) | Epic events + network events by `generator.type`, 5m bins |
| Epic Event Distribution | `PieChart` | Epic log types: SIEM audit, clinical, HL7, FHIR, MyChart, ETL |
| Network Event Distribution | `PieChart` | Network sources: cisco_ios, paloalto, fortinet, netflow, snmp |
| Site Health Summary | Custom multi-card layout | Per-site composite health score (Epic + Network combined) |
| SNMP Device Health Grid | `DataTable` with health badges | Device hostname, CPU, memory, interfaces up/total, status |

#### Seasonality Overlays

- **Current vs. baseline activity:** Overlay current Epic event volume on top of 4-week same-weekday average
- **Shift-pattern awareness:** Visual band showing expected volume range for current time-of-day

---

### 5.2 Epic Health — Clinical System Deep Dive

**Route:** `/epic`
**Purpose:** Deep dive into Epic EHR system health — the clinical technology stack.

#### Sections

**A. Login & Authentication Health**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Login Volume Over Time | `TimeseriesChart` | `makeTimeseries` on Epic SIEM logins, split by success/fail, 5m interval |
| Login Success Rate | `SingleValue` + trend | `summarize success = countIf(Action=="Login Success"), total = count()` |
| Active Users (unique) | `SingleValue` | `countDistinct(EMPid)` in current timeframe |
| Login Volume by Site | `CategoricalBarChart` | `summarize count(), by: {healthcare.site}` |

**B. Clinical Workflow Throughput**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Order Volume Over Time | `TimeseriesChart` | Clinical events by `ORDER_TYPE`, 5m bins |
| Note Creation Rate | `TimeseriesChart` | Clinical events by `NOTE_TYPE`, 5m bins |
| Department Activity | `CategoricalBarChart` (horizontal) | Clinical events grouped by `DEPARTMENT` |
| Clinical Event Types | `PieChart` | Distribution of clinical event categories |

**C. MyChart Portal Health**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Portal Sessions Over Time | `TimeseriesChart` | MyChart sessions by `patient_portal_action`, 5m bins |
| Device Type Distribution | `PieChart` | MyChart by `device_type` (mobile, desktop, tablet) |
| Portal Response Times | `TimeseriesChart` | If available, response time percentiles over time |

**D. Seasonal Patterns**
| Insight | Method |
|---------|--------|
| Shift change detection | Login volume spike at 7AM and 7PM = healthy shift handoff |
| Clinical throughput baseline | Order volume by hour-of-day, auto-adaptive baseline |
| MyChart usage peaks | Portal sessions peak at 8-9AM and 5-7PM (patients checking results) |

---

### 5.3 Network Health — Infrastructure Deep Dive

**Route:** `/network`
**Purpose:** Network infrastructure health analysis.
**Reference pattern:** Network Insights `Infrastructure.tsx` (multi-vendor sections: Cisco IOS → PAN-OS → FortiGate → SNMP)

#### Sections

**A. Device Health Overview (SNMP)**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Device CPU Over Time | `TimeseriesChart` | `timeseries cpu = avg(\`network.snmp.cpu\`), by: {hostname}` |
| Device Memory Over Time | `TimeseriesChart` | `timeseries mem = avg(\`network.snmp.memory\`), by: {hostname}` |
| Active Sessions | `TimeseriesChart` | `timeseries sessions = avg(\`network.snmp.sessions\`), by: {hostname}` |
| Device Snapshot Table | `DataTable` | Latest CPU, memory, sessions, interfaces up/total per device |
| Health Status Rings | Custom SVG (from Network Insights `NetworkWireframe.tsx`) | Per-device CPU/memory color rings on topology view |

**B. Interface Health**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Interface Traffic In/Out | `TimeseriesChart` (dual series) | `timeseries` on `network.snmp.if.in_octets` and `out_octets` |
| Interface Utilization | `TimeseriesChart` | `timeseries util = avg(\`network.snmp.if.utilization\`), by: {hostname, interface}` |
| Interface State Changes | `DataTable` | Cisco IOS logs with UPDOWN/LINEPROTO events |
| Link Flap Detection | `DataTable` + alert badge | Interfaces with > 3 state changes in 30 minutes |

**C. Routing Protocol Health**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Routing Events Timeline | `TimeseriesChart` | OSPF/BGP events over time |
| Neighbor State Table | `DataTable` | Latest routing neighbor states, IP, protocol |
| Routing Stability Score | `SingleValue` | Ratio of stable neighbors to total, last 1h |

**D. Firewall Connection Health**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Connection Rate Over Time | `TimeseriesChart` | Built/teardown events per 5min |
| Throughput (Bytes In/Out) | `TimeseriesChart` (dual axis) | `network.firewall.bytes_recv/sent` over time |
| Connection Table Rate | `SingleValue` | Current connections per second vs. device capacity |

**E. Network Traffic Volume (NetFlow)**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| Total Traffic Over Time | `TimeseriesChart` | NetFlow bytes + packets per 5min bin |
| Protocol Distribution | `PieChart` | NetFlow by protocol |
| Top Ports | `CategoricalBarChart` | NetFlow by `network.flow.dst_port` |

---

### 5.4 Integration Health — HL7, FHIR, ETL Pipeline Monitoring

**Route:** `/integrations`
**Purpose:** Health of the data integration layer connecting Epic to downstream systems.

#### Sections

**A. HL7v2 Interface Health**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| HL7 Message Volume Over Time | `TimeseriesChart` | HL7 messages by `MSH.9` (message type), 5m bins |
| HL7 Message Type Distribution | `PieChart` | ADT, ORM, ORU, MDM, SIU counts |
| HL7 ACK Rate | `SingleValue` + trend | Percentage of messages with successful ACK |
| HL7 Error Table | `DataTable` | Messages with NAK or error status, sorted by timestamp |

**B. FHIR API Health**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| FHIR Request Rate Over Time | `TimeseriesChart` | FHIR requests by `method`, 5m bins |
| FHIR Response Status Distribution | `PieChart` | 2xx, 3xx, 4xx, 5xx breakdown |
| FHIR Error Rate | `SingleValue` + trend | (4xx + 5xx) / total |
| FHIR Response Time Percentiles | `TimeseriesChart` | P50, P95, P99 response times |
| FHIR Slow Requests Table | `DataTable` | Requests with response_time > 2000ms |
| FHIR Client Usage | `CategoricalBarChart` | Request count by `client_id` |

**C. ETL/Integration Job Health**
| Visualization | Type | DQL Pattern |
|--------------|------|-------------|
| ETL Job Success/Failure Over Time | `TimeseriesChart` | ETL events by `status` (success/failure), 5m bins |
| ETL Job Duration Trends | `TimeseriesChart` | `duration_seconds` by `job_name` |
| Records Processed | `TimeseriesChart` | `records_processed` by `source_system` |
| Failed Jobs Table | `DataTable` | ETL jobs with `status == "failed"`, sorted by timestamp |
| Job Success Rate | `SingleValue` | Success count / total count |

**D. Seasonal Patterns**
| Insight | Method |
|---------|--------|
| HL7 ADT volume follows admissions | Peak at 10AM-2PM weekdays, trough at weekends |
| ETL batch window | Expected runs at midnight, 6AM, noon — alert if missing |
| FHIR API daily pattern | Mobile app usage creates evening/morning peaks |

---

### 5.5 Site View — Per-Site Health Drill-Down

**Route:** `/sites`
**Purpose:** Site-by-site health comparison with drill-down capability.

#### Layout

**Top Level:** Card grid showing all 4 sites with composite health scores

| Site Card Content | Source |
|------------------|--------|
| Site name and code | Static config |
| Composite health score (0-100) | Weighted: Epic health 40% + Network health 30% + Integration health 30% |
| Active problems count | Davis problems filtered by `healthcare.site` |
| Key metrics: login rate, device CPU avg, HL7 ACK rate | Combined DQL queries filtered per site |

**Drill-Down (click a site):** Filtered view showing:
- All Overview KPIs scoped to that site
- Epic health metrics for that site only
- Network devices at that site (SNMP filtered by `healthcare.site`)
- Integration jobs relevant to that site

---

### 5.6 Problems — Davis AI Health Incidents

**Route:** `/problems`
**Purpose:** Display Davis AI-detected health problems and metric event alerts.

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
- Color-coded by `event.category` (AVAILABILITY, ERROR, SLOWDOWN, RESOURCE)

**C. Problem History (closed)**
```dql
fetch dt.davis.problems
| filter event.status == "CLOSED"
| summarize problem_count = count(), avg_duration = avg(toDouble(event.end - event.start) / 60000000000.0), by: { event.category }
```

**D. Custom Metric Events (to be configured)**

| Metric Event Name | Metric Selector | Strategy | Condition |
|-------------------|----------------|----------|-----------|
| Epic Login Volume Drop | `epic.siem.login.count:splitBy("healthcare.site")` | Seasonal baseline | Volume drops below seasonal norm by 2σ |
| HL7 ACK Rate Degradation | `epic.hl7.ack.rate:splitBy("healthcare.site")` | Auto-adaptive | ACK rate drops below learned baseline |
| FHIR API Slowdown | `epic.fhir.response_time.p95` | Auto-adaptive | P95 response time exceeds baseline by 2σ |
| ETL Job Failure | `epic.etl.failure.count` | Static | > 0 failures per 15min window |
| ETL Job Missing | `epic.etl.job.count` (expected runs) | Static | Expected batch job not seen within 30min of schedule |
| Device CPU Critical | `network.snmp.cpu:splitBy("hostname")` | Auto-adaptive | CPU exceeds learned per-device baseline by 3σ |
| Device Memory Critical | `network.snmp.memory:splitBy("hostname")` | Static | Memory > 90% |
| Interface Utilization Saturation | `network.snmp.if.utilization:splitBy("hostname","interface")` | Auto-adaptive | Utilization exceeds baseline by 2σ |
| Interface Flap Storm | `network.interface.state_change.count:splitBy("hostname")` | Static | > 5 state changes per 30min |
| Routing Neighbor Loss | `network.routing.neighbor.down.count` | Static | > 0 neighbor down events |
| NetFlow Volume Anomaly | `network.flow.bytes:splitBy("healthcare.site")` | Seasonal baseline | Traffic deviates from same-weekday/hour norm by 3σ |
| Site Health Degradation | Composite: login + device CPU + HL7 rate | Auto-adaptive | Composite score drops below learned baseline |

**E. Seasonality Configuration**

| Pattern | Baseline Window | Season Length | Alert Sensitivity |
|---------|----------------|---------------|-------------------|
| Clinical shift cycle | 14 days | 24 hours | Medium (2σ) |
| Weekly volume pattern | 8 weeks | 7 days | Medium (2σ) |
| ETL batch schedule | 7 days | 24 hours | High (expect exact schedule) |
| Monthly reporting cycle | 6 months | 30 days | Low (3σ) |
| Device utilization daily | 14 days | 24 hours | Medium (2σ) |

---

### 5.7 Explore — DQL Editor with Health Presets

**Route:** `/explore`
**Purpose:** Free-form DQL exploration with healthcare operations-focused preset queries.
**Reference pattern:** Network Insights `Data.tsx` (DQLEditor + preset buttons + table/chart output)

#### Preset Queries

| Label | Query Summary |
|-------|--------------|
| All Epic Events | Epic logs by `generator.type == "epic-siem"` |
| Epic Login Activity | SIEM audit logs with Action field |
| HL7 Messages | HL7v2 message logs with MSH fields |
| HL7 Errors | HL7 messages with error/NAK status |
| FHIR API Requests | FHIR logs with method, path, status |
| FHIR Slow Requests | FHIR requests with response_time > 2s |
| ETL Job Status | ETL logs with job_name, status, duration |
| ETL Failures | ETL logs where status = failed |
| MyChart Sessions | MyChart activity logs |
| Clinical Orders | Clinical events with ORDER_TYPE |
| Network Device Health | SNMP poll logs with CPU/memory/sessions |
| SNMP CPU Trend | `timeseries avg(network.snmp.cpu) by hostname` |
| SNMP Interface Traffic | `timeseries sum(network.snmp.if.in_octets) by hostname` |
| Interface State Changes | Cisco IOS UPDOWN/LINEPROTO events |
| Routing Protocol Events | OSPF/BGP neighbor state changes |
| NetFlow Volume | NetFlow bytes and packets over time |
| Davis Health Problems | `fetch dt.davis.problems` |
| Events by Site | All events summarized by `healthcare.site` |

---

## 6. Cross-Data Correlation Strategy

### 6.1 Health Impact Correlations

The key value of this app is correlating infrastructure health with clinical impact:

```
Network Interface Flap ←→ Epic HL7 Message Failures
  - Interface hosting Epic HL7 connection goes down → HL7 NAKs spike
  - Detection: join interface state change with HL7 error rate in same time window

Device CPU/Memory Saturation ←→ Epic Response Time Degradation
  - Network device CPU at 95% → packets dropped → FHIR API latency increases
  - Detection: correlate SNMP CPU metric with FHIR response time percentile

Routing Neighbor Loss ←→ Site Connectivity Impact
  - BGP/OSPF neighbor down → site loses connectivity → Epic login volume drops to 0
  - Detection: routing event followed by per-site login volume drop within 5min

NetFlow Volume Spike ←→ Epic System Slowdown
  - Bandwidth saturation → Epic system performance degradation
  - Detection: NetFlow volume exceeds interface capacity correlated with Epic response time

Firewall Connection Table Full ←→ Epic Connection Failures
  - Connection table saturated → new connections dropped → Epic API 503 errors
  - Detection: firewall connection rate plateau + FHIR 5xx error rate increase
```

### 6.2 DQL Correlation Examples

**Network Outage → Epic Impact:**
```dql
fetch logs
| filter log.source == "cisco_ios" 
  AND (matchesPhrase(content, "UPDOWN") OR matchesPhrase(content, "LINEPROTO"))
  AND network.interface.state == "down"
| summarize interface_downs = count(), by: { site = healthcare.site, interval = bin(timestamp, 5m) }
| join [
    fetch logs
    | filter generator.type == "epic-siem"
    | summarize epic_events = count(), by: { site = healthcare.site, interval = bin(timestamp, 5m) }
  ], on: { site, interval }, kind: inner
| fieldsAdd impact_ratio = if(epic_events == 0, 1.0, else: toDouble(interface_downs) / toDouble(epic_events))
| filter interface_downs > 0
| sort interval desc
```

**Device CPU vs. FHIR Response Time:**
```dql
fetch logs
| filter log.source == "snmp.poll"
| summarize avg_cpu = avg(toDouble(network.snmp.cpu)), by: { interval = bin(timestamp, 5m) }
| join [
    fetch logs
    | filter generator.type == "epic-siem" AND isNotNull(response_time_ms)
    | summarize p95_response = percentile(toDouble(response_time_ms), 95), by: { interval = bin(timestamp, 5m) }
  ], on: { interval }, kind: inner
| sort interval desc
```

**Site Health Composite Score:**
```dql
fetch logs
| filter generator.type == "epic-siem"
| summarize epic_count = count(), by: { site = healthcare.site }
| join [
    fetch logs
    | filter log.source == "snmp.poll"
    | summarize avg_cpu = avg(toDouble(network.snmp.cpu)), avg_mem = avg(toDouble(network.snmp.memory)), by: { site = healthcare.site }
  ], on: { site }, kind: inner
| fieldsAdd health_score = 100.0 
    - if(avg_cpu > 80, 30, else: if(avg_cpu > 60, 15, else: 0))
    - if(avg_mem > 80, 30, else: if(avg_mem > 60, 15, else: 0))
| sort health_score asc
```

---

## 7. Anomaly Detection & Seasonality Requirements

### 7.1 Davis AI Integration Points

| Capability | How Used |
|-----------|----------|
| **Static thresholds** | Hard limits: device memory > 90%, ETL failure > 0, routing neighbor loss > 0 |
| **Auto-adaptive baselines** | Per-device, per-metric learned baselines: CPU, memory, interface utilization, FHIR response times |
| **Seasonal baselines** | Shift-pattern and weekly cycle awareness for clinical activity volumes |
| **Metric events** | Custom events on extracted metrics triggering Davis problems |
| **Problem correlation** | Davis groups related events (e.g., "network device CPU + Epic FHIR slowdown" = single problem) |
| **Topology awareness** | Metric events mapped to relevant entity (host, service, custom device) |

### 7.2 Metrics to Extract (via OpenPipeline or generator attributes)

| Metric Key | Source | Dimensions | Purpose |
|-----------|--------|------------|---------|
| `epic.siem.login.count` | Epic SIEM | `healthcare.site`, `Action` | System activity baseline |
| `epic.hl7.message.count` | Epic HL7 | `healthcare.site`, `MSH.9` | Interface throughput |
| `epic.hl7.ack.rate` | Epic HL7 | `healthcare.site` | Interface reliability |
| `epic.fhir.request.count` | Epic FHIR | `method`, `status` | API throughput |
| `epic.fhir.response_time.p95` | Epic FHIR | `method` | API performance |
| `epic.etl.job.count` | Epic ETL | `job_name`, `status` | Pipeline health |
| `epic.etl.duration.seconds` | Epic ETL | `job_name` | Pipeline performance |
| `epic.mychart.session.count` | Epic MyChart | `healthcare.site`, `device_type` | Portal availability |
| `epic.clinical.order.count` | Epic Clinical | `ORDER_TYPE`, `healthcare.site` | Workflow throughput |
| `network.snmp.cpu` | SNMP | `hostname` | Device health |
| `network.snmp.memory` | SNMP | `hostname` | Device health |
| `network.snmp.if.utilization` | SNMP | `hostname`, `interface` | Bandwidth health |
| `network.interface.state_change.count` | Cisco IOS | `hostname`, `network.interface.name` | Interface stability |
| `network.routing.neighbor.count` | Cisco IOS | `network.routing.protocol` | Routing stability |
| `network.flow.bytes` | NetFlow | `healthcare.site` | Traffic volume |

### 7.3 Seasonality Patterns to Detect

| Pattern | Cycle | Expected Shape | Anomaly Example |
|---------|-------|---------------|-----------------|
| Clinical shift cycle | 24h | Peak 7AM-7PM, trough 11PM-5AM | Login drop during day shift |
| Weekend reduction | 7d | Mon-Fri 100%, Sat 30%, Sun 20% | Monday volume = Sunday volume |
| ED surge pattern | Variable | Spike after local events (weather, accidents) | 10x normal ED volume sustained > 2h |
| ETL batch schedule | 24h | Exact runs at midnight, 6AM, noon | Batch job 30min late |
| Monthly reporting | 30d | Spike last 3 days (billing/compliance) | No spike at month-end |
| Seasonal flu | Annual | Oct-Mar elevated admissions | Summer admission spike |
| Device utilization daily | 24h | Business hours higher, overnight lower | Overnight saturation |

---

## 8. Health Scenarios (correlated detection requirements)

### 8.1 ED Surge / Mass Casualty Incident (MCI)

| Signal | Epic Indicator | Network Indicator | Combined Detection |
|--------|---------------|-------------------|-------------------|
| Volume spike | Order volume 5-10x normal, high-acuity orders | NetFlow volume spike to ED subnet | Seasonal deviation on both |
| Capacity strain | Login volume increase (more providers), long session times | Device CPU/memory increase on ED switches | Auto-adaptive baseline breach |
| Interface stress | HL7 ADT message surge | Interface utilization approaching saturation | Cross-correlation threshold |
| Resolution | Volumes normalize over hours | Traffic returns to baseline | Seasonal recovery detection |

### 8.2 Epic Outage (Network Root Cause)

| Signal | Epic Indicator | Network Indicator | Combined Detection |
|--------|---------------|-------------------|-------------------|
| Network failure | — | Interface down event, routing neighbor loss | Static threshold (immediate) |
| Epic impact | Login volume drops, FHIR API errors spike | — | Seasonal baseline violation |
| Correlation | Epic errors coincide with network event timestamp | Network event precedes Epic impact by seconds | Cross-domain join |
| Root cause | Epic errors = symptom | Network event = cause | Davis problem correlation |

### 8.3 HL7 Interface Failure

| Signal | Epic Indicator | Network Indicator | Combined Detection |
|--------|---------------|-------------------|-------------------|
| Interface degradation | HL7 NAK rate increasing | Interface utilization spike or packet loss | ACK rate auto-adaptive breach |
| Complete failure | HL7 message volume drops to 0 | Interface down or routing change | Volume drop = static 0 + network event |
| Queue buildup | Message volume backlog detected | — | Expected volume missing |
| Recovery | Message surge (queue drain) | Interface restored | Recovery correlation |

### 8.4 Network Link Flap Storm

| Signal | Epic Indicator | Network Indicator | Combined Detection |
|--------|---------------|-------------------|-------------------|
| Link instability | — | Interface up/down > 5 times in 30min | Static flap threshold |
| Clinical impact | Intermittent Epic errors, slow response | Packet loss, latency increase | Cross-domain timing |
| Cascade | Multiple Epic functions degraded | Multiple interfaces affected | Multi-signal problem |

---

## 9. Navigation & UX

### 9.1 Header Navigation (matching Network Insights pattern)

```
[App Logo] | Overview | Epic Health | Network Health | Integrations | Sites | Problems | Explore | [TimeframeSelector]
```

### 9.2 Timeframe Control

- Global `TimeframeSelector` in `AppHeader.ActionItems` (same as Network Insights)
- Default: `now()-2h`
- All pages respect shared timeframe via `DqlQueryParamsProvider`
- Presets: Last 30min, Last 2h, Last 6h, Last 24h, Last 7d, Last 30d

### 9.3 Drill-Down Patterns

| From | To | Action |
|------|-----|--------|
| Overview site card | Site View filtered to that site | Click navigates to `/sites?site=kcrmc-main` |
| Overview KPI card | Relevant detail page | Click navigates to `/epic`, `/network`, etc. |
| SNMP device row | Network Health filtered to device | Click adds `hostname` filter |
| Davis problem | Problems page filtered | Click filters to specific problem |
| Network device on wireframe | Device detail panel (Network Insights pattern) | Click shows stat cards + recent events |

### 9.4 Cross-App Links

| From This App | To | Purpose |
|--------------|-----|---------|
| Network device | Network Insights App (wireframe page) | Detailed network topology view |
| Security anomaly | Healthcare Security Monitoring App | Investigate security aspect of health event |
| Device entity | Infrastructure & Operations App | Native DT infrastructure view |

---

## 10. Network Wireframe Integration

**Optional page or embedded component** — reuse the Network Insights `NetworkWireframe.tsx` pattern to show healthcare network topology with health overlays.

### Health Wireframe Requirements

| Feature | Description |
|---------|-------------|
| Auto-discovery from SNMP inventory | Same `network.device.inventory` bizevent query as Network Insights |
| Health rings on devices | CPU ring (green/amber/red) + memory ring per device |
| Animated flow links | Traffic volume shown as animated dot speed/thickness |
| Clinical overlay | Badge on devices showing "Epic traffic: Xk events/5m" from correlated data |
| Click drill-down | Device panel with SNMP stats + Epic health impact for that device's site |

---

## 11. Non-Functional Requirements

| Requirement | Target | Notes |
|------------|--------|-------|
| Initial page load | < 3 seconds | Limit initial queries to 6 KPI cards + 2 charts |
| Query timeout | 30 seconds max | Use `limit` and time-bounded queries |
| Data freshness | Near-real-time (< 2min lag) | Grail ingestion latency |
| Browser support | Chrome, Edge, Firefox (latest) | Dynatrace AppEngine standard |
| Accessibility | Strato WCAG 2.1 AA compliance | Use Strato components for built-in a11y |
| Bundle size | < 2MB | Tree-shake Strato imports per AGENTS.md guidance |
| Auto-refresh | 60-second polling for Overview KPIs | `useDql` refetch on interval |

---

## 12. Implementation Phases

### Phase 1 — Foundation (MVP)
- App scaffolding with `dt-app`
- `queries.ts` with all DQL queries
- Overview page with KPI cards and timelines
- Epic Health page (login + clinical throughput)
- Network Health page (SNMP devices + interfaces)
- Explore page with presets

### Phase 2 — Integration & Sites
- Integration Health page (HL7, FHIR, ETL monitoring)
- Site View page with per-site drill-down
- Cross-data correlation queries
- Health scoring composite calculations

### Phase 3 — Anomaly Detection & Problems
- Metric event configurations for Davis AI
- Seasonal baseline definitions (shift pattern, weekly cycle)
- Problems page with Davis problem display
- Auto-adaptive threshold tuning
- Problem creation for health degradation scenarios

### Phase 4 — Advanced Visualization
- Network wireframe with health overlays (reuse Network Insights SVG pattern)
- Animated topology with real-time health status
- Cross-app intent links (to Network Insights, Security Monitoring, Infrastructure & Operations)
- ED surge detection workflow
- Capacity planning views (utilization trends + forecasting)

---

## Appendix A: Scenario Coverage Matrix (Updated April 17, 2026)

Based on analysis of all 8 centralized scenarios in `config/scenarios/`, this section maps each toggleable scenario to the app pages that detect its signals.

### A.1 Toggle Mechanism

| Layer | Mechanism | Runtime Toggle | Simultaneous |
|-------|-----------|----------------|-------------|
| **Centralized** (8 scenarios in `config/scenarios/`) | WebUI API: `POST /api/scenarios/{key}/activate` | **YES** — no redeployment needed | **YES** — multiple scenarios can be active |
| **Epic-only** (8 in `src/epic_generator/config/scenarios/`) | `EPIC_SCENARIO` env var | NO — requires pod restart | NO — one at a time |
| **Network-only** (10 in `src/network_generator/scenarios/`) | CLI `--scenario` flag | NO — requires pod restart | YES — multiple flags |

### A.2 Scenario → Page Detection Matrix

| Scenario | Toggle Key | Overview | Epic Health | Network Health | Integrations | Site View | Problems |
|----------|-----------|----------|------------|---------------|-------------|-----------|----------|
| Normal Day Shift | `normal-day-shift` | Baseline (all green) | Login + clinical baseline | SNMP baseline | HL7/FHIR/ETL baseline | All sites green | No problems |
| ED Surge / MCI | `ed-surge` | Epic KPI amber, volume spike | Order 5-10x, ED department spike | ED switch CPU spike | HL7 ADT surge | `kcrmc-main` amber | Seasonal deviation alert |
| Epic Outage (Network Root Cause) | `epic-outage-network-root-cause` | Epic RED, Network RED | Login crash → recovery wave | Core switch interface flap, Citrix/F5 down | FHIR 503 errors | `kcrmc-main` RED | **Davis problem** — cascade chain |
| HL7 Interface Failure | `hl7-interface-failure` | Integration KPI RED | — | Switch port err-disable (VLAN 30) | HL7 ACK rate crash, volume drop | Affected site amber | Interface + HL7 problem |
| Ransomware Attack | `ransomware-attack` | Wichita RED, login spike | Brute force → mass BTG access | FortiGate IPS + Palo Alto threat | API exfiltration 20x | `wch-clinic` → `kcrmc-main` cascade | Multi-signal critical |
| IoMT Device Compromise | `iomt-device-compromise` | Network KPI amber | Clinical data gap | IoMT VLAN anomaly, ARP spoofing | Device telemetry loss | Affected site amber | IoMT security event |
| MyChart Credential Stuffing | `mychart-credential-stuffing` | MyChart KPI RED | Portal response time spike | DMZ firewall saturation | — | `kcrmc-main` amber (DMZ) | Portal degradation |
| Insider Threat | `insider-threat-snooping` | After-hours login anomaly | BTG access pattern | — | — | User's site highlighted | Seasonal deviation (minimal) |

### A.3 Cross-Correlation Opportunities

| Scenario Pair (simultaneous) | Cross-Signal | App Detection |
|------------------------------|-------------|---------------|
| `ransomware-attack` active | Wichita IPS alerts + Epic login failures from same IP range (10.20.20.x) | IP-based join on Site View shows network threat → clinical impact |
| `epic-outage-network-root-cause` active | Interface down timestamp (T+0) → Citrix down (T+10s) → Epic logins fail (T+20s) | Temporal chain on Overview cascade timeline |
| `ed-surge` + baseline | ED order volume 5x + network ED subnet utilization 2x | Department-subnet join shows capacity correlation |
| `hl7-interface-failure` active | Switch port err-disable → HL7 NAK spike within 60s | Network → Integration temporal correlation |

### A.4 Topology Alignment (Verified)

The hospital topology (`config/hospital/topology.yaml`) is **already aligned** with Epic generator sites:

| Site Code | Epic `users.json` | Network `topology.yaml` | IP Range | Status |
|-----------|-------------------|------------------------|----------|--------|
| `kcrmc-main` | ✅ | ✅ | `10.10.x.x` | **Aligned** |
| `tpk-clinic` | ✅ | ✅ | `10.20.x.x` | **Aligned** |
| `wch-clinic` | ✅ | ✅ | `10.30.x.x` | **Aligned** |
| `lwr-clinic` | ✅ | ✅ | `10.40.x.x` | **Aligned** |

Cross-correlation joins on `healthcare.site` and IP subnet are fully operational.
