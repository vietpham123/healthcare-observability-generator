# Demo Flow: Healthcare Observability Platform

Step-by-step walkthrough for demonstrating the Healthcare Observability Generator and the Dynatrace Platform App. Designed for a 20–30 minute live demo.

---

## Prerequisites

| Component | Status Check |
|-----------|-------------|
| AKS generators running | `kubectl get pods -n healthcare-gen` — all pods `Running` |
| Data flowing to DT | Grail query: `fetch logs \| filter healthcare.pipeline == "healthcare-epic" \| sort timestamp desc \| limit 5` |
| DT Platform App deployed | Open: `https://gyz6507h.sprint.apps.dynatracelabs.com/ui/apps/my.dynatrace.healthcare.health.monitoring` |
| Web UI available | `http://172.206.131.122` for scenario toggling |
| Health indicators green | All SectionHealth pills showing green on Overview page |

---

## Part 1: The Data Pipeline (5 min)

### 1.1 — Show the Generators

Open the AKS cluster in Dynatrace (Kubernetes app):
- **Namespace**: `healthcare-gen`
- **Workloads**: `epic-generator` (v1.0.8), `network-generator` (v1.3.0), `webui` (v1.3.0)
- Point out: these containers generate all synthetic data — Epic SIEM logs, network syslog, SNMP metrics, NetFlow records

### 1.2 — Show Raw Data in Grail

Open DT **Notebooks** or **Logs & Events** and run:

```dql
// Epic SIEM logs
fetch logs
| filter dt.system.bucket == "observe_and_troubleshoot_apps_95_days"
| filter healthcare.pipeline == "healthcare-epic"
| sort timestamp desc
| limit 20
```

Point out key attributes: `healthcare.site`, `healthcare.event_type`, `E1Mid`, `epic.user_id`, `content`

```dql
// Network logs
fetch logs
| filter dt.system.bucket == "observe_and_troubleshoot_apps_95_days"
| filter healthcare.pipeline == "healthcare-network"
| sort timestamp desc
| limit 20
```

Point out: `network.device.hostname`, `network.vendor`, `network.severity`

```dql
// Network metrics (MINT)
timeseries avg(healthcare.network.device.cpu.utilization), by: {site, device}
```

Point out: dimensions `site`, `device`, `vendor` — these are the SNMP-polled metrics from 22 devices across 4 sites.

```dql
// NetFlow records
fetch logs
| filter log.source == "netflow"
| sort timestamp desc
| limit 20
```

Point out: `network.flow.src_addr`, `network.flow.dst_addr`, `network.flow.bytes`, `network.device.site`

### 1.3 — Key Takeaway

> "Two generators produce correlated data — an Epic SIEM simulator and a network infrastructure simulator. Everything flows into Dynatrace Grail via standard ingest APIs. No agents, no ActiveGate — just REST."

---

## Part 2: The Platform App — Overview (5 min)

### 2.1 — Open the App

Navigate to: **Apps → Healthcare Observability → Overview**

### 2.2 — Health Indicators

Point out the **Section Health** indicators at the top of the page:
- **Green pills** = all metrics within healthy thresholds
- **Hover over each pill** to see the tooltip: what is measured, why, threshold breakdown, current value
- **Auto-refreshing** every 30 seconds (no manual refresh needed)

### 2.3 — Campus Map

Point out:
- **Kansas map** — real geographic projection with I-70, I-35 highways, county grid, reference cities
- **Hospital hub** (Lawrence) — large green icon at the center of Kansas along I-70
- **Satellite clinics** — Oakley (west), Wellington (south), Belleville (north)
- **NetFlow animation** — watch the green dots travel from Lawrence to satellite clinics
- **Health badges** — green = healthy, amber = degraded, red = critical

> "This is a live map. The dots are actual NetFlow records from the last 30 minutes. Each dot represents aggregated bytes flowing between Lawrence and a satellite site."

### 2.4 — KPI Cards

Below the map:
- **Epic Login Success** — success rate from Epic SIEM login events
- **HL7 Delivery** — whether HL7 messages are flowing in the last 5 minutes
- **FHIR API Health** — success rate for FHIR R4 REST API calls
- **ETL Success** — batch job completion rate (excludes RUNNING jobs)
- **Avg Device CPU** — fleet-wide average CPU across network devices
- **Network Critical** — count of critical/emergency/alert syslog events
- **Active Users** — distinct users in the last 2 hours

### 2.5 — Site Filter

Click a site button (e.g., **Oakley Rural Health**):
- All KPIs filter to that site
- Map highlights the selected site
- All charts on the page update

> "Every page in the app has this site filter. It works for both log-based queries and metric-based timeseries."

---

## Part 3: Epic Health Deep Dive (5 min)

### 3.1 — Navigate to Epic Health

Click **Epic Health** tab. Note the section health indicators: Login Success, STAT Order Rate.

### 3.2 — Walk Through Charts

| Chart | What to Show |
|-------|-------------|
| **Login Trend** (TimeseriesChart) | Time-of-day curve — peaks at shift changes (7am, 3pm, 11pm) |
| **Login Success Rate** (TimeseriesChart) | Should be ~83% during normal operations (includes BLOCKED events) |
| **Event Distribution** (DonutChart) | Breakdown: SIEM, Clinical, HL7, FHIR, MyChart |
| **Audit Timeline** (CategoricalBarChart) | HIPAA audit events over time |
| **Session Analysis** | Active session count, average duration |

### 3.3 — Drill by Site

Select **Wellington Care Center** — watch all charts filter to just that clinic's data.

> "This is the Epic application layer — login health, clinical activity, and audit compliance. The next page shows the infrastructure underneath."

---

## Part 4: Network Health (5 min)

### 4.1 — Navigate to Network Health

Click **Network** tab. Note health indicators: Peak Device CPU, Device Fleet Health.

### 4.2 — Device Fleet Honeycomb

The honeycomb shows all network devices as hex tiles:
- **Green** tiles = device is reporting (up and healthy)
- **Red** tiles = device is silent (down or unreachable)

Hover over a tile to see the device hostname.

> "Each hex is a network device — routers, switches, firewalls, load balancers. Green means it reported a heartbeat in the last 5 minutes. Red means silence."

### 4.3 — KPI Cards

- **Devices Up** — count from latest heartbeat/SNMP poll
- **Avg CPU** — fleet-wide average
- **Avg Memory** — fleet-wide average
- **Network Events** — syslog count
- **NetFlow Records** — flow record count

### 4.4 — Traffic Charts

| Chart | What to Show |
|-------|-------------|
| **CPU by Device** (TimeseriesChart) | Individual device CPU lines — warning at 60%, critical at 80% |
| **Memory by Device** (TimeseriesChart) | Same for memory |
| **Traffic In** (TimeseriesChart) | Ingress bytes/sec per device |
| **Traffic Out** (TimeseriesChart) | Egress bytes/sec per device |

### 4.5 — Filter by Site

Select **Oakley Rural Health** — see only Oakley's devices in the honeycomb and charts.

> "This is the network infrastructure layer. When something goes wrong here, it cascades up to the Epic layer — we'll show that next."

---

## Part 5: Integration Health (3 min)

### 5.1 — Navigate to Integration Health

Click **Integration** tab. Note health indicators across four sections: Mirth Connect, HL7 Interface, FHIR API, and ETL Pipelines.

### 5.2 — KPI Cards

| KPI | What It Shows |
|-----|--------------|
| **HL7 Delivery** | Whether HL7 v2.x messages are actively flowing (100% = yes, 0% = no) |
| **FHIR API Health** | Success rate of FHIR R4 API calls (HTTP 2xx/3xx vs 4xx/5xx) |
| **FHIR Error Rate** | Percentage of FHIR calls returning errors |
| **ETL Success** | Batch job completion rate (SUCCESS + SUCCESS_WITH_WARNINGS) |
| **HL7 Vol/5min** | HL7 message count in the last 5-minute window |
| **Mirth Channels** | Percentage of Mirth Connect channels that are healthy |

### 5.3 — Section Health Indicators

Each section (Mirth Connect, HL7, FHIR, ETL) has its own health pill:
- **Mirth Connect**: Healthy only when all channels are running, error rate < 10%, and queue depth < 50
- **HL7 Interface**: Checks whether messages are actively flowing
- **FHIR API**: Success rate of REST API calls
- **ETL Pipelines**: Batch job success rate

> "This is the integration layer — HL7 messages, FHIR APIs, Mirth Connect channels, and ETL pipelines. In a real Epic environment, failures here mean data stops flowing between systems."

---

## Part 6: Security (3 min)

### 6.1 — Navigate to Security

Click **Security** tab. Note KPIs: Break-the-Glass Events, Failed Logins, Login Success Rate, After-Hours BTG, Active Workstations, Auth Failures.

### 6.2 — Key Metrics

| Metric | What It Shows |
|--------|--------------|
| **Break-the-Glass Events** | Emergency access events (BTG is normal in hospitals but monitored) |
| **After-Hours BTG** | BTG events outside 6 AM – 10 PM (higher risk for snooping) |
| **Failed Logins** | Login failure count (FAILEDLOGIN + LOGIN_BLOCKED + WPSEC_LOGIN_FAIL) |
| **Login Success Rate** | Overall Epic login success percentage |
| **Auth Failures** | BCA authentication layer failures |
| **Active Workstations** | Distinct workstations with activity |

### 6.3 — Charts

- **Security Events Over Time** — BTG vs Failed Login vs Login Blocked trends
- **BTG by User** — which users are using break-the-glass most
- **Failed Logins by Hour** — time-of-day pattern for failed logins
- **Security by Site** — BTG and auth failures broken down by site
- **Recent Security Events** — table of latest BTG and failure events

> "In a HIPAA-regulated environment, BTG events are expected but monitored. A spike means either a real emergency or a potential insider threat."

---

## Part 7: MyChart (2 min)

### 7.1 — Navigate to MyChart

Click **MyChart** tab. Note health indicator: MyChart Login.

### 7.2 — Key Metrics

- **Login Activity** — Patient portal login volume (volume-based health check)
- **Messaging Trends** — Patient-provider message volume
- **Scheduling** — Appointment booking activity
- **Device Distribution** — Mobile vs Desktop vs Tablet

> "MyChart is the patient-facing portal. Its health is measured by event flow volume — if events are flowing, the portal is up."

---

## Part 8: Correlated Scenario Demo (5–10 min)

This is the highlight of the demo — showing cross-domain correlation.

### 8.1 — Trigger a Scenario

Open the Web UI (`http://172.206.131.122`) and activate **Core Switch Failure**.

### 8.2 — Watch the Health Indicators Change

Within 60 seconds:
- **Network** page: Device Fleet honeycomb shows kcrmc-core-01 turn **red** (down), CPU spikes on kcrmc-dist-epic-01 (85%) and kcrmc-dist-epic-02 (78%)
- **Integration** page: Mirth Connect health degrades (elevated errors and queue depth)
- **Overview** page: Avg Device CPU rises, Network Critical count increases

### 8.3 — Walk Through the Cascade

**Network** page (check first):
1. Hex grid shows kcrmc-core-01 as RED (device down — no heartbeats)
2. CPU chart shows dist-epic-01 and dist-epic-02 spiking
3. Memory rises proportionally on affected switches

**Integration** page (check second):
1. Mirth channels ADT-OUT, ORM-OUT, ORU-OUT show elevated error rates and queue depths
2. Mirth section health turns amber/red
3. HL7 volume may show disruption

### 8.4 — Try Ransomware Attack

Deactivate Core Switch Failure, then activate **Ransomware Attack**.

Within 30-60 seconds:
- **Epic Health**: Login Success Rate drops dramatically (83% → ~44%)
- **Security**: Failed Logins spike (120 → 1400+), BTG events appear
- **Overview**: Login Success → RED

### 8.5 — Correlation Narrative

> "In the core switch failure, the network layer broke first — a device went down, causing Mirth Connect queue backups and HL7 delivery issues. In the ransomware scenario, the Epic application layer broke — mass login failures and emergency access events. Two different failure modes, both visible in the same app."

### 8.6 — Deactivate Scenario

Return to Web UI, click **Deactivate All**.
- **Core Switch Failure**: Recovers in ~2-3 minutes (network heartbeats resume)
- **Ransomware**: Recovery takes ~50 minutes (failed login events persist in the 2-hour DQL query window)

---

## Part 9: Explore Page (2 min)

### 9.1 — Navigate to Explore

Click **Explore** tab.

### 9.2 — Raw Log Viewer

Select **Epic SIEM** from the pipeline dropdown:
- See the last 100 raw log records with all fields
- Toggle to **Network** to see network infrastructure logs

### 9.3 — DQL Sandbox

Run any DQL query against the ingested data:

```dql
fetch logs
| filter dt.system.bucket == "observe_and_troubleshoot_apps_95_days"
| filter healthcare.pipeline == "healthcare-epic"
| filter E1Mid == "FAILEDLOGIN"
| sort timestamp desc
| limit 50
```

> "This is a DQL sandbox. Anything you can query in Grail, you can query here."

---

## Part 10: Sites (2 min)

### 10.1 — Navigate to Sites

Click **Sites** tab.

### 10.2 — Site Cards

Each site has a card showing:
- Site name, code, bed count, and profile type
- Login success rate (last 30 min)
- Active sessions
- Clinical events
- Network devices + average CPU

Click a site to drill down into site-specific detail: HL7 volume, error rate, event categories, netflow timeline.

> "This is the per-site summary. A hospital IT director would use this to compare sites at a glance."

---

## Scenario Quick Reference

| Scenario | Key Visuals | Pages to Watch |
|----------|-------------|----------------|
| **Normal Day Shift** | Smooth curves, green indicators | Overview |
| **Core Switch Failure** | Network device down (red hex), CPU spikes, Mirth queue backup | Network, Integration |
| **Ransomware Attack** | Red indicators everywhere, login failures spike, BTG events | Security, Epic Health, Overview |
| **HL7 Interface Failure** | HL7 disruption, syslog events from switch err-disable | Integration, Network |
| **Insider Threat** | After-hours BTG events, VIP patient snooping | Security |

---

## Demo Tips

1. **Start with health indicators** — hover over the green pills to show tooltips before anything breaks
2. **Use the site filter early** — it shows the app isn't static; it's querying live data
3. **Core Switch Failure is best for cross-domain** — network device down → Mirth degradation → HL7 impact
4. **Ransomware is best for shock value** — turns login success rate RED within 60 seconds
5. **Watch the auto-refresh** — no need to manually reload; indicators update every 30s
6. **Keep the Web UI on a second screen** — toggle scenarios without leaving the DT app
7. **If data looks stale** — check `kubectl get pods -n healthcare-gen`; generator pods may have restarted
8. **If the hex grid is all green** — that's normal baseline; activate Core Switch Failure to see a red tile
9. **After disabling a scenario** — Core Switch Failure recovers in ~2-3 min; Ransomware takes ~50 min due to failed login events persisting in the DQL query window

---

## App Navigation Reference

| Tab Label | Route | Page Component | Key Content |
|-----------|-------|----------------|-------------|
| **Overview** | `/` | Overview | Campus map, KPI cards, event distribution, correlation chart |
| **Security** | `/security` | SecurityCompliance | BTG events, failed logins, after-hours access, workstations |
| **Integration** | `/integration` | IntegrationHealth | Mirth Connect, HL7, FHIR API, ETL pipelines |
| **Network** | `/network` | NetworkHealth | Device honeycomb, CPU/memory charts, traffic in/out |
| **Epic Health** | `/epic` | EpicHealth | Login trends, clinical activity, audit events, sessions |
| **MyChart** | `/mychart` | MyChartPortal | Patient portal logins, messaging, scheduling, devices |
| **Sites** | `/sites` | SiteView | Per-site summary cards with drill-down |
| **Explore** | `/explore` | Explore | Raw log viewer and DQL sandbox |
