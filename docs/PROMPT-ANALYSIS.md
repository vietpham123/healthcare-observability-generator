# Prompt Analysis & Project Appendix

Comprehensive reference for the Healthcare Observability Generator project — covering architecture decisions, query patterns, threshold calibration, scenario correlation design, and lessons learned from AI-assisted development.

---

## 1. Project Genesis & Design Philosophy

### Core Concept
Build a **synthetic healthcare observability data platform** that generates temporally-correlated telemetry across two domains (Epic EHR + Network Infrastructure) and sends it to Dynatrace Grail for analysis via a custom Platform App.

### Design Principles
1. **Cross-domain correlation**: Every anomaly scenario generates events in both Epic and Network domains simultaneously, with shared timestamps and related identifiers
2. **Realistic baseline**: Normal operations produce varied, time-of-day-aware data that matches real hospital patterns (shift changes, admission waves, overnight quiet periods)
3. **DQL-first visualization**: The DT app queries Grail directly — no intermediate databases or caching layers
4. **Infrastructure-as-data**: The network topology is config-driven (YAML), not hardcoded — changing sites/devices changes all generated data
5. **Scenario injection**: Anomalies are injected as overlays on top of baseline, never replacing it

### Why Lawrence, Kansas?
- Central US location provides natural hub-and-spoke topology to satellite clinics
- Kansas geography (flat, rectangular) maps cleanly to equirectangular projection
- I-70 and I-35 corridor provides logical WAN routing paths
- Small enough metro to be plausible as a regional medical center, large enough for multiple satellite sites

---

## 2. Generator Architecture

### Epic SIEM Generator (`src/epic_generator/`)

**Tick model**: Every `EPIC_TICK_INTERVAL` seconds (default 10), the orchestrator generates a batch of events across all generators:

| Generator | Events Per Tick (baseline) | Key Fields |
|-----------|---------------------------|------------|
| SIEM | 5–15 | `E1Mid` (BCA_LOGIN_SUCCESS, FAILEDLOGIN, etc.), user, workstation, IP |
| Clinical | 3–8 | ORDER_TYPE, MEDICATION, NOTE_TYPE, department |
| HL7 | 2–6 | MSH.9 (ADT^A01, ORM^O01, ORU^R01, SIU^S12), ACK status |
| FHIR | 1–4 | HTTP method, resource path, status code, response time |
| MyChart | 2–5 | MYCHART_LOGIN, portal action, device type |
| ETL | 0–1 (periodic) | Job name, records processed, status, duration |

**Anomaly injection**: When `ACTIVE_SCENARIO` is set, the orchestrator calls scenario-specific injection functions that:
1. Increase error rates for affected generators
2. Add scenario-specific event types (e.g., BREAK_THE_GLASS for ransomware)
3. Modify user/patient/workstation distributions to create detectable patterns

### Network Generator (`src/network_generator/`)

**Tick model**: Every `NETWORK_TICK_INTERVAL` seconds (default 60), generates:

| Output Type | Events Per Tick (baseline) | Transport |
|-------------|---------------------------|-----------|
| Syslog | 10–30 per device | Log Ingest API |
| SNMP Metrics | 1 per device per metric | MINT protocol |
| NetFlow | 5–15 flow records | Log Ingest API |
| SNMP Traps | 0–2 (stochastic) | Events API |

**Topology-driven**: All output is generated from `config/hospital/topology.yaml`:
- 4 sites × 3–8 devices each = 22 total devices
- Device types: routers, switches, firewalls, load balancers, wireless controllers
- Each vendor (Cisco, Palo Alto, FortiGate, F5, Citrix, Aruba) has its own log format emulator

### Correlation Mechanism

Both generators share:
- **Timestamps**: Events from both domains for the same scenario use real `datetime.utcnow()`
- **IP addresses**: Scenario events reference the same IP ranges (e.g., `10.10.40.x` for IoMT VLAN)
- **Site codes**: `healthcare.site` and `network.device.site` use the same site code vocabulary
- **Scenario state**: `ACTIVE_SCENARIO` env var is set on both deployments simultaneously

---

## 3. DQL Query Design Patterns

### Filter Chain Pattern
All DT app queries follow a consistent pattern:
```dql
fetch logs
| filter dt.system.bucket == "observe_and_troubleshoot_apps_95_days"
| filter healthcare.pipeline == "healthcare-epic"
| filter <additional-domain-filter>
| <aggregation>
```

### Key Query Fixes (v1.14.3)

#### ETL Success Rate
**Problem**: RUNNING jobs were counted in the denominator but not as successes, dragging the rate to ~45%.
**Fix**: Added `| filter job_result != "RUNNING"` and counted `SUCCESS_WITH_WARNINGS` as success.

```dql
fetch logs
| filter ... AND healthcare.event_type == "ETL"
| filter job_result != "RUNNING"
| summarize total = count(),
    success = countIf(job_result == "SUCCESS" OR job_result == "SUCCESS_WITH_WARNINGS")
| fieldsAdd success_rate = 100.0 * success / total
```

#### MyChart Login Rate
**Problem**: Query divided MyChart successes by ALL failed logins (including non-MyChart), yielding ~0.83%.
**Fix**: Changed to volume-based metric — measures whether MyChart events are flowing.

```dql
fetch logs
| filter ... AND E1Mid == "MYCHART_LOGIN"
| makeTimeseries vol = count(), interval: 5m
| fieldsAdd val = arrayLast(vol)
```

#### Epic Login Success Rate
**Problem**: Only counted BCA_LOGIN_SUCCESS as success. Missed that LOGIN_BLOCKED and WPSEC_LOGIN_FAIL are normal in baseline (~17% of events).
**Fix**: Count all login events (SUCCESS + FAILEDLOGIN + BLOCKED), threshold set to 65% (baseline ~83%).

### Site Filter Injection
The `withSiteFilter()` utility handles three query types:
1. **`fetch logs`** → appends `| filter healthcare.site == "..."` after the first filter line
2. **`timeseries`** → injects `filter: {site == "..."}` before the first keyword parameter
3. **NetFlow** → uses `network.device.site` instead of `healthcare.site`

**Critical edge case**: Multiline `timeseries` queries (where `timeseries` is followed by a newline, not a space) need explicit detection. A simple `startsWith("timeseries ")` misses them.

---

## 4. Threshold Calibration

### Methodology
1. **Run baseline only** (no active scenario) for 10+ minutes
2. **Query each metric** via DQL and note the natural range
3. **Set green threshold** comfortably above the worst-case baseline value
4. **Set amber threshold** at a level that would indicate a mild scenario (e.g., ED Surge)
5. **Critical** = below amber — indicates a severe scenario (e.g., Ransomware)

### Baseline Measurements (April 2026)

| Metric | Baseline Value | Initial Threshold (green) | Issue | Final Threshold (green) |
|--------|---------------|--------------------------|-------|------------------------|
| Epic Login Success | ~83% | 85% | Baseline was CRITICAL | 65% |
| Auth Login Success | ~93% | 95% | Baseline was WARNING | 80% |
| FHIR Health Rate | ~90% | 98% | Baseline was CRITICAL | 85% |
| ETL Success Rate | ~86% (after fix) | 98% | Was 45% before fix | 88% |
| BTG Total Count | ~50/hr | 0 | Always CRITICAL | 200 |
| After-Hours BTG | ~10-20/hr | 0 | Always CRITICAL | 50 |
| Failed Login Count | ~80-120/30min | 0 | Always CRITICAL | 200 |
| MyChart Login | 100% (after fix) | 95% | Was 0.83% before fix | 95% |
| Network CPU | ~35% | 60% | Correct from start | 60% |

### Key Lesson
> Thresholds must be calibrated against **actual baseline data**, not against ideal values. A hospital naturally has ~7% login failure rate, ~10% FHIR error rate, and generates 50+ BTG events per hour. Setting thresholds at "perfection" (0 failures, 100% success) means the dashboard is always red.

---

## 5. Scenario Correlation Matrix

Each scenario produces a specific pattern across both generators. This matrix shows what changes from baseline:

### Ransomware Attack
| Domain | Change from Baseline | DT App Indicator |
|--------|---------------------|------------------|
| Epic SIEM | Login failures ↑ 300%, BTG events ↑ 500%, mass patient lookup | Login Success ↓ RED, BTG Count ↑ RED |
| Network | IPS alerts (FortiGate), C2 callbacks (Palo Alto), internal scanning | Network Events ↑, Critical Events ↑ |
| Integration | HL7 delivery drops, FHIR timeouts, ETL failures | HL7 ↓ RED, FHIR ↓ RED, ETL ↓ RED |

### ED Surge (Mass Casualty Incident)
| Domain | Change from Baseline | DT App Indicator |
|--------|---------------------|------------------|
| Epic SIEM | 15+ simultaneous registrations, STAT orders ↑ 400% | STAT Order Rate ↑ RED |
| Network | ED VLAN saturation, Citrix VServer spike | Network CPU ↑, Traffic ↑ |
| Integration | HL7 ADT message burst, FHIR response time ↑ | HL7 volume spike |

### MyChart Credential Stuffing
| Domain | Change from Baseline | DT App Indicator |
|--------|---------------------|------------------|
| Epic SIEM | 500+ failed logins, 8 successes, PHI export attempts | Login Success ↓ RED, Failed Count ↑ |
| Network | F5 ASM brute-force alerts, Citrix overload, PA threat logs | Network Events ↑ |
| Integration | Normal (attack targets portal, not integrations) | No change |

### Insider Threat (Snooping)
| Domain | Change from Baseline | DT App Indicator |
|--------|---------------------|------------------|
| Epic SIEM | After-hours BTG, VIP patient access, unusual workstation | After-Hours BTG ↑, Rapid Patient Access |
| Network | None (no network anomaly) | No change |
| Integration | None | No change |

---

## 6. Dynatrace Platform App — Strato Component Patterns

### SectionHealth with Tooltip (proven pattern)
```tsx
<Tooltip text={<TooltipContent />}>
  <div style={{ display: "inline-flex" }}>
    <Flex alignItems="center" gap={8}>
      <div style={{ width: 12, height: 12, borderRadius: "50%", background: color }} />
      <Text>{label}</Text>
    </Flex>
  </div>
</Tooltip>
```
**Why `<div>` wrapper?** Strato `<Tooltip>` requires a native DOM element child for ref forwarding. `<Flex>` is a React component that doesn't forward refs.

### Auto-Refresh with useDql
```tsx
const HEALTH_REFRESH_MS = 30_000;

const result = useDql(query, {
  refetchInterval: HEALTH_REFRESH_MS,
});
```
Each `SectionHealth` instance independently polls Grail every 30 seconds.

### Chart gapPolicy
All `TimeseriesChart` instances use `gapPolicy="connect"` to prevent visual breaks when data arrives irregularly.

### HoneycombChart Gotcha
`HoneycombChart` accepts only `number[]`, not object arrays. Extract the numeric values first:
```tsx
const values = records.map(r => r.cpu_avg as number);
```

---

## 7. Infrastructure & Deployment

### AKS Cluster
| Resource | Value |
|----------|-------|
| Cluster | `aks-healthcare-gen` |
| Resource Group | `VPEtrade_group` |
| Region | `southcentralus` |
| Node Pool | 2× Standard_B2ms |
| Namespace | `healthcare-gen` |

### Container Registry
- ACR: `vietregistry.azurecr.io`
- Images: `healthcare-gen/epic`, `healthcare-gen/network`, `healthcare-gen/webui`

### DT App Deployment
- Cannot deploy via SSH (browser SSO required)
- Working flow: edit locally → `npx dt-app deploy` → rsync back to VM
- Always bump `app.config.json` version before deploy (checksum mismatch otherwise)

### WebUI K8s Integration
- ServiceAccount with RBAC: `get/list/patch` on deployments in `healthcare-gen` namespace
- Injects `ACTIVE_SCENARIO` env var via K8s API patch
- Triggers `kubectl rollout restart` for clean restart with new scenario
- Handles race conditions with atomic patch-then-restart operations

---

## 8. Known Issues & Workarounds

| Issue | Workaround |
|-------|-----------|
| `npx dt-app deploy` via SSH | Deploy from local machine only |
| HoneycombChart won't accept objects | Map to `number[]` before passing |
| Strato Tooltip needs native DOM child | Wrap in `<div>` instead of `<Flex>` |
| Shell heredocs corrupt Python/JSON | Use base64-encoded Python scripts for file writes |
| GitHub SSH not configured on VM | Push from local clone |
| NetFlow data takes 60s to appear | Wait after generator restart |
| Canvas/SVG misalignment | Use uniform scaling matching `preserveAspectRatio` |

---

## 9. Query Reference

### Core Filter Constants
```dql
-- Shared bucket filter
dt.system.bucket == "observe_and_troubleshoot_apps_95_days"

-- Pipeline filters
healthcare.pipeline == "healthcare-epic"
healthcare.pipeline == "healthcare-network"

-- Special source
log.source == "netflow"
```

### Example Health Indicator Queries

**Epic Login Success Rate:**
```dql
fetch logs
| filter dt.system.bucket == "observe_and_troubleshoot_apps_95_days"
| filter healthcare.pipeline == "healthcare-epic"
| filter E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN" OR E1Mid == "LOGIN_BLOCKED" OR E1Mid == "WPSEC_LOGIN_FAIL"
| summarize total = count(), success = countIf(E1Mid == "BCA_LOGIN_SUCCESS")
| fieldsAdd success_rate = 100.0 * toDouble(success) / toDouble(total)
```

**ETL Success Rate:**
```dql
fetch logs
| filter dt.system.bucket == "observe_and_troubleshoot_apps_95_days"
| filter healthcare.pipeline == "healthcare-epic"
| filter healthcare.event_type == "ETL"
| filter job_result != "RUNNING"
| summarize total = count(),
    success = countIf(job_result == "SUCCESS" OR job_result == "SUCCESS_WITH_WARNINGS")
| fieldsAdd success_rate = 100.0 * toDouble(success) / toDouble(total)
```

**Network Device CPU:**
```dql
timeseries avg(healthcare.network.device.cpu.utilization), by: {device}
```

**BTG Count:**
```dql
fetch logs
| filter dt.system.bucket == "observe_and_troubleshoot_apps_95_days"
| filter healthcare.pipeline == "healthcare-epic"
| filter E1Mid == "BREAK_THE_GLASS"
| summarize btg_count = count()
```

---

## 10. File Map

| File | Purpose |
|------|---------|
| `src/epic_generator/orchestrator.py` | Epic generator main loop + anomaly injection |
| `src/network_generator/cli.py` | Network generator CLI entry point |
| `config/hospital/topology.yaml` | Network device inventory (4 sites, 22 devices) |
| `config/scenarios/*.json` | 8 correlated scenario definitions |
| `webui/app.py` | FastAPI control panel with K8s API |
| `dynatrace-apps/healthcare-health-monitoring/ui/app/queries.ts` | All DQL queries |
| `dynatrace-apps/healthcare-health-monitoring/ui/app/components/SectionHealth.tsx` | Health indicators |
| `dynatrace-apps/healthcare-health-monitoring/ui/app/pages/*.tsx` | All 9 app pages |
| `deploy/kubernetes/base/` | K8s manifests (Kustomize base) |
| `deploy/docker/Dockerfile.*` | Container build files |
