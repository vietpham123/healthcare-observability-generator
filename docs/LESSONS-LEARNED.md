# Lessons Learned: Building a Dynatrace Platform App with AI

A comprehensive record of patterns, pitfalls, and proven strategies from building the **Healthcare Health Monitoring** DT platform app (v1.0 → v1.4.8) using AI-assisted development. This document is intended to serve as the foundation for an **AI skill for DT app development**.

---

## 1. Project Setup & Toolchain

### What Worked
- **`dt-app` CLI** (`npx dt-app init`, `build`, `deploy`) is the standard toolchain. Version 1.8.1 is stable.
- `app.config.json` defines the app manifest: id, name, version, scopes, and environment URL.
- React 18 + TypeScript 5.9 is the standard stack. Strato design system components are imported from `@dynatrace/strato-components/*`.

### Key Lessons
| Lesson | Details |
|--------|---------|
| **Version bumps are mandatory** | Deploying the same version with different code fails (checksum mismatch). Always increment `app.config.json` version before `npx dt-app deploy`. |
| **Deploy requires local browser** | `npx dt-app deploy` opens a browser for SSO authentication. It cannot work via SSH or headless. Use `rsync` to pull code locally, then deploy from a machine with a browser. |
| **`npx dt-app dev`** | Runs a local dev server with hot reload. Useful for iteration but requires the DT environment to be reachable. |

### Scopes
The app needs explicit scopes in `app.config.json` for every data type it reads:
```json
{ "name": "storage:logs:read" },
{ "name": "storage:buckets:read" },
{ "name": "storage:metrics:read" },
{ "name": "storage:bizevents:read" },
{ "name": "storage:events:read" },
{ "name": "davis:problems:read" }
```

---

## 2. Strato Components — What Works and What Doesn't

### Chart Imports
**Always** import charts from `@dynatrace/strato-components/charts`, NOT `@dynatrace/strato-components-preview/charts`. The preview package has different APIs and will break builds.

### Component-Specific Gotchas

| Component | Issue | Solution |
|-----------|-------|----------|
| **TimeseriesChart** | Data gaps show as breaks in lines | Add `gapPolicy="connect"` prop |
| **HoneycombChart** | Supports categorical and numeric modes | Categorical: `{ name, value: string }[]` with `colorScheme` map; Numeric: `number[]` |
| **Select / FilterBar** | `Select.Content` wrapper required around `Select.Option` children; FilterBar expects specific structures | Bypass entirely — use button-based toggle filters instead. Simpler, more reliable. |
| **DonutChart** | Needs `{ name, value }[]` format | Use a helper function `toDonutData(records)` |
| **CategoricalBarChart** | Needs `{ name, value }[]` format | Use a helper function `toBarData(records)` |

### TimeseriesChart Data Format
The `useDql` hook returns raw Grail records. For timeseries charts, use a `toTimeseries()` helper that converts `{ timeframe, interval, ... }` records into the format TimeseriesChart expects. This is NOT documented well — you need to inspect the component's TypeScript types.

### Layout Components
- `Flex`, `Surface`, `TitleBar` from `@dynatrace/strato-components/layouts`
- `Text` from `@dynatrace/strato-components/typography`
- `ProgressCircle` from `@dynatrace/strato-components/content`

---

## 3. DQL Queries — Critical Patterns

### Query Types and Their Behaviors

| Query Type | Starts With | Returns | Filter Method |
|------------|-------------|---------|---------------|
| Log queries | `fetch logs` | Records with named fields | `\| filter field == "value"` |
| Metric queries | `timeseries` | Timeseries arrays | `filter: {dimension == "value"}` parameter |
| Aggregated logs | `fetch logs ... \| makeTimeseries` | Timeseries from log counts | `\| filter` before `\| makeTimeseries` |

### Site Filtering Strategy

The `withSiteFilter(query, siteCode, kind)` function handles injection for all query types:

1. **Log queries**: Finds the first `| filter` line and appends a new filter line after it
2. **Timeseries queries**: Detects `timeseries ` or `timeseries\n` at the start and injects `filter: {site == "..."}` before the first keyword parameter (`by:`, `from:`, `interval:`)
3. **NetFlow queries**: Uses `network.device.site` instead of `healthcare.site`

**Critical discovery**: Multiline `timeseries` queries (where `timeseries` is followed by a newline, not a space) need explicit detection. A simple `startsWith("timeseries ")` misses them.

### Site Alias Backward Compatibility
When site codes change, maintain an alias map so historical data still matches:
```typescript
export const SITE_ALIAS: Record<string, string> = {
  "tpk-clinic": "oak-clinic",
  "wch-clinic": "wel-clinic",
  "lwr-clinic": "bel-clinic",
};
```
The filter function expands the selected site to include all its aliases in an OR clause.

### DQL Bucket Filters
- Epic and Network logs: `dt.system.bucket == "observe_and_troubleshoot_apps_95_days" AND healthcare.pipeline == "healthcare-epic"`
- NetFlow: `log.source == "netflow"` (bucket filter removed because netflow data may land in different buckets)

---

## 4. SVG Map with Canvas Animation Overlay

### Architecture
The campus map uses two overlapping layers:
1. **SVG layer**: Static map (Kansas outline, highways, cities, site icons, flow lines)
2. **Canvas layer**: Animated particles traveling along flow lines

### Geo Projection
An equirectangular projection maps real lat/lon to SVG coordinates:
```typescript
const KS_WEST = -102.05, KS_EAST = -94.59;
const KS_NORTH = 40.003, KS_SOUTH = 36.993;
function lonToX(lon) { return ((lon - KS_WEST) / (KS_EAST - KS_WEST)) * CW + PAD_X; }
function latToY(lat) { return ((KS_NORTH - lat) / (KS_NORTH - KS_SOUTH)) * CH + PAD_Y; }
```

### Critical Canvas/SVG Alignment Bug
**Problem**: SVG uses `preserveAspectRatio="xMidYMid meet"` (uniform scaling + centering), but the canvas initially used independent x/y scaling. This causes particle dots to drift from SVG flow lines, especially on wider containers.

**Solution**: The canvas must compute the same uniform scale and offset:
```typescript
const uniformScale = Math.min(rect.width / VB_W, rect.height / VB_H);
const offsetX = (rect.width - VB_W * uniformScale) / 2;
const offsetY = (rect.height - VB_H * uniformScale) / 2;
// Then: x = gx * uniformScale + offsetX
```

### Geographic Accuracy Matters
- Kansas City, MO (39.0997, -94.5786) is east of `KS_EAST` — renders outside the Kansas boundary
- Kansas City, KS (Wyandotte County, 39.1155, -94.6268) renders at the very edge
- Lawrence, KS (38.9717, -95.2353) is well inside Kansas along I-70 — good hub location
- Always validate that site coordinates fall within the projection bounds

### Ensuring Hub Presence
If the DQL siteHealthSummary query doesn't return kcrmc-main (e.g., no recent data), the flow origin disappears. The map must always inject the hub into geoSites as a fallback:
```typescript
if (!mapped.find(s => s.code === "kcrmc-main") && SITE_GEO["kcrmc-main"]) {
  mapped.push({ code: "kcrmc-main", ...defaults, ...SITE_GEO["kcrmc-main"] });
}
```

---

## 5. Data Generator → DT App Integration

### Metric Dimensions
Network metrics are sent via MINT protocol with dimensions that become filterable in DQL:
```
healthcare.network.device.cpu.utilization,site="kcrmc-main",device="core-rtr-01",vendor="cisco_ios" gauge,35.2 1713456000000
```
In DQL `timeseries` queries, these dimensions are accessed directly: `filter: {site == "kcrmc-main"}`.

### Log Attributes
Log records carry attributes that become DQL fields:
- `healthcare.site` — site code for Epic and Network logs
- `healthcare.pipeline` — `"healthcare-epic"` or `"healthcare-network"`
- `network.device.site` — site code in NetFlow records
- `network.device.hostname` — device name in Network logs

### Topology as Config
The `config/hospital/topology.yaml` file defines:
- Site names, addresses, GPS coordinates
- Device inventory (hostname, vendor, model, interfaces, IP scheme)
- Changing the hub location requires updating this file AND rebuilding the network container

---

## 6. Deployment Workflow

### The Deploy Dance (proven reliable)

```bash
# 1. Edit code locally at /tmp/healthcare-app/
# 2. Build
cd /tmp/healthcare-app && npx dt-app build

# 3. Bump version
sed -i '' 's/"version": "X.Y.Z"/"version": "X.Y.Z+1"/' app.config.json

# 4. Deploy (local only — needs browser SSO)
npx dt-app deploy

# 5. Sync to git repo
rsync -av --exclude node_modules --exclude .dt-app --exclude dist \
  /tmp/healthcare-app/ /tmp/hcg-push/dynatrace-apps/healthcare-health-monitoring/
cd /tmp/hcg-push && git add -A && git commit -m "vX.Y.Z: description" && git push

# 6. Sync to VM
rsync -avz --exclude node_modules --exclude .dt-app --exclude dist \
  -e "ssh -i ~/.ssh/key.pem" /tmp/healthcare-app/ user@vm:~/repo/dynatrace-apps/healthcare-health-monitoring/
```

### Generator Container Rebuild (when topology/config changes)

```bash
ssh user@vm 'cd ~/repo && \
  docker build -t registry/network:vX.Y.Z -f deploy/docker/Dockerfile.network . && \
  az acr login --name registry && \
  docker push registry/network:vX.Y.Z && \
  kubectl rollout restart deployment network-generator -n healthcare-gen'
```

---

## 7. Shell Scripting Pitfalls

| Issue | Details | Solution |
|-------|---------|----------|
| **Heredoc writes silently fail** | Shell heredocs (`cat << 'EOF' > file`) can silently corrupt files when content contains special characters, backticks, or dollar signs | Use a Python script to write files instead |
| **SSH + deploy doesn't work** | `npx dt-app deploy` via SSH gets stuck waiting for browser SSO | Deploy locally only |
| **GitHub SSH from VM** | The VM may not have GitHub SSH keys configured | Push from local machine, not from VM |

---

## 8. Recommended AI Skill Structure

Based on this project, an AI skill for DT app development should cover:

### Skill Files
```
dt-app-development/
  SKILL.md              # Entry point — when to use, quick reference
  references/
    strato-components.md    # Component catalog with correct import paths + props
    dql-patterns.md         # Query patterns, filter injection, timeseries vs fetch
    app-config.md           # Scopes, version management, deploy workflow
    campus-map.md           # SVG + Canvas overlay pattern, geo projection
    common-pitfalls.md      # Build failures, version conflicts, component bugs
```

### Key Rules the Skill Should Enforce
1. Always bump version before deploy
2. Import charts from `@dynatrace/strato-components/charts` (not `-preview`)
3. `HoneycombChart` supports categorical (`{ name, value }[]` + `colorScheme`) and numeric (`number[]`) modes
4. `gapPolicy="connect"` on all TimeseriesChart instances
5. `withSiteFilter` must handle both `timeseries ` and `timeseries\n` patterns
6. Canvas overlays on SVG must use uniform scaling to match `preserveAspectRatio`
7. Site alias maps for backward compatibility when renaming sites
8. Always ensure hub site is present in geoSites even if DQL returns no data for it

---

## 9. Version History

| Version | Changes |
|---------|---------|
| 1.0.0 | Initial app — Overview page with static map, basic KPIs |
| 1.1.0 | Added Epic Health, Network Health, Integration Health pages |
| 1.2.0 | Added SiteView drill-down, Explore page |
| 1.3.0 | Site filter buttons, per-page filtering |
| 1.4.0 | Fixed netflow queries, wired live netflow to map |
| 1.4.1 | Button-based site filter (replaced broken Select/FilterBar) |
| 1.4.2 | gapPolicy="connect" on all TimeseriesChart instances |
| 1.4.3 | Real Kansas geo projection, KC moved to Kansas, network page filtering fixed |
| 1.4.4 | Hub moved to Overland Park KS |
| 1.4.5 | Hub always present in geoSites, flow origin guaranteed |
| 1.4.6 | Site filtering for timeseries/metric queries |
| 1.4.7 | Hub moved to Lawrence KS, removed fake netflow generator |
| 1.4.8 | Canvas particle alignment fix (uniform scaling), multiline timeseries filter detection |

---

## 10. Threshold Calibration (v1.14.3 Session)

### The 100%-is-green Trap
**Problem**: Initial thresholds assumed ideal values (95% success, 0 BTG events). Real baseline data showed ~83% Epic login success, ~93% auth success, and ~50/hr BTG events. Result: dashboard was permanently red.

**Lesson**: Always measure baseline data before setting thresholds. Run the baseline scenario for 10+ minutes, query each metric, and set green at a comfortable margin above worst-case baseline.

### Counting What Matters
| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| ETL Success | 45.6% (RUNNING jobs polluted denominator) | ~86% (filter out RUNNING, count SUCCESS_WITH_WARNINGS) |
| MyChart Login | 0.83% (all failed logins / MyChart successes) | 100% (volume-based: events flowing = healthy) |
| Epic Login | 83% but threshold=85% | 83% but threshold=65% |

**Lesson**: Review the DQL query semantics, not just the thresholds. The formula matters more than the threshold value.

### Pipeline Value Discovery
**Problem**: Assumed pipeline values were `epic-siem` and `network-syslog` based on code review. Actual ingested values were `healthcare-epic` and `healthcare-network`.

**Lesson**: Always verify pipeline/attribute values against actual Grail data:
```dql
fetch logs | summarize count(), by: {healthcare.pipeline} | sort count() desc
```

---

## 11. Strato Component Patterns (v1.14.3 Session)

### Tooltip Ref Forwarding
**Problem**: Wrapping `<Tooltip>` around `<Flex>` causes "ref forwarding" errors — Strato Tooltip needs a native DOM element child to attach its ref.

**Solution**: Wrap in `<div style={{ display: "inline-flex" }}>` instead of `<Flex>`.

### useDql refetchInterval
**Discovery**: `useDql` from `@dynatrace-sdk/react-hooks` supports `refetchInterval` in its options parameter. Setting `refetchInterval: 30_000` makes the hook re-execute the DQL query every 30 seconds without any additional state management.

**Pattern**:
```tsx
const result = useDql(query, { refetchInterval: 30_000 });
```

This is the simplest way to get auto-refreshing data in a DT platform app. Each component instance maintains its own independent polling cycle.

---

## 12. Multi-Scenario WebUI Architecture (v2.1.0–v2.2.0)

### Race Condition Fix
**Problem**: Enabling scenario A while B was active caused both to run simultaneously — the new scenario env var was set but the old one wasn't cleared before restart.

**Solution**: Atomic patch-then-restart: clear ACTIVE_SCENARIO first, wait for restart, then set new value and restart again.

### K8s API Integration
**Pattern**: WebUI runs with an in-cluster ServiceAccount that has RBAC to `get`, `list`, and `patch` Deployments in the `healthcare-gen` namespace. Environment variable injection uses the strategic merge patch type:
```python
body = {"spec": {"template": {"spec": {"containers": [{"name": name, "env": [...]}]}}}}
apps_v1.patch_namespaced_deployment(name, namespace, body)
```

### Demo Guide Walkthrough System
The v2.2.0 WebUI includes step-by-step walkthrough guides:
- Each scenario has a JSON-defined guide with ordered steps
- Steps include descriptions, DT app deep links, and observation prompts
- Frontend auto-advances but supports manual navigation
- Guides are decoupled from scenario activation (can be read without activating)


---

## 13. Scenario Testing — Comprehensive Validation (v2.2.0 Session)

### Scenario-to-Epic Mapping Discovery
**Problem**: Not all WebUI scenarios map to unique Epic scenarios. Three network-only scenarios (HL7 Interface Failure, Epic Outage, IoMT Device Compromise) all map to `epic_scenario: "normal_shift"` -- they produce no Epic-side anomalies.

**Discovery table**:
| WebUI Scenario | Epic Mapping | Impact Domain |
|----------------|-------------|---------------|
| `ransomware-attack` | `ransomware` | Epic + Network |
| `ed-surge` | `ed_surge` | Epic + Network |
| `insider-threat-snooping` | `insider_threat` | Epic only |
| `mychart-credential-stuffing` | `mychart_peak` | Epic (elevated activity, NOT attack patterns) |
| `hl7-interface-failure` | `normal_shift` | Network only |
| `epic-outage-network-root-cause` | `normal_shift` | Network only |
| `iomt-device-compromise` | `normal_shift` | Network only |
| `normal-day-shift` | `normal_shift` | Baseline |

**Lesson**: When testing scenarios, check the mapping first. Network-only scenarios will not move Epic health indicators.

### MyChart Credential Stuffing Misnomer
**Problem**: "MyChart Credential Stuffing" maps to `mychart_peak`, which generates elevated MyChart activity (appointments, messaging, proxy access) -- NOT credential stuffing attack patterns (500+ failed logins, PHI export attempts).

**Expected**: MYCHART_LOGIN / MYCHART_FAILED_LOGIN events with high failure rate.
**Actual**: MYCHART_APPT_SCHEDULE, MYCHART_MSG_SEND, MYCHART_PROXY_ACCESS events (normal peak usage).

**Lesson**: Scenario names in the WebUI should accurately reflect what the generator produces. If the scenario claims "Credential Stuffing" but produces normal peak traffic, either the name or the generator needs updating.

### Ransomware Data Persistence in DQL Windows
**Problem**: After deactivating the ransomware scenario, Epic Login health took ~50 minutes to fully recover from RED (44%) back to GREEN (83%). The DQL queries use `fetch logs` without an explicit time range, which defaults to the last 30 minutes of data.

**Recovery timeline**:
| Time Post-Deactivation | Epic Login | Failed Logins | Status |
|------------------------|-----------|---------------|--------|
| 0 min | 44.0% | 1449 | RED |
| 18 min | 49.5% | 1175 | AMBER |
| 28 min | 57.8% | 839 | AMBER |
| 48 min | 76.5% | 357 | GREEN (login), AMBER (failed count) |
| 53 min | 82.7% | 251 | GREEN (login), AMBER (failed count) |

**Lesson**: Ransomware generates a burst of ~1450 failed logins that persist in the 30-minute query window. Full recovery takes ~50 minutes, not 2-3 minutes. Demo guides should set correct expectations.

### Volume vs. Percentage Metrics Behave Differently
**Problem**: ED Surge generates high event volume but doesn't shift percentage-based metrics (like login success rate). Both successful and failed logins increase proportionally.

**Lesson**: Percentage-based health indicators are resistant to volume-based scenarios. Volume-based scenarios need volume-based indicators to show impact.

### Network-Only Scenarios Show Minimal DT App Impact
**Problem**: HL7 Interface Failure, Epic Outage, and IoMT Device Compromise produced network events but since they use `normal_shift` for Epic, the DT app health indicators remained GREEN.

**Lesson**: The current DT app health indicators are heavily Epic-centric. Network-specific indicators (switch port errors, HL7 NACK rate, IPS alert count) would be needed to detect network-only scenarios.

---

## 14. DQL Default Query Window Behavior

### No Explicit Timeframe = Last 30 Minutes
**Discovery**: `fetch logs` without `| filter timestamp > now() - Xm` uses a default sliding window of approximately 30 minutes. Data ingestion lag can extend the effective window.

**Impact**: When a scenario generates a burst of anomalous events, those events persist in the query window for 30+ minutes after the scenario is deactivated. Recovery is gradual, not instant.

**Lesson**: For demo purposes, either use explicit time ranges in health queries for faster recovery, or set expectations that post-scenario recovery takes 15-50 minutes depending on scenario intensity.

---

## 15. Insider Threat Produces Detectable BTG Patterns

### Verified Pattern
The Insider Threat scenario generates `AC_BREAK_THE_GLASS_ACCESS` events at approximately 6-7 events per minute.

**Key Observations**:
- BTG events are the primary indicator (not login failures)
- The scenario also generates elevated SECURE events
- It does NOT generate FAILEDLOGIN events (insider already has valid credentials)
- Network indicators remain unaffected (this is an Epic-only scenario)

**Lesson**: Insider Threat is best detected through BTG count and after-hours access patterns, not through login failure metrics. This makes it distinguishable from Ransomware (which generates both BTG and FAILEDLOGIN).
