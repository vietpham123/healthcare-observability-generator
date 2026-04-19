# Demo Flow: Healthcare Observability Platform

Step-by-step walkthrough for demonstrating the Healthcare Observability Generator and the Dynatrace Platform App. Designed for a 20–30 minute live demo.

---

## Prerequisites

| Component | Status Check |
|-----------|-------------|
| AKS generators running | `kubectl get pods -n healthcare-gen` — all pods `Running` |
| Data flowing to DT | Grail query: `fetch logs \| filter healthcare.pipeline == "healthcare-epic" \| sort timestamp desc \| limit 5` |
| DT Platform App deployed | Open: `https://{env-id}.apps.dynatracelabs.com/ui/apps/my.healthcare.health.monitoring` |
| Web UI available | `http://172.206.131.122` for scenario toggling |
| Health indicators green | All SectionHealth pills showing green on Overview page |

---

## Part 1: The Data Pipeline (5 min)

### 1.1 — Show the Generators

Open the AKS cluster in Dynatrace (Kubernetes app):
- **Namespace**: `healthcare-gen`
- **Workloads**: `epic-generator` (v1.0.4), `network-generator`, `webui` (v2.2.0)
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

Navigate to: **Apps → Healthcare Health Monitoring → Overview**

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
- **Login Success Rate** — percentage from Epic SIEM
- **Active Sessions** — current Hyperspace sessions
- **Clinical Events** — orders, notes, results
- **HL7 Messages** — interface engine throughput
- **Network Devices** — count of monitored devices
- **Network Events** — syslog event count

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

Click **Network Health** tab. Note health indicators: Avg CPU, Device Up Ratio.

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

Click **Integration Health** tab. Note health indicators: HL7 Delivery, FHIR Health, ETL Success.

### 5.2 — Key Metrics

| Metric | What It Shows |
|--------|--------------|
| **HL7 Delivery Rate** | Messages per minute through the interface engine (ADT, ORM, ORU, SIU) |
| **HL7 Error Rate** | NACKs and timeouts — should be <1% normally |
| **FHIR Response Time** | API latency for FHIR R4 calls (Patient, Encounter, Observation) |
| **ETL Pipeline Status** | Data warehouse extract jobs — completion rate (excludes RUNNING jobs) |

> "This is the integration layer — HL7 messages, FHIR APIs, and ETL pipelines. In a real Epic environment, failures here mean data stops flowing between systems."

---

## Part 6: Security & Compliance (3 min)

### 6.1 — Navigate to Security & Compliance

Click **Security & Compliance** tab. Note health indicators: Login Success, Auth Success, BTG Count, After-Hours BTG, Failed Login Count.

### 6.2 — Key Metrics

| Metric | What It Shows |
|--------|--------------|
| **Break-the-Glass Count** | Emergency access events (normal: ~50/hr in a hospital) |
| **After-Hours BTG** | BTG events outside 6 AM – 10 PM (higher risk) |
| **Failed Login Analysis** | Login failure patterns by user, workstation, time |
| **Login Success Rates** | Both Epic-wide and BCA authentication layer |

> "In a HIPAA-regulated environment, BTG events are expected but monitored. A spike means either a real emergency or a potential insider threat."

---

## Part 7: MyChart Portal (2 min)

### 7.1 — Navigate to MyChart Portal

Click **MyChart Portal** tab. Note health indicator: MyChart Login.

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

Open the Web UI (`http://172.206.131.122`) and activate **Ransomware Attack**.

### 8.2 — Watch the Health Indicators Change

Within 30-60 seconds (SectionHealth auto-refreshes every 30s):
- **Overview**: Login Success → RED, FHIR → RED
- **Security & Compliance**: BTG Count → RED, Failed Logins → RED
- **Integration Health**: HL7 → RED, ETL → RED
- **Network Health**: CPU may spike on firewall devices

### 8.3 — Watch the Cascade on Charts

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

### 8.4 — Correlation Narrative

> "Notice the timeline: the network attack started at T+0 with IPS alerts. Two minutes later, Epic logins started failing because the infrastructure was degraded. The security team triggered break-the-glass access at T+5. By T+10, all integration feeds were disrupted. In a real SOC, you'd need this cross-domain view to understand that the Epic outage was caused by a network security incident, not an application problem."

### 8.5 — Deactivate Scenario

Return to Web UI, deactivate **Ransomware Attack**.
- **Important**: Ransomware recovery takes ~50 minutes (not 2-3 min) because ~1450 failed logins persist in the DQL query window
- The 30-second auto-refresh means you'll see the transition in real time

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

## Part 10: Site View (2 min)

### 10.1 — Navigate to Site View

Click **Site View** tab.

### 10.2 — Site Cards

Each site has a card showing:
- Site name, code, bed count, and profile type
- Login success rate (last 30 min)
- Active sessions
- Clinical events
- Network devices + average CPU

> "This is the per-site summary. A hospital IT director would use this to compare sites at a glance."

---

## Scenario Quick Reference

| Scenario | Duration | Key Visuals | Pages to Watch |
|----------|----------|-------------|----------------|
| **Normal Day Shift** | Always on | Smooth curves, green indicators | Overview |
| **ED Surge** | 10-15 min | STAT orders spike, ED network saturation | Epic, Network |
| **Ransomware** | 10-15 min | Red indicators everywhere, IPS alerts, BTG spike | Security, Network, Integration |
| **Epic Outage (Network)** | 10-15 min | Network DOWN → Epic login failures | Network, Epic |
| **HL7 Interface Failure** | 5-10 min | HL7 NACKs, switch err-disable | Integration, Network |
| **IoMT Device Compromise** | 5-10 min | FHIR anomaly, port security alerts | Integration, Network |
| **MyChart Credential Stuffing** | 5-10 min | 500+ login failures, F5 alerts | MyChart, Security, Network |
| **Insider Threat** | 5-10 min | After-hours BTG, VIP snooping | Security |

---

## Demo Tips

1. **Start with health indicators** — hover over the green pills to show tooltips before anything breaks
2. **Use the site filter early** — it shows the app isn't static; it's querying live data
3. **End with a scenario** — the cross-domain correlation is the "wow" moment
4. **Watch the auto-refresh** — no need to manually reload; indicators update every 30s
5. **Keep the Web UI on a second screen** — toggle scenarios without leaving the DT app
6. **If data looks stale** — check `kubectl get pods -n healthcare-gen`; generator pods may have restarted
7. **If the map has no dots** — NetFlow data takes ~60 seconds to appear after generators start
8. **After disabling a scenario** — recovery depends on intensity: ED Surge/IoMT/HL7 recover in ~5 min; Ransomware takes ~50 min due to burst event persistence in DQL query window


---

## Appendix: Verified Scenario Test Results (April 2026)

Comprehensive testing of all 8 scenarios via WebUI API with DQL health indicator verification.

### Impact Summary

| Scenario | Epic Login Impact | Failed Logins Impact | FHIR/ETL Impact | Network Impact | Recovery Time |
|----------|------------------|---------------------|-----------------|----------------|---------------|
| ED Surge | Minimal shift | No change | No change | Volume increase | ~5 min |
| Ransomware | 83% → 44% RED | 120 → 1449 RED | No change | No change | ~50 min |
| MyChart Credential Stuffing | No attack patterns | No change | No change | No change | ~5 min |
| HL7 Interface Failure | No change | No change | No change | Syslog events | ~5 min |
| Epic Outage (Network) | No change | No change | No change | CPU 27→32% | ~5 min |
| IoMT Device Compromise | No change | No change | No change | Minimal | ~5 min |
| Insider Threat | No change | No change | No change | No change | ~10 min |
| Normal Day Shift | Baseline | Baseline | Baseline | Baseline | N/A |

### Scenario Categories

**High-impact (shifts Epic health indicators):**
- Ransomware Attack — the only scenario that dramatically moves percentage metrics

**Medium-impact (detectable through specific indicators):**
- Insider Threat — generates BTG events (AC_BREAK_THE_GLASS_ACCESS + SECURE)
- ED Surge — generates volume increase and ORDER_ENTRY events

**Network-only (no Epic-side impact):**
- HL7 Interface Failure, Epic Outage, IoMT Device Compromise — all map to `normal_shift` for Epic

**Activity-based (no anomaly patterns):**
- MyChart Credential Stuffing — generates normal peak MyChart activity, NOT attack patterns
- Normal Day Shift — baseline behavior confirmation

### Demo Recommendations

1. **For maximum visual impact**: Use **Ransomware Attack** — it turns multiple health indicators RED within 60 seconds
2. **For quick demos**: Use **Insider Threat** — BTG events appear quickly and recover in ~10 minutes
3. **Avoid for short demos**: **Ransomware** — recovery takes ~50 minutes, making back-to-back demos difficult
4. **Show the contrast**: Activate ED Surge first (shows volume increase), then Ransomware (shows percentage shift) — demonstrates two different anomaly detection patterns
