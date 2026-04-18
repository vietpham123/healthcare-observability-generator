# Demo Flow: Healthcare Observability Platform

Step-by-step walkthrough for demonstrating the Healthcare Observability Generator and the Dynatrace Platform App. Designed for a 20–30 minute live demo.

---

## Prerequisites

| Component | Status Check |
|-----------|-------------|
| AKS generators running | `kubectl get pods -n healthcare-gen` — all pods `Running` |
| Data flowing to DT | Grail query: `fetch logs \| filter healthcare.pipeline == "healthcare-epic" \| sort timestamp desc \| limit 5` |
| DT Platform App deployed | Open: `https://{env-id}.apps.dynatracelabs.com/ui/apps/my.healthcare.health.monitoring` |
| Web UI available (optional) | `http://{vm-ip}:8080` for scenario toggling |

---

## Part 1: The Data Pipeline (5 min)

### 1.1 — Show the Generators

Open the AKS cluster in Dynatrace (Kubernetes app):
- **Namespace**: `healthcare-gen`
- **Workloads**: `epic-generator`, `network-generator`, `webui`
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

Point out key attributes: `healthcare.site`, `healthcare.event_type`, `epic.user_id`, `content`

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

Navigate to: **Apps → Healthcare Health Monitoring → Overview**

### 2.2 — Campus Map

Point out:
- **Kansas map** — real geographic projection with I-70, I-35 highways, county grid, reference cities
- **Hospital hub** (Lawrence) — large green icon at the center of Kansas along I-70
- **Satellite clinics** — Oakley (west), Wellington (south), Belleville (north)
- **NetFlow animation** — watch the green dots travel from Lawrence to satellite clinics
- **Health badges** — green = healthy (>95% login success), amber = degraded, red = critical

> "This is a live map. The dots are actual NetFlow records from the last 30 minutes. Each dot represents aggregated bytes flowing between Lawrence and a satellite site."

### 2.3 — KPI Cards

Below the map:
- **Login Success Rate** — percentage from Epic SIEM
- **Active Sessions** — current Hyperspace sessions
- **Clinical Events** — orders, notes, results
- **HL7 Messages** — interface engine throughput
- **Network Devices** — count of monitored devices
- **Network Events** — syslog event count

### 2.4 — Site Filter

Click a site button (e.g., **Oakley Rural Health**):
- All KPIs filter to that site
- Map highlights the selected site
- All charts on the page update

> "Every page in the app has this site filter. It works for both log-based queries and metric-based timeseries."

---

## Part 3: Epic Health Deep Dive (5 min)

### 3.1 — Navigate to Epic Health

Click **Epic Health** tab.

### 3.2 — Walk Through Charts

| Chart | What to Show |
|-------|-------------|
| **Login Trend** (TimeseriesChart) | Time-of-day curve — peaks at shift changes (7am, 3pm, 11pm) |
| **Login Success Rate** (TimeseriesChart) | Should be ~97-99% during normal operations |
| **Event Distribution** (DonutChart) | Breakdown: SIEM, Clinical, HL7, FHIR, MyChart |
| **Audit Timeline** (CategoricalBarChart) | HIPAA audit events over time |
| **Session Analysis** | Active session count, average duration |

### 3.3 — Drill by Site

Select **Wellington Care Center** — watch all charts filter to just that clinic's data.

> "This is the Epic application layer — login health, clinical activity, and audit compliance. The next page shows the infrastructure underneath."

---

## Part 4: Network Health (5 min)

### 4.1 — Navigate to Network Health

Click **Network Health** tab.

### 4.2 — Device Fleet Honeycomb

The honeycomb shows all network devices colored by CPU utilization:
- **Green** cells = healthy (<60% CPU)
- **Amber** cells = elevated (60-80%)
- **Red** cells = critical (>80%)

> "Each cell is a network device — routers, switches, firewalls, load balancers. This is SNMP data sent as MINT metrics."

### 4.3 — KPI Cards

- **Devices Up** — count from latest SNMP poll
- **Avg CPU** — fleet-wide average
- **Avg Memory** — fleet-wide average
- **Network Events** — syslog count (last 30 min)
- **NetFlow Records** — flow record count

### 4.4 — Traffic Charts

| Chart | What to Show |
|-------|-------------|
| **CPU by Device** (TimeseriesChart) | Individual device CPU lines, faceted by device name |
| **Memory by Device** (TimeseriesChart) | Same for memory |
| **Traffic In** (TimeseriesChart) | Ingress bytes/sec per device |
| **Traffic Out** (TimeseriesChart) | Egress bytes/sec per device |

### 4.5 — Filter by Site

Select **Oakley Rural Health** — see only Oakley's 3-4 devices in the honeycomb and charts.

> "This is the network infrastructure layer. When something goes wrong here, it cascades up to the Epic layer — we'll show that next."

---

## Part 5: Integration Health (3 min)

### 5.1 — Navigate to Integration Health

Click **Integration Health** tab.

### 5.2 — Key Metrics

| Metric | What It Shows |
|--------|--------------|
| **HL7 Delivery Rate** | Messages per minute through the interface engine (ADT, ORM, ORU, SIU) |
| **HL7 Error Rate** | NACKs and timeouts — should be <1% normally |
| **FHIR Response Time** | API latency for FHIR R4 calls (Patient, Encounter, Observation) |
| **ETL Pipeline Status** | Data warehouse extract jobs — completion rate, row counts |

> "This is the integration layer — HL7 messages, FHIR APIs, and ETL pipelines. In a real Epic environment, failures here mean data stops flowing between systems."

---

## Part 6: Correlated Scenario (5 min)

This is the highlight of the demo — showing cross-domain correlation.

### 6.1 — Trigger a Scenario

Open the Web UI (`http://{vm-ip}:8080`) and activate **Ransomware Attack**.

### 6.2 — Watch the Cascade

**Network Health** page (check first):
1. FortiGate IPS alerts appear in Network Events
2. Palo Alto threat logs show C2 callback traffic
3. Device CPU spikes on firewalls
4. NetFlow shows unusual internal scanning patterns

**Epic Health** page (check second):
1. Login failures spike (infrastructure degraded)
2. Break-the-glass events appear (emergency access)
3. Mass patient record lookups (data exfiltration attempt)

**Integration Health** page (check third):
1. HL7 delivery rate drops
2. FHIR response times spike
3. ETL jobs start failing

### 6.3 — Correlation Narrative

> "Notice the timeline: the network attack started at T+0 with IPS alerts. Two minutes later, Epic logins started failing because the infrastructure was degraded. The security team triggered break-the-glass access at T+5. By T+10, all integration feeds were disrupted. In a real SOC, you'd need this cross-domain view to understand that the Epic outage was caused by a network security incident, not an application problem."

### 6.4 — Deactivate Scenario

Return to Web UI, deactivate **Ransomware Attack**. Systems return to normal within 2-3 minutes.

---

## Part 7: Site View (2 min)

### 7.1 — Navigate to Site View

Click **Site View** tab.

### 7.2 — Site Cards

Each site has a card showing:
- Site name, code, bed count, and profile type
- Login success rate (last 30 min)
- Active sessions
- Clinical events
- Network devices + average CPU

> "This is the per-site summary. A hospital IT director would use this to compare sites at a glance."

---

## Part 8: Explore (2 min)

### 8.1 — Navigate to Explore

Click **Explore** tab.

### 8.2 — Free-form DQL

Run any DQL query against the ingested data:

```dql
fetch logs
| filter dt.system.bucket == "observe_and_troubleshoot_apps_95_days"
| filter healthcare.pipeline == "healthcare-epic"
| filter healthcare.event_type == "SIEM"
| filter matchesPhrase(content, "FAILED")
| sort timestamp desc
| limit 50
```

> "This is a DQL sandbox. Anything you can query in Grail, you can query here."

---

## Scenario Quick Reference

| Scenario | Duration | Key Visuals |
|----------|----------|-------------|
| **Normal Day Shift** | Always on | Smooth curves, green badges |
| **ED Surge** | 10-15 min | Login spike, ED network saturation |
| **Ransomware** | 10-15 min | Red badges, IPS alerts, C2 traffic, break-the-glass |
| **HL7 Interface Failure** | 5-10 min | HL7 NACKs, switch port err-disable |
| **MyChart Credential Stuffing** | 5-10 min | 500+ login failures, F5 brute force |
| **Insider Threat** | 5-10 min | After-hours access, VIP snooping (Epic only) |

---

## Demo Tips

1. **Start with data** — showing raw Grail queries first establishes credibility; the app is just a visualization layer
2. **Use the site filter early** — it shows the app isn't static; it's querying live data
3. **End with a scenario** — the cross-domain correlation is the "wow" moment
4. **Keep the Web UI on a second screen** — toggle scenarios without leaving the DT app
5. **If data looks stale** — check `kubectl get pods -n healthcare-gen`; generator pods may have restarted
6. **If the map has no dots** — NetFlow data takes ~60 seconds to appear after generators start
