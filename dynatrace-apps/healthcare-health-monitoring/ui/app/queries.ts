// ============================================================================
// Healthcare Health Monitoring — Shared DQL Queries  (v1.4.0)
// ============================================================================
// All queries target the dedicated healthcare bucket.
// Sites: kcrmc-main (KC), oak-clinic (Oakley), wel-clinic (Wellington),
//        bel-clinic (Belleville)
// ============================================================================

const BUCKET = 'dt.system.bucket == "observe_and_troubleshoot_apps_95_days"';
export const EPIC_FILTER = `${BUCKET} AND healthcare.pipeline == "healthcare-epic"`;
export const NETWORK_FILTER = `${BUCKET} AND healthcare.pipeline == "healthcare-network"`;
export const NETFLOW_FILTER = `log.source == "netflow"`;

// Site alias map: old codes → new codes (for filter matching)
export const SITE_ALIAS: Record<string, string> = {
  "tpk-clinic": "oak-clinic",
  "wch-clinic": "wel-clinic",
  "lwr-clinic": "bel-clinic",
};

export const ALL_SITES = [
  { code: "kcrmc-main", name: "Lawrence Regional Medical Center" },
  { code: "oak-clinic", name: "Oakley Rural Health" },
  { code: "wel-clinic", name: "Wellington Care Center" },
  { code: "bel-clinic", name: "Belleville Family Medicine" },
];

// Build a DQL site filter clause for Epic logs (healthcare.site field)
// Includes old alias codes so historical data matches
export function epicSiteFilter(siteCode: string): string {
  const aliases = Object.entries(SITE_ALIAS).filter(([, v]) => v === siteCode).map(([k]) => k);
  const codes = [siteCode, ...aliases].map((c) => `healthcare.site == "${c}"`).join(" OR ");
  return `(${codes})`;
}

// Build a DQL site filter clause for Network logs (healthcare.site field)
export function networkSiteFilter(siteCode: string): string {
  return epicSiteFilter(siteCode); // same field
}

// Build a DQL site filter for NetFlow (network.device.site field)
export function netflowSiteFilter(siteCode: string): string {
  const aliases = Object.entries(SITE_ALIAS).filter(([, v]) => v === siteCode).map(([k]) => k);
  const codes = [siteCode, ...aliases].map((c) => `network.device.site == "${c}"`).join(" OR ");
  return `(${codes})`;
}

export const queries = {

  // ─── Overview KPIs ────────────────────────────────────────────────
  epicLoginSuccessRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN" OR E1Mid == "LOGIN_BLOCKED" OR E1Mid == "WPSEC_LOGIN_FAIL"
    | summarize
        successes = countIf(E1Mid == "BCA_LOGIN_SUCCESS"),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(successes) / toDouble(total) * 100.0, else: 0.0)`,

  hl7DeliveryRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | makeTimeseries vol = count(), interval: 5m
    | fieldsAdd recent_vol = arrayLast(vol)
    | fieldsAdd delivery_rate = if(isNull(recent_vol) OR recent_vol < 1, 0.0, else: 100.0)`,

  fhirHealthRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | summarize
        ok = countIf(toDouble(response_code) < 400),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(ok) / toDouble(total) * 100.0, else: 0.0)`,

  networkDeviceUpRatio: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | summarize last_seen = max(timestamp), by: { hostname = network.device.hostname }
    | fieldsAdd minutes_ago = toDouble(now() - last_seen) / 60000000000.0
    | summarize
        total = count(),
        up = countIf(minutes_ago < 5)
    | fieldsAdd up_ratio = if(total > 0, toDouble(up) / toDouble(total) * 100.0, else: 0.0)`,

  avgDeviceCpu: `timeseries cpu = avg(healthcare.network.device.cpu.utilization), from: now()-15m
    | fieldsAdd avg_cpu = arrayAvg(cpu)
    | fields avg_cpu`,

  avgDeviceMem: `timeseries mem = avg(healthcare.network.device.memory.utilization), from: now()-15m
    | fieldsAdd avg_mem = arrayAvg(mem)
    | fields avg_mem`,

  totalEpicEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | summarize total = count()`,

  totalNetworkEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | summarize total = count()`,

  activeUsers: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(EMPid)
    | summarize unique_users = countDistinct(EMPid)`,

  // ─── Overview Charts ──────────────────────────────────────────────
  systemActivityTimeline: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${BUCKET}
    | filter isNotNull(healthcare.pipeline) OR log.source == "netflow"
    | fieldsAdd pipeline = if(log.source == "netflow", "netflow", else: healthcare.pipeline)
    | makeTimeseries events = count(), by: { pipeline }, interval: 5m`,

  epicEventDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | fieldsAdd event_category = if(isNotNull(MSH.9), "HL7",
        else: if(isNotNull(response_time_ms), "FHIR API",
        else: if(isNotNull(patient_portal_action), "MyChart",
        else: if(isNotNull(job_name), "ETL",
        else: if(isNotNull(ORDER_TYPE), "Clinical Order",
        else: if(e1mid == "HKU_LOGIN" OR e1mid == "CTO_LOGIN" OR e1mid == "FAILEDLOGIN", "Login/Auth",
        else: "SIEM Audit"))))))
    | summarize cnt = count(), by: { event_category }
    | sort cnt desc`,

  // ─── Campus map / Site summary ────────────────────────────────────
  siteHealthSummary: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | summarize
        events = count(),
        logins = countIf(E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN" OR E1Mid == "LOGIN_BLOCKED" OR E1Mid == "WPSEC_LOGIN_FAIL"),
        login_ok = countIf(E1Mid == "BCA_LOGIN_SUCCESS"),
        users = countDistinct(EMPid),
        by: { site = healthcare.site }`,

  networkSiteHealth: `timeseries
      cpu = avg(healthcare.network.device.cpu.utilization),
      mem = avg(healthcare.network.device.memory.utilization),
      by: {site}, from: now()-15m
    | fieldsAdd avg_cpu = arrayAvg(cpu), avg_mem = arrayAvg(mem)
    | fields site, avg_cpu, avg_mem`,

  networkDevicesBySite: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | summarize devices = countDistinct(network.device.hostname), by: { site = healthcare.site }`,

  // ─── Honeycomb / Fleet ────────────────────────────────────────────
  deviceSnapshot: `timeseries
      cpu = avg(healthcare.network.device.cpu.utilization),
      mem = avg(healthcare.network.device.memory.utilization),
      by: {device, site, vendor}, from: now()-15m
    | fieldsAdd avg_cpu = arrayAvg(cpu), avg_mem = arrayAvg(mem)
    | fields device, site, vendor, avg_cpu, avg_mem
    | sort site, device`,

  // ─── Epic Health — Login & Auth ───────────────────────────────────
  loginVolumeOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN" OR E1Mid == "LOGIN_BLOCKED" OR E1Mid == "WPSEC_LOGIN_FAIL"
    | fieldsAdd login_status = if(E1Mid == "BCA_LOGIN_SUCCESS", "success", else: "failure")
    | makeTimeseries logins = count(), by: { login_status }, interval: 5m`,

  loginSuccessRateTrend: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN" OR E1Mid == "LOGIN_BLOCKED" OR E1Mid == "WPSEC_LOGIN_FAIL"
    | makeTimeseries
        successes = countIf(E1Mid == "BCA_LOGIN_SUCCESS"),
        total = count(),
        interval: 5m`,

  loginBySite: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN" OR E1Mid == "LOGIN_BLOCKED" OR E1Mid == "WPSEC_LOGIN_FAIL"
    | summarize logins = count(), by: { site = healthcare.site }
    | sort logins desc`,

  securityEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT" OR e1mid == "WPSEC_LOGIN_FAIL" OR e1mid == "LOGIN_BLOCKED" OR e1mid == "FAILEDLOGIN"
    | fields timestamp, e1mid, EMPid, healthcare.site
    | sort timestamp desc
    | limit 30`,

  // ─── Epic Health — Clinical ────────────────────────────────────────
  siemEventsByType: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter isNotNull(e1mid)
    | summarize cnt = count(), by: { e1mid }
    | sort cnt desc`,

  orderVolumeOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(ORDER_TYPE)
    | makeTimeseries orders = count(), by: { ORDER_TYPE }, interval: 5m`,

  departmentActivity: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(DEPARTMENT)
    | summarize events = count(), by: { DEPARTMENT }
    | sort events desc
    | limit 15`,

  // ─── Network Health — Device Metrics ──────────────────────────────
  deviceCpuOverTime: `timeseries cpu = avg(healthcare.network.device.cpu.utilization), by: {device}, from: now()-2h`,
  deviceMemOverTime: `timeseries mem = avg(healthcare.network.device.memory.utilization), by: {device}, from: now()-2h`,
  trafficInOverTime: `timeseries bytes_in = avg(healthcare.network.if.traffic.in.bytes), by: {device}, from: now()-2h`,
  trafficOutOverTime: `timeseries bytes_out = avg(healthcare.network.if.traffic.out.bytes), by: {device}, from: now()-2h`,
  deviceCpuBySite: `timeseries cpu = avg(healthcare.network.device.cpu.utilization), by: {site}, from: now()-2h`,

  // ─── Network Health — Log Events ──────────────────────────────────
  networkLogTimeline: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | makeTimeseries events = count(), by: { vendor = network.device.vendor }, interval: 5m`,

  networkDeviceList: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | summarize
        events = count(),
        last_seen = max(timestamp),
        vendor = takeFirst(network.device.vendor),
        role = takeFirst(network.device.role),
        site = takeFirst(healthcare.site),
        by: { hostname = network.device.hostname }
    | sort hostname asc`,

  networkVendorDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | summarize cnt = count(), by: { vendor = network.device.vendor }
    | sort cnt desc`,

  // ─── NetFlow Queries ──────────────────────────────────────────────
  netflowTotalFlows: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | summarize total = count()`,

  netflowTimeline: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | makeTimeseries flows = count(), by: { site = network.device.site }, interval: 5m`,

  netflowProtocolDist: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | summarize cnt = count(), by: { protocol = network.flow.protocol }
    | sort cnt desc`,

  netflowTopDstPorts: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | summarize cnt = count(), by: { dst_port = network.flow.dst_port }
    | sort cnt desc
    | limit 10`,

  netflowTopSrcCountries: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | filter network.flow.src.country != "United States"
    | summarize cnt = count(), by: { country = network.flow.src.country }
    | sort cnt desc
    | limit 10`,

  netflowBySite: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | summarize flows = count(), by: { site = network.device.site }
    | sort flows desc`,

  netflowRecentFlows: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | fields timestamp, network.flow.src_ip, network.flow.dst_ip, network.flow.dst_port, network.flow.protocol, network.flow.bytes, network.device.hostname, network.device.site
    | sort timestamp desc
    | limit 30`,

  // ─── Integration Health — HL7 ─────────────────────────────────────
  hl7VolumeOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | makeTimeseries messages = count(), interval: 5m`,

  hl7MessageBreakdown: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | parse content, "LD 'ORC|' LD:orc_action '|'"
    | summarize cnt = count(), by: { orc_action }
    | sort cnt desc`,

  hl7RecentMessages: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | parse content, "LD 'ORC|' LD:orc_action '|'"
    | fields timestamp, MSH.9, MSH.10, orc_action, healthcare.site
    | sort timestamp desc
    | limit 30`,

  // ─── Integration Health — FHIR API ────────────────────────────────
  fhirRequestRateOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | makeTimeseries requests = count(), by: { method }, interval: 5m`,

  fhirStatusDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | fieldsAdd status_group = if(toDouble(response_code) < 300, "2xx",
        else: if(toDouble(response_code) < 400, "3xx",
        else: if(toDouble(response_code) < 500, "4xx", else: "5xx")))
    | summarize cnt = count(), by: { status_group }
    | sort cnt desc`,

  fhirErrorRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | summarize
        errors = countIf(toDouble(response_code) >= 400),
        total = count()
    | fieldsAdd error_rate = if(total > 0, toDouble(errors) / toDouble(total) * 100.0, else: 0.0)`,

  fhirResponseTimePercentiles: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | makeTimeseries
        p50 = percentile(toDouble(response_time_ms), 50),
        p95 = percentile(toDouble(response_time_ms), 95),
        p99 = percentile(toDouble(response_time_ms), 99),
        interval: 5m`,

  fhirSlowRequests: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms) AND toDouble(response_time_ms) > 500
    | fields timestamp, method, path, response_code, response_time_ms, client_id, healthcare.site
    | sort timestamp desc
    | limit 30`,

  fhirClientUsage: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(client_id)
    | summarize requests = count(), by: { client_id }
    | sort requests desc
    | limit 15`,

  // ─── Integration Health — ETL Jobs ────────────────────────────────
  etlJobStatusOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name)
    | makeTimeseries jobs = count(), by: { job_result }, interval: 5m`,

  etlJobDurationTrends: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name) AND isNotNull(duration_seconds)
    | makeTimeseries duration = avg(toDouble(duration_seconds)), by: { job_name }, interval: 5m`,

  etlFailedJobs: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name) AND (job_result == "FAILED" OR job_result == "failed")
    | fields timestamp, job_name, source_system, duration_seconds, records_processed, content
    | sort timestamp desc
    | limit 30`,

  etlSuccessRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name) AND isNotNull(job_result)
    | summarize
        successes = countIf(job_result == "SUCCESS" OR job_result == "success" OR job_result == "completed"),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(successes) / toDouble(total) * 100.0, else: 0.0)`,

  // ─── Correlation ──────────────────────────────────────────────────
  epicNetworkCorrelation: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${BUCKET} AND (isNotNull(healthcare.pipeline) OR log.source == "netflow")
    | fieldsAdd pipeline = if(log.source == "netflow", "netflow", else: healthcare.pipeline)
    | makeTimeseries events = count(), by: { pipeline }, interval: 5m`,

  eventsBySite: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${BUCKET} AND isNotNull(healthcare.pipeline)
    | summarize count = count(), by: { site = healthcare.site, pipeline = healthcare.pipeline }
    | sort count desc`,

  // ─── Explore ──────────────────────────────────────────────────────
  allEpicEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | fields timestamp, e1mid, Action, EMPid, DEPARTMENT, ORDER_TYPE, healthcare.site
    | sort timestamp desc
    | limit 50`,

  allNetworkEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | fields timestamp, network.device.hostname, network.device.vendor, network.device.role, healthcare.site, network.log_type
    | sort timestamp desc
    | limit 50`,

  allNetflowEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | fields timestamp, network.flow.src_ip, network.flow.dst_ip, network.flow.dst_port, network.flow.protocol, network.flow.bytes, network.device.hostname, network.device.site
    | sort timestamp desc
    | limit 50`,

  activeProblemsList: `fetch events
    | filter event.status == "ACTIVE"
    | fields timestamp, event.name, event.status, event.kind
    | sort timestamp desc
    | limit 30`,

  // ─── Site Drill-Down — Tier 1 Data ────────────────────────────────
  // These are parameterised per-site; call with template literals
  siteHL7Volume: (siteFilter: string) => `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter ${siteFilter}
    | filter isNotNull(MSH.9)
    | summarize total = count()`,

  siteErrorRate: (siteFilter: string) => `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter ${siteFilter}
    | summarize
        errors = countIf(severity == "ERROR" OR severity == "WARN"),
        total = count()
    | fieldsAdd error_rate = if(total > 0, toDouble(errors) / toDouble(total) * 100.0, else: 0.0)`,

  siteNetflowVolume: (siteFilter: string) => `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | filter ${siteFilter}
    | summarize total = count()`,

  siteNetflowTimeline: (siteFilter: string) => `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | filter ${siteFilter}
    | makeTimeseries flows = count(), interval: 5m`,

  siteTopEventTypes: (siteFilter: string) => `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter ${siteFilter}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter isNotNull(e1mid)
    | fieldsAdd event_category = if(isNotNull(MSH.9), "HL7",
        else: if(isNotNull(response_time_ms), "FHIR API",
        else: if(isNotNull(patient_portal_action), "MyChart",
        else: if(isNotNull(job_name), "ETL",
        else: if(isNotNull(ORDER_TYPE), "Clinical Order",
        else: if(e1mid == "HKU_LOGIN" OR e1mid == "CTO_LOGIN" OR e1mid == "FAILEDLOGIN", "Login/Auth",
        else: "SIEM Audit"))))))
    | summarize cnt = count(), by: { event_category }
    | sort cnt desc`,

  // ===== Tier 3: Detection Queries =====

  /** Network logs grouped by severity */
  networkBySeverity: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | filter isNotNull(syslog_severity)
    | summarize cnt = count(), by: { syslog_severity }
    | sort cnt desc`,

  /** Network critical event count (for KPI) */
  networkCriticalEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | filter syslog_severity == "CRITICAL" OR syslog_severity == "EMERGENCY" OR syslog_severity == "ALERT"
    | summarize critical_count = count()`,

  /** HL7 messages by message type (ADT, ORM, etc.) */
  hl7ByMessageType: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | makeTimeseries cnt = count(), by: { MSH.9 }, interval: 5m`,

  /** Port security violations from network logs */
  portSecurityViolations: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | filter matchesPhrase(content, "violation") OR matchesPhrase(content, "restrict") OR matchesPhrase(content, "port-security")
    | summarize violation_count = count()`,

  /** Lateral movement scan detection — hosts contacting many unique IPs */
  lateralScanDetection: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETFLOW_FILTER}
    | summarize unique_dsts = countDistinct(dst_ip), by: { src_ip }
    | filter unique_dsts > 15
    | sort unique_dsts desc`,

  /** Rapid patient access — users accessing many patients quickly */
  rapidPatientAccess: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(patient_id)
    | summarize patient_count = countDistinct(patient_id), by: { EMPid }
    | filter patient_count > 10
    | sort patient_count desc`,

  /** STAT order rate */
  statOrderRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(ORDER_TYPE)
    | summarize
        stat_orders = countIf(matchesPhrase(ORDER_TYPE, "STAT")),
        total_orders = count()
    | fieldsAdd stat_pct = if(total_orders > 0, toDouble(stat_orders) / toDouble(total_orders) * 100.0, else: 0.0)`,

  /** Firewall deny/block events from network logs */
  firewallEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | filter matchesPhrase(content, "deny") OR matchesPhrase(content, "blocked") OR matchesPhrase(content, "drop")
    | summarize firewall_count = count()`,

  /** Total break-the-glass events (all hours) — for section health */
  btgTotalCount: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT"
    | summarize btg_total = count()`,

  /** After-hours break-the-glass events (for KPI) */
  afterHoursBtgCount: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT"
    | fieldsAdd hour = getHour(timestamp)
    | filter hour < 6 OR hour >= 22
    | summarize btg_after_hours = count()`,

  /** HL7 volume in last 5 minutes (for KPI) */
  hl7RecentVolume: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1, from: now()-5m
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | summarize hl7_volume = count()`,

  // ─── Authentication Health — New Mnemonic Fields ──────────────────

  /** Login success vs failure by E1Mid (BCA_LOGIN_SUCCESS / FAILEDLOGIN) */
  loginSuccessVsFailure: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN"
    | makeTimeseries logins = count(), by: { E1Mid }, interval: 5m`,

  /** Login error type breakdown */
  loginErrorTypeBreakdown: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "FAILEDLOGIN" AND isNotNull(LOGINERROR)
    | summarize cnt = count(), by: { LOGINERROR }
    | sort cnt desc`,

  /** Login context distribution */
  loginContextDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(LOGIN_CONTEXT) AND (E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN")
    | summarize cnt = count(), by: { LOGIN_CONTEXT }
    | sort cnt desc`,

  /** Client type distribution for login events */
  loginClientTypeDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(CLIENT_TYPE) AND (E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN")
    | summarize cnt = count(), by: { CLIENT_TYPE }
    | sort cnt desc`,

  /** Login source distribution */
  loginSourceDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(LOGIN_SOURCE) AND (E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN")
    | summarize cnt = count(), by: { LOGIN_SOURCE }
    | sort cnt desc`,

  /** Login activity by workstation */
  loginByWorkstation: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter (E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN") AND isNotNull(WorkstationID)
    | summarize
        total = count(),
        failures = countIf(E1Mid == "FAILEDLOGIN"),
        by: { WorkstationID }
    | sort total desc
    | limit 15`,

  /** Internet area distribution */
  loginInternetAreaDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(INTERNET_AREA) AND (E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN")
    | summarize cnt = count(), by: { INTERNET_AREA }
    | sort cnt desc`,

  /** Active workstation count (KPI) */
  activeWorkstationCount: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(WorkstationID) AND (E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN")
    | summarize active_ws = countDistinct(WorkstationID)`,

  /** LDAP login count (KPI) */
  ldapLoginCount: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(LOGIN_LDAP_ID) AND (E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN")
    | summarize ldap_users = countDistinct(LOGIN_LDAP_ID)`,

  /** Failed login count (KPI for auth page) */
  authFailedLoginCount: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "FAILEDLOGIN"
    | summarize total = count()`,

  /** Login success rate (auth-specific using BCA_LOGIN_SUCCESS) */
  authLoginSuccessRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "BCA_LOGIN_SUCCESS" OR E1Mid == "FAILEDLOGIN"
    | summarize
        successes = countIf(E1Mid == "BCA_LOGIN_SUCCESS"),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(successes) / toDouble(total) * 100.0, else: 0.0)`,

  // ─── Service Audit — New Mnemonic Fields ──────────────────────────

  /** API service category breakdown */
  apiCategoryBreakdown: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "IC_SERVICE_AUDIT" AND isNotNull(SERVICECATEGORY)
    | summarize cnt = count(), by: { SERVICECATEGORY }
    | sort cnt desc`,

  /** Service type distribution */
  serviceTypeDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "IC_SERVICE_AUDIT" AND isNotNull(SERVICETYPE)
    | summarize cnt = count(), by: { SERVICETYPE }
    | sort cnt desc`,

  /** Service category over time */
  serviceCategoryOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "IC_SERVICE_AUDIT" AND isNotNull(SERVICECATEGORY)
    | makeTimeseries calls = count(), by: { SERVICECATEGORY }, interval: 5m`,

  /** Top service names */
  topServiceNames: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "IC_SERVICE_AUDIT" AND isNotNull(SERVICENAME)
    | summarize cnt = count(), by: { SERVICENAME }
    | sort cnt desc
    | limit 15`,

  /** Service user type distribution */
  serviceUserTypeDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "IC_SERVICE_AUDIT" AND isNotNull(SERVICE_USERTYP)
    | summarize cnt = count(), by: { SERVICE_USERTYP }
    | sort cnt desc`,

  /** Instance URN distribution */
  instanceUrnDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "IC_SERVICE_AUDIT" AND isNotNull(INSTANCEURN)
    | summarize cnt = count(), by: { INSTANCEURN }
    | sort cnt desc`,

  /** Workstation activity over time (heatmap-style) */
  workstationActivityOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(WorkstationID) AND isNotNull(E1Mid)
    | fieldsAdd hour = getHour(timestamp)
    | summarize events = count(), by: { WorkstationID, hour }
    | sort WorkstationID, hour`,

  /** Failed logins by workstation (security insight) */
  failedLoginsByWorkstation: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter E1Mid == "FAILEDLOGIN" AND isNotNull(WorkstationID)
    | summarize failures = count(), by: { WorkstationID }
    | sort failures desc
    | limit 10`,
};
