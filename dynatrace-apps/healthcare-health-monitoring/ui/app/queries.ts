// ============================================================================
// Healthcare Health Monitoring — Shared DQL Queries  (v1.0.2)
// ============================================================================
// All queries target the dedicated healthcare bucket for performance.
// Data discriminators (OpenPipeline tags):
//   Epic logs:    healthcare.pipeline == "healthcare-epic"
//   Network logs: healthcare.pipeline == "healthcare-network"
//   Metrics:      healthcare.network.* (timeseries)
// ============================================================================

const BUCKET = 'dt.system.bucket == "observe_and_troubleshoot_apps_95_days"';
export const EPIC_FILTER = `${BUCKET} AND healthcare.pipeline == "healthcare-epic"`;
export const NETWORK_FILTER = `${BUCKET} AND healthcare.pipeline == "healthcare-network"`;

export const queries = {
  // ─── Overview KPIs ────────────────────────────────────────────────
  epicLoginSuccessRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(Action)
    | summarize
        successes = countIf(Action == "Login Success" OR Action == "HKU_LOGIN"),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(successes) / toDouble(total) * 100.0, else: 0.0)`,

  hl7AckRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | summarize
        acks = countIf(matchesPhrase(content, "ACK") OR matchesPhrase(content, "AA")),
        total = count()
    | fieldsAdd ack_rate = if(total > 0, toDouble(acks) / toDouble(total) * 100.0, else: 0.0)`,

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

  activeProblems: `fetch events
    | filter event.status == "ACTIVE"
    | summarize problem_count = count()`,

  // ─── Overview Charts ──────────────────────────────────────────────
  systemActivityTimeline: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${BUCKET}
    | filter isNotNull(healthcare.pipeline)
    | makeTimeseries events = count(), by: { healthcare.pipeline }, interval: 5m`,

  epicEventDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | fieldsAdd event_category = coalesce(
        if(isNotNull(MSH.9), "HL7"),
        if(isNotNull(response_time_ms), "FHIR API"),
        if(isNotNull(patient_portal_action), "MyChart"),
        if(isNotNull(job_name), "ETL"),
        if(isNotNull(ORDER_TYPE), "Clinical"),
        "SIEM Audit"
      )
    | summarize cnt = count(), by: { event_category }
    | sort cnt desc`,

  networkEventDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | summarize cnt = count(), by: { log.source }
    | sort cnt desc`,

  // ─── Epic Health — Login & Auth ───────────────────────────────────
  loginVolumeOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(Action)
    | fieldsAdd login_status = if(
        Action == "Login Success" OR Action == "HKU_LOGIN" OR Action == "CTO_LOGIN",
        "success",
        else: "failure"
      )
    | makeTimeseries logins = count(), by: { login_status }, interval: 5m`,

  loginSuccessRateTrend: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(Action)
    | makeTimeseries
        successes = countIf(Action == "Login Success" OR Action == "HKU_LOGIN"),
        total = count(),
        interval: 5m
    | fieldsAdd rate = if(total[] > 0, successes[] / total[] * 100.0, else: 0.0)`,

  activeUsers: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(EMPid)
    | summarize unique_users = countDistinct(EMPid)`,

  loginBySite: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(Action)
    | summarize logins = count(), by: { site = healthcare.site }
    | sort logins desc`,

  // ─── Epic Health — Clinical Throughput ─────────────────────────────
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

  clinicalEventTypes: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(ORDER_TYPE) OR isNotNull(NOTE_TYPE) OR isNotNull(MEDICATION_NAME)
    | fieldsAdd clinical_type = coalesce(ORDER_TYPE, NOTE_TYPE, "Medication")
    | summarize cnt = count(), by: { clinical_type }
    | sort cnt desc`,

  // ─── Epic Health — MyChart Portal ─────────────────────────────────
  myChartSessionsOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(patient_portal_action)
    | makeTimeseries sessions = count(), by: { patient_portal_action }, interval: 5m`,

  myChartDeviceTypes: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(device_type)
    | summarize cnt = count(), by: { device_type }
    | sort cnt desc`,

  // ─── Network Health — Device Health (Metrics) ─────────────────────
  deviceCpuOverTime: `timeseries cpu = avg(healthcare.network.device.cpu.utilization), by: {device}, from: now()-2h`,

  deviceMemOverTime: `timeseries mem = avg(healthcare.network.device.memory.utilization), by: {device}, from: now()-2h`,

  trafficInOverTime: `timeseries bytes_in = avg(healthcare.network.if.traffic.in.bytes), by: {device}, from: now()-2h`,

  trafficOutOverTime: `timeseries bytes_out = avg(healthcare.network.if.traffic.out.bytes), by: {device}, from: now()-2h`,

  deviceSnapshot: `timeseries
      cpu = avg(healthcare.network.device.cpu.utilization),
      mem = avg(healthcare.network.device.memory.utilization),
      by: {device, site, vendor}, from: now()-15m
    | fieldsAdd avg_cpu = arrayAvg(cpu), avg_mem = arrayAvg(mem)
    | fields device, site, vendor, avg_cpu, avg_mem
    | sort avg_cpu desc`,

  deviceCpuBySite: `timeseries cpu = avg(healthcare.network.device.cpu.utilization), by: {site}, from: now()-2h`,

  // ─── Network Health — Log Events ──────────────────────────────────
  networkLogTimeline: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | makeTimeseries events = count(), by: { log.source }, interval: 5m`,

  networkDeviceList: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | summarize
        events = count(),
        last_seen = max(timestamp),
        vendor = takeFirst(network.device.vendor),
        role = takeFirst(network.device.role),
        model = takeFirst(network.device.model),
        site = takeFirst(healthcare.site),
        by: { hostname = network.device.hostname }
    | sort hostname asc`,

  networkVendorDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | summarize cnt = count(), by: { vendor = network.device.vendor }
    | sort cnt desc`,

  networkSiteDistribution: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | summarize cnt = count(), by: { site = healthcare.site }
    | sort cnt desc`,

  // ─── Integration Health — HL7 ─────────────────────────────────────
  hl7VolumeOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | makeTimeseries messages = count(), by: { message_type = MSH.9 }, interval: 5m`,

  hl7MessageTypes: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | summarize cnt = count(), by: { message_type = MSH.9 }
    | sort cnt desc`,

  hl7AckRateTrend: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | makeTimeseries
        acks = countIf(matchesPhrase(content, "ACK") OR matchesPhrase(content, "AA")),
        total = count(),
        interval: 5m`,

  hl7Errors: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | filter matchesPhrase(content, "NAK") OR matchesPhrase(content, "AE") OR matchesPhrase(content, "AR") OR matchesPhrase(content, "error")
    | fields timestamp, MSH.9, MSH.10, content, healthcare.site
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
    | filter isNotNull(response_time_ms) AND toDouble(response_time_ms) > 2000
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

  etlRecordsProcessed: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(records_processed)
    | makeTimeseries records = sum(toDouble(records_processed)), by: { source_system }, interval: 5m`,

  etlFailedJobs: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name) AND job_result == "failed"
    | fields timestamp, job_name, source_system, duration_seconds, records_processed, content
    | sort timestamp desc
    | limit 30`,

  etlSuccessRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name)
    | summarize
        successes = countIf(job_result == "success" OR job_result == "completed"),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(successes) / toDouble(total) * 100.0, else: 0.0)`,

  // ─── Site View ────────────────────────────────────────────────────
  epicEventsBySite: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | summarize
        events = count(),
        logins = countIf(isNotNull(Action)),
        login_success = countIf(Action == "Login Success" OR Action == "HKU_LOGIN"),
        by: { site = healthcare.site }
    | fieldsAdd login_rate = if(logins > 0, toDouble(login_success) / toDouble(logins) * 100.0, else: 0.0)`,

  networkHealthBySite: `timeseries cpu = avg(healthcare.network.device.cpu.utilization), by: {site}, from: now()-15m
    | fieldsAdd avg_cpu = arrayAvg(cpu)
    | fields site, avg_cpu`,

  siteCompositeHealth: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | summarize
        epic_events = count(),
        login_success = countIf(Action == "Login Success" OR Action == "HKU_LOGIN"),
        logins = countIf(isNotNull(Action)),
        by: { site = healthcare.site }
    | fieldsAdd epic_health = if(logins > 0, toDouble(login_success) / toDouble(logins) * 100.0, else: 100.0)
    | fieldsAdd composite = epic_health * 0.5 + 85.0 * 0.5`,

  // ─── Explore ──────────────────────────────────────────────────────
  allEpicEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | fields timestamp, Action, EMPid, DEPARTMENT, ORDER_TYPE, healthcare.site, log.source
    | sort timestamp desc
    | limit 50`,

  allNetworkEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | fields timestamp, network.device.hostname, network.device.vendor, network.device.role, healthcare.site, log.source, network.log_type
    | sort timestamp desc
    | limit 50`,

  eventsBySite: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${BUCKET} AND isNotNull(healthcare.pipeline)
    | summarize count = count(), by: { healthcare.site, healthcare.pipeline }
    | sort count desc`,

  activeProblemsList: `fetch events
    | filter event.status == "ACTIVE"
    | fields timestamp, event.name, event.status, event.kind
    | sort timestamp desc
    | limit 30`,

  problemHistory: `fetch events
    | filter event.status == "CLOSED"
    | summarize cnt = count(), by: { event.kind }
    | sort cnt desc`,
};
