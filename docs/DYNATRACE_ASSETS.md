# Dynatrace Configuration Assets

> Complete inventory of all Dynatrace-side configuration required to deploy the Healthcare Observability Generator.  
> Last updated with alerts v1.0.0 and DT App v1.18.1.

---

## Table of Contents

1. [DT Platform App](#dt-platform-app)
2. [OpenPipeline Configuration](#openpipeline-configuration)
3. [Davis Anomaly Alerts](#davis-anomaly-alerts)
4. [MINT Metrics (Ingest)](#mint-metrics)
5. [DQL Queries (App)](#dql-queries)
6. [API Token Scopes](#api-token-scopes)
7. [Deployment Checklist](#deployment-checklist)

---

## DT Platform App

| Property | Value |
|----------|-------|
| **App Name** | Healthcare Health Monitoring |
| **App ID** | `my.healthcare.health.monitoring` |
| **Version** | 1.18.1 |
| **Environment** | `https://gyz6507h.sprint.apps.dynatracelabs.com` |
| **Source** | `dynatrace-apps/healthcare-health-monitoring/` |
| **Deploy Command** | `npx dt-app deploy` |

### Required App Scopes

| Scope | Purpose |
|-------|---------|
| `storage:logs:read` | Query Epic SIEM and network health logs from Grail |
| `storage:buckets:read` | Read log buckets |
| `storage:metrics:read` | Read SNMP device metrics and extracted health metrics |
| `storage:bizevents:read` | Query SNMP device inventory bizevents |
| `storage:events:read` | Read Davis problems and events |
| `davis:problems:read` | Display auto-detected health problems |

### App Pages

| Page | Description |
|------|-------------|
| Overview | System-wide KPIs, activity timeline, event distribution |
| Epic Health | Login/auth metrics, clinical orders, department activity |
| Authentication Health | Login success rates, workstation analysis, LDAP |
| Integration Health | HL7 v2.x messages, FHIR API, ETL jobs, Mirth Connect |
| Security & Compliance | BTG events, failed logins, firewall denies, lateral movement |
| Network Health | Device fleet, CPU/memory, syslog events, vendor distribution |
| Site View | 2×3 grid of all 6 sites with drill-down |
| MyChart Portal | Patient portal analytics |
| Explore | Raw log viewer for Epic, Network, NetFlow |

---

## OpenPipeline Configuration

| Property | Value |
|----------|-------|
| **Pipeline ID** | `pipeline_Healthcare_Observability_5001` |
| **Settings Object ID** | `vu9U3hXa3q0AAAABACNidWlsdGluOm9wZW5waXBlbGluZS5sb2dzLnBpcGVsaW5lcwAGdGVuYW50AAZ0ZW5hbnQAJDdkODY2YjUxLTRhODUtMzYwMC05OGNkLWY4ZDk3MTQ3NjdhML7vVN4V2t6t` |
| **Schema** | `builtin:openpipeline.logs.pipelines` |

### Processors (5 Total)

Each processor assigns `healthcare.site` based on hex-aware field character distribution.

| # | Processor ID | Log Type | Distribution Field |
|---|-------------|----------|-------------------|
| 1 | `processor_Epic_SIEM_XML_5001` | Epic SIEM (XML) | `EMPID` |
| 2 | `processor_Epic_ETL_JSON_5002` | Epic ETL (JSON) | `records_processed` |
| 3 | `processor_FHIR_API_Access_5003` | FHIR API | `correlation_id` |
| 4 | `processor_HL7_Message_5004` | HL7 v2.x | `hl7_msg_control_id` |
| 5 | `processor_FHIR_Resource_5005` | FHIR Resources | `fhir_resource_id` |

### Site Distribution Logic

Character-based distribution using `endsWith()` on the distribution field:

| Last Character(s) | Assigned Site | Share |
|-------------------|--------------|-------|
| `0`, `1`, `2`, `a`, `b` | `kcrmc-main` | ~31% |
| `3`, `4`, `c` | `tpk-clinic` (→ oak-clinic) | ~19% |
| `5`, `6`, `d` | `wch-clinic` (→ wel-clinic) | ~19% |
| `7`, `8`, `9`, `e`, `f` | `lwr-clinic` (→ bel-clinic) | ~31% |

> **Note**: `tpk-clinic`, `wch-clinic`, `lwr-clinic` are the OpenPipeline-assigned codes.  
> The DT App maps them to display names via `SITE_ALIAS` in `queries.ts`.

### Network & NetFlow Site Assignment

Network and NetFlow logs carry `healthcare.site` and `network.device.site` set at generator time (from `topology.yaml`), not via OpenPipeline.

---

## Davis Anomaly Alerts

### Log-Based Alerts (`builtin:logmonitoring.log-events`)

#### 1. Healthcare - Failed Login Burst

| Property | Value |
|----------|-------|
| **Scenario** | Ransomware Attack (Phase 2: Credential Harvesting) |
| **Category** | Security |
| **DQL Query** | `E1Mid == "FAILEDLOGIN" AND isNotNull(dt.source.generator)` |
| **Davis Title** | Epic Failed Login Burst Detected |
| **Baseline** | ~3 FAILEDLOGIN per 5 minutes |
| **Fires When** | FAILEDLOGIN events spike (10x+ during ransomware) |

#### 2. Healthcare - Firewall Threat Burst

| Property | Value |
|----------|-------|
| **Scenario** | Ransomware Attack (Phases 1+3: Recon, Lateral Movement) |
| **Category** | Security |
| **DQL Query** | `healthcare.pipeline == "healthcare-network" AND network.event.type == "THREAT"` |
| **Davis Title** | Network Firewall Threat Burst Detected |
| **Baseline** | ~6 THREAT events per 5 minutes |
| **Fires When** | IPS/IDS triggers spike from Palo Alto, FortiGate |

#### 3. Healthcare - Break-the-Glass Anomaly

| Property | Value |
|----------|-------|
| **Scenario** | Insider Threat - After-Hours Snooping |
| **Category** | Compliance |
| **DQL Query** | `matchesValue(E1Mid, "AC_BREAK_THE_GLASS*")` |
| **Davis Title** | Break-the-Glass Activity Spike |
| **Baseline** | Scattered BTG events during business hours |
| **Fires When** | Concentrated burst of BTG events (especially after-hours) |

#### 4. Healthcare - Network Interface Errors

| Property | Value |
|----------|-------|
| **Scenario** | Core Switch Failure |
| **Category** | Infrastructure |
| **DQL Query** | `healthcare.pipeline == "healthcare-network" AND network.event.type == "INTERFACE" AND matchesPhrase(content, "down")` |
| **Davis Title** | Network Interface Error Events Detected |
| **Baseline** | Occasional interface flaps |
| **Fires When** | Core switch fails → cascading interface downs |

#### 5. Healthcare - HL7 Message Delivery Failure

| Property | Value |
|----------|-------|
| **Scenario** | HL7 Interface Failure |
| **Category** | Integration |
| **DQL Query** | `isNotNull(hl7_msg_type) AND (matchesPhrase(content, "NACK") OR matchesPhrase(content, "ERROR") OR matchesPhrase(content, "timeout") OR matchesPhrase(content, "rejected"))` |
| **Davis Title** | HL7 Message Delivery Failure |
| **Baseline** | Zero NACKs/errors during normal operations |
| **Fires When** | HL7 interface disruption causes delivery failures |

#### 6. Healthcare Obs Gen - Error Events (Pre-existing)

| Property | Value |
|----------|-------|
| **Scenario** | Any (generator health) |
| **Category** | Operational |
| **DQL Query** | `dt.source.generator=="healthcare-obs-gen-v2" and loglevel=="ERROR"` |
| **Davis Title** | Healthcare Generator Error |
| **Fires When** | Generator itself produces ERROR-level logs |

### Metric-Based Alerts (`builtin:anomaly-detection.metric-events`)

#### 7. Healthcare - Mirth Queue Backup

| Property | Value |
|----------|-------|
| **Scenario** | HL7 Interface Failure |
| **Category** | Integration |
| **Metric Key** | `healthcare.mirth.channel.queue.depth` |
| **Threshold** | > 50 (static) |
| **Model** | 3 violating samples out of 5, 3 dealerting |
| **Davis Title** | Mirth Connect Queue Backup |
| **Baseline** | Queue depth ~2-5 messages |
| **Fires When** | HL7 interface failure causes message backlog |

### Alert → Scenario Cross-Reference

| Scenario | Alerts That Fire |
|----------|-----------------|
| **Normal Day Shift** | None (baseline) |
| **Ransomware Attack** | Failed Login Burst + Firewall Threat Burst |
| **Insider Threat Snooping** | Break-the-Glass Anomaly |
| **HL7 Interface Failure** | HL7 Message Delivery Failure + Mirth Queue Backup |
| **Core Switch Failure** | Network Interface Errors |

---

## MINT Metrics

Metrics ingested via the DT OTLP metrics endpoint from the generators:

| Metric Key | Type | Dimensions | Source |
|------------|------|------------|--------|
| `healthcare.network.device.cpu.utilization` | Gauge | device, site, vendor | Network generator |
| `healthcare.network.device.memory.utilization` | Gauge | device, site, vendor | Network generator |
| `healthcare.network.if.traffic.in.bytes` | Counter | device, site | Network generator |
| `healthcare.network.if.traffic.out.bytes` | Counter | device, site | Network generator |
| `healthcare.mirth.channel.queue.depth` | Gauge | channel_name | Epic generator |
| `healthcare.mirth.channel.messages.sent` | Counter | channel_name | Epic generator |
| `healthcare.mirth.channel.messages.received` | Counter | channel_name | Epic generator |
| `healthcare.mirth.channel.messages.errors` | Counter | channel_name | Epic generator |
| `healthcare.mirth.channel.status` | Gauge | channel_name | Epic generator |

---

## DQL Queries

The DT App uses **65+ DQL queries** defined in `ui/app/queries.ts`. Key filter constants:

```
BUCKET = 'dt.system.bucket == "observe_and_troubleshoot_apps_95_days"'
EPIC_FILTER = BUCKET + ' AND healthcare.pipeline == "healthcare-epic"'
NETWORK_FILTER = BUCKET + ' AND healthcare.pipeline == "healthcare-network"'
NETFLOW_FILTER = 'log.source == "netflow"'
```

### Query Categories

| Category | Count | Key Queries |
|----------|-------|-------------|
| **Overview KPIs** | 9 | Login success rate, HL7 delivery, FHIR health, device up ratio |
| **Overview Charts** | 2 | System activity timeline, event distribution |
| **Campus/Site** | 3 | Site health summary, network devices by site |
| **Epic Health** | 5 | Login volume, success rate trend, login by site, security events, SIEM by type |
| **Network Health** | 8 | Device CPU/mem/traffic over time, log timeline, device list, vendor dist |
| **NetFlow** | 7 | Total flows, timeline, protocol dist, top ports, top countries |
| **Integration (HL7)** | 3 | HL7 volume, message breakdown, recent messages |
| **Integration (FHIR)** | 5 | Request rate, status dist, error rate, response time percentiles, slow requests |
| **Integration (ETL)** | 4 | Job status, duration trends, failed jobs, success rate |
| **Mirth Connect** | 5 | Queue depth, message rate, error rate, channel health, channel summary |
| **Authentication** | 10 | Success vs failure, error breakdown, context/client/source dist, workstation analysis |
| **Security/Detection** | 7 | Network severity, critical events, port security, lateral scan, rapid patient access, BTG |
| **Correlation** | 2 | Epic-network correlation, events by site |
| **Site Drill-Down** | 5 | Per-site HL7, error rate, netflow, top events (parameterized) |
| **Explore** | 4 | Raw Epic, network, netflow events, active problems |

---

## API Token Scopes

### Data Ingest Token (for generators)

| Scope | Purpose |
|-------|---------|
| `logs.ingest` | Ingest Epic SIEM, HL7, FHIR, ETL, network syslog logs |
| `metrics.ingest` | Ingest MINT metrics (device CPU, memory, traffic, Mirth) |
| `bizevents.ingest` | Ingest SNMP device inventory events |

### Platform Token (for DT App queries)

| Scope | Purpose |
|-------|---------|
| `storage:logs:read` | DQL log queries |
| `storage:metrics:read` | DQL timeseries queries |
| `storage:events:read` | Davis event queries |

### Classic API Token (for Settings management)

| Scope | Purpose |
|-------|---------|
| `settings.read` | Read alert definitions, OpenPipeline config |
| `settings.write` | Create/update alerts, OpenPipeline config |
| `WriteConfig` | Legacy config management |
| `ReadConfig` | Legacy config read |

---

## Deployment Checklist

### Prerequisites

- [ ] Dynatrace SaaS/Managed environment with Grail enabled
- [ ] OpenPipeline access (Logs pipeline management)
- [ ] API tokens with required scopes (see above)
- [ ] Node.js 18+ (for DT App deployment)

### Step 1: Configure OpenPipeline

1. Import the healthcare pipeline via Settings API:
   ```
   PUT /api/v2/settings/objects/{pipelineObjectId}
   ```
2. Verify 5 processors are active in **OpenPipeline → Logs → Healthcare Observability**
3. Confirm site distribution: run DQL `fetch logs | filter healthcare.pipeline == "healthcare-epic" | summarize count(), by:{healthcare.site}`

### Step 2: Deploy Alerts

Create all 7 alerts via Settings API:

```bash
# Log events (5 alerts)
POST /api/v2/settings/objects
# Schema: builtin:logmonitoring.log-events
# Scope: environment

# Metric events (1 alert)  
POST /api/v2/settings/objects
# Schema: builtin:anomaly-detection.metric-events
# Scope: environment
```

Verify: **Settings → Anomaly Detection → Custom Events** — should show 7 Healthcare alerts, all ON.

### Step 3: Deploy DT App

```bash
cd dynatrace-apps/healthcare-health-monitoring
npm install
npx dt-app deploy
```

### Step 4: Start Generators

```bash
# AKS deployment
kubectl apply -k deploy/kubernetes/overlays/aks/

# Or Docker Compose
docker-compose up -d
```

### Step 5: Verify Data Flow

1. **Logs**: DQL `fetch logs | filter isNotNull(healthcare.pipeline) | summarize count(), by:{healthcare.pipeline}`
2. **Metrics**: DQL `timeseries cpu = avg(healthcare.network.device.cpu.utilization), interval:5m`
3. **Alerts**: Activate a scenario via WebUI → check **Problems** page for Davis alerts
4. **App**: Open Healthcare Health Monitoring app → verify all pages load with data

---

## File Reference

| Asset | Location |
|-------|----------|
| DT App source | `dynatrace-apps/healthcare-health-monitoring/` |
| App config | `dynatrace-apps/healthcare-health-monitoring/app.config.json` |
| DQL queries | `dynatrace-apps/healthcare-health-monitoring/ui/app/queries.ts` |
| OpenPipeline backup | Settings API object (see Pipeline ID above) |
| Alert definitions | Settings API objects (see Alert section above) |
| Network topology | `config/hospital/topology.yaml` |
| Scenario configs | `config/scenarios/*.json` / `config/scenarios/*.yaml` |
| Kubernetes manifests | `deploy/kubernetes/` |
