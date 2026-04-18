// ============================================================================
// Healthcare Health Monitoring — Shared DQL Queries
// ============================================================================
// Centralized query module following Network Insights App pattern.
// All queries reference data produced by the Epic SIEM and Network generators.
//
// Data discriminators:
//   Epic logs:    generator.type == "epic-siem"
//   Network logs: generator.type == "network"
//   SNMP polls:   log.source == "snmp.poll"
//   SNMP metrics: network.snmp.* (via timeseries)
//   Device inventory: event.type == "network.device.inventory" (bizevents)
// ============================================================================

// Shared filters — reusable across queries
export const EPIC_FILTER = 'generator.type == "epic-siem"';
export const NETWORK_FILTER = 'generator.type == "network"';
export const SNMP_FILTER = 'log.source == "snmp.poll"';

export const queries = {
  // ─── Overview KPIs ────────────────────────────────────────────────
  epicLoginSuccessRate: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(Action)
    | summarize
        successes = countIf(Action == "Login Success" OR Action == "HKU_LOGIN"),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(successes) / toDouble(total) * 100.0, else: 0.0)`,

  hl7AckRate: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | summarize
        acks = countIf(matchesPhrase(content, "ACK") OR matchesPhrase(content, "AA")),
        total = count()
    | fieldsAdd ack_rate = if(total > 0, toDouble(acks) / toDouble(total) * 100.0, else: 0.0)`,

  fhirHealthRate: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | summarize
        ok = countIf(toDouble(status) < 400),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(ok) / toDouble(total) * 100.0, else: 0.0)`,

  networkDeviceUpRatio: `fetch logs
    | filter ${SNMP_FILTER}
    | summarize last_poll = max(timestamp), by: { hostname = network.device.hostname }
    | fieldsAdd minutes_ago = toDouble(now() - last_poll) / 60000000000.0
    | summarize
        total = count(),
        up = countIf(minutes_ago < 10)
    | fieldsAdd up_ratio = if(total > 0, toDouble(up) / toDouble(total) * 100.0, else: 0.0)`,

  avgDeviceCpu: `fetch logs
    | filter ${SNMP_FILTER}
    | sort timestamp desc
    | summarize cpu = takeFirst(toDouble(network.snmp.cpu)), by: { hostname = network.device.hostname }
    | summarize avg_cpu = avg(cpu)`,

  activeProblems: `fetch dt.davis.problems
    | filter event.status == "ACTIVE"
    | summarize problem_count = count()`,

  // ─── Overview Charts ──────────────────────────────────────────────
  systemActivityTimeline: `fetch logs
    | filter ${EPIC_FILTER} OR ${NETWORK_FILTER}
    | makeTimeseries events = count(), by: { generator.type }, interval: 5m`,

  epicEventDistribution: `fetch logs
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

  networkEventDistribution: `fetch logs
    | filter ${NETWORK_FILTER}
    | summarize cnt = count(), by: { log.source }
    | sort cnt desc`,

  // ─── Epic Health — Login & Auth ───────────────────────────────────
  loginVolumeOverTime: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(Action)
    | fieldsAdd login_status = if(
        Action == "Login Success" OR Action == "HKU_LOGIN" OR Action == "CTO_LOGIN",
        "success",
        else: "failure"
      )
    | makeTimeseries logins = count(), by: { login_status }, interval: 5m`,

  loginSuccessRateTrend: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(Action)
    | makeTimeseries
        successes = countIf(Action == "Login Success" OR Action == "HKU_LOGIN"),
        total = count(),
        interval: 5m
    | fieldsAdd rate = if(total[] > 0, successes[] / total[] * 100.0, else: 0.0)`,

  activeUsers: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(EMPid)
    | summarize unique_users = countDistinct(EMPid)`,

  loginBySite: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(Action)
    | summarize logins = count(), by: { site = healthcare.site }
    | sort logins desc`,

  // ─── Epic Health — Clinical Throughput ─────────────────────────────
  orderVolumeOverTime: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(ORDER_TYPE)
    | makeTimeseries orders = count(), by: { ORDER_TYPE }, interval: 5m`,

  departmentActivity: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(DEPARTMENT)
    | summarize events = count(), by: { DEPARTMENT }
    | sort events desc
    | limit 15`,

  clinicalEventTypes: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(ORDER_TYPE) OR isNotNull(NOTE_TYPE) OR isNotNull(MEDICATION_NAME)
    | fieldsAdd clinical_type = coalesce(ORDER_TYPE, NOTE_TYPE, "Medication")
    | summarize cnt = count(), by: { clinical_type }
    | sort cnt desc`,

  // ─── Epic Health — MyChart Portal ─────────────────────────────────
  myChartSessionsOverTime: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(patient_portal_action)
    | makeTimeseries sessions = count(), by: { patient_portal_action }, interval: 5m`,

  myChartDeviceTypes: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(device_type)
    | summarize cnt = count(), by: { device_type }
    | sort cnt desc`,

  // ─── Network Health — SNMP Device Overview ────────────────────────
  snmpCpuOverTime: `timeseries cpu = avg(` + "`network.snmp.cpu`" + `), by: {hostname}`,

  snmpMemOverTime: `timeseries mem = avg(` + "`network.snmp.memory`" + `), by: {hostname}`,

  snmpSessionsOverTime: `timeseries sessions = avg(` + "`network.snmp.sessions`" + `), by: {hostname}`,

  snmpDeviceSnapshot: `fetch logs
    | filter ${SNMP_FILTER}
    | sort timestamp desc
    | summarize
        cpu = takeFirst(toDouble(network.snmp.cpu)),
        memory = takeFirst(toDouble(network.snmp.memory)),
        sessions = takeFirst(toDouble(network.snmp.sessions)),
        interfaces_up = takeFirst(toDouble(network.snmp.interfaces_up)),
        interfaces_total = takeFirst(toDouble(network.snmp.interfaces_total)),
        vendor = takeFirst(network.device.vendor),
        site = takeFirst(healthcare.site),
        by: { hostname = network.device.hostname }`,

  snmpInventory: `fetch bizevents
    | filter event.type == "network.device.inventory"
    | sort timestamp desc
    | summarize
        vendor = takeFirst(vendor),
        model = takeFirst(model),
        role = takeFirst(role),
        site = takeFirst(site),
        management_ip = takeFirst(management_ip),
        cpu = takeFirst(toDouble(cpu)),
        memory = takeFirst(toDouble(memory)),
        sessions = takeFirst(toDouble(sessions)),
        interfaces_up = takeFirst(toDouble(interfaces_up)),
        interfaces_total = takeFirst(toDouble(interfaces_total)),
        by: { hostname }`,

  // ─── Network Health — Interface Health ────────────────────────────
  snmpIfTrafficIn: `timeseries bytes_in = sum(` + "`network.snmp.if.in_octets`" + `), by: {hostname}`,

  snmpIfTrafficOut: `timeseries bytes_out = sum(` + "`network.snmp.if.out_octets`" + `), by: {hostname}`,

  snmpIfUtilization: `timeseries util = avg(` + "`network.snmp.if.utilization`" + `), by: {hostname, interface}`,

  interfaceStateChanges: `fetch logs
    | filter log.source == "cisco_ios" AND ${NETWORK_FILTER}
    | filter matchesPhrase(content, "UPDOWN") OR matchesPhrase(content, "LINEPROTO")
    | fields timestamp, network.interface.name, network.interface.state, mnemonic, hostname, healthcare.site, content
    | sort timestamp desc
    | limit 25`,

  linkFlapDetection: `fetch logs
    | filter log.source == "cisco_ios" AND ${NETWORK_FILTER}
    | filter matchesPhrase(content, "UPDOWN") OR matchesPhrase(content, "LINEPROTO")
    | summarize flaps = count(), by: { hostname, interface = network.interface.name, bin30 = bin(timestamp, 30m) }
    | filter flaps > 3
    | sort flaps desc`,

  // ─── Network Health — Routing ─────────────────────────────────────
  routingEventsTimeline: `fetch logs
    | filter log.source == "cisco_ios" AND ${NETWORK_FILTER}
    | filter matchesPhrase(content, "OSPF") OR matchesPhrase(content, "BGP") OR isNotNull(network.routing.protocol)
    | makeTimeseries events = count(), by: { protocol = network.routing.protocol }, interval: 5m`,

  routingNeighborTable: `fetch logs
    | filter log.source == "cisco_ios" AND ${NETWORK_FILTER}
    | filter isNotNull(network.routing.protocol)
    | fields timestamp, network.routing.protocol, network.routing.state, network.routing.neighbor_ip, mnemonic, hostname
    | sort timestamp desc
    | limit 25`,

  // ─── Network Health — Firewall Connections ────────────────────────
  connectionRateOverTime: `fetch logs
    | filter ${NETWORK_FILTER}
    | filter isNotNull(network.firewall.action)
    | filter network.firewall.action == "built" OR network.firewall.action == "teardown" OR network.firewall.action == "allow" OR network.firewall.action == "accept"
    | makeTimeseries connections = count(), by: { network.firewall.action }, interval: 5m`,

  firewallThroughput: `fetch logs
    | filter ${NETWORK_FILTER}
    | filter isNotNull(network.firewall.bytes_recv) OR isNotNull(network.firewall.bytes_sent)
    | makeTimeseries bytes_in = sum(toDouble(network.firewall.bytes_recv)), bytes_out = sum(toDouble(network.firewall.bytes_sent)), interval: 5m`,

  // ─── Network Health — NetFlow Volume ──────────────────────────────
  netflowVolumeOverTime: `fetch logs
    | filter log.source == "netflow" AND ${NETWORK_FILTER}
    | summarize total_bytes = sum(toDouble(network.flow.bytes)), total_packets = sum(toDouble(network.flow.packets)), by: { interval = bin(timestamp, 5m) }`,

  netflowProtocolDist: `fetch logs
    | filter log.source == "netflow" AND ${NETWORK_FILTER}
    | summarize flows = count(), total_bytes = sum(toDouble(network.flow.bytes)), by: { network.flow.protocol }
    | sort total_bytes desc`,

  netflowTopPorts: `fetch logs
    | filter log.source == "netflow" AND ${NETWORK_FILTER}
    | summarize flows = count(), total_bytes = sum(toDouble(network.flow.bytes)), by: { network.flow.dst_port }
    | sort total_bytes desc
    | limit 20`,

  // ─── Integration Health — HL7 ─────────────────────────────────────
  hl7VolumeOverTime: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | makeTimeseries messages = count(), by: { message_type = MSH.9 }, interval: 5m`,

  hl7MessageTypes: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | summarize cnt = count(), by: { message_type = MSH.9 }
    | sort cnt desc`,

  hl7AckRateTrend: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | makeTimeseries
        acks = countIf(matchesPhrase(content, "ACK") OR matchesPhrase(content, "AA")),
        total = count(),
        interval: 5m`,

  hl7Errors: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(MSH.9)
    | filter matchesPhrase(content, "NAK") OR matchesPhrase(content, "AE") OR matchesPhrase(content, "AR") OR matchesPhrase(content, "error")
    | fields timestamp, MSH.9, MSH.10, content, healthcare.site
    | sort timestamp desc
    | limit 30`,

  // ─── Integration Health — FHIR API ────────────────────────────────
  fhirRequestRateOverTime: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | makeTimeseries requests = count(), by: { method }, interval: 5m`,

  fhirStatusDistribution: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | fieldsAdd status_group = if(toDouble(status) < 300, "2xx",
        else: if(toDouble(status) < 400, "3xx",
        else: if(toDouble(status) < 500, "4xx", else: "5xx")))
    | summarize cnt = count(), by: { status_group }
    | sort cnt desc`,

  fhirErrorRate: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | summarize
        errors = countIf(toDouble(status) >= 400),
        total = count()
    | fieldsAdd error_rate = if(total > 0, toDouble(errors) / toDouble(total) * 100.0, else: 0.0)`,

  fhirResponseTimePercentiles: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms)
    | makeTimeseries
        p50 = percentile(toDouble(response_time_ms), 50),
        p95 = percentile(toDouble(response_time_ms), 95),
        p99 = percentile(toDouble(response_time_ms), 99),
        interval: 5m`,

  fhirSlowRequests: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(response_time_ms) AND toDouble(response_time_ms) > 2000
    | fields timestamp, method, path, status, response_time_ms, client_id, healthcare.site
    | sort timestamp desc
    | limit 30`,

  fhirClientUsage: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(client_id)
    | summarize requests = count(), by: { client_id }
    | sort requests desc
    | limit 15`,

  // ─── Integration Health — ETL Jobs ────────────────────────────────
  etlJobStatusOverTime: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name)
    | makeTimeseries jobs = count(), by: { status }, interval: 5m`,

  etlJobDurationTrends: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name) AND isNotNull(duration_seconds)
    | makeTimeseries duration = avg(toDouble(duration_seconds)), by: { job_name }, interval: 5m`,

  etlRecordsProcessed: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(records_processed)
    | makeTimeseries records = sum(toDouble(records_processed)), by: { source_system }, interval: 5m`,

  etlFailedJobs: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name) AND status == "failed"
    | fields timestamp, job_name, source_system, duration_seconds, records_processed, content
    | sort timestamp desc
    | limit 30`,

  etlSuccessRate: `fetch logs
    | filter ${EPIC_FILTER}
    | filter isNotNull(job_name)
    | summarize
        successes = countIf(status == "success" OR status == "completed"),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(successes) / toDouble(total) * 100.0, else: 0.0)`,

  // ─── Site View ────────────────────────────────────────────────────
  epicEventsBySite: `fetch logs
    | filter ${EPIC_FILTER}
    | summarize
        events = count(),
        logins = countIf(isNotNull(Action)),
        login_success = countIf(Action == "Login Success" OR Action == "HKU_LOGIN"),
        by: { site = healthcare.site }
    | fieldsAdd login_rate = if(logins > 0, toDouble(login_success) / toDouble(logins) * 100.0, else: 0.0)`,

  networkHealthBySite: `fetch logs
    | filter ${SNMP_FILTER}
    | sort timestamp desc
    | summarize
        avg_cpu = avg(toDouble(network.snmp.cpu)),
        avg_mem = avg(toDouble(network.snmp.memory)),
        devices = countDistinct(network.device.hostname),
        by: { site = healthcare.site }`,

  siteCompositeHealth: `fetch logs
    | filter ${EPIC_FILTER}
    | summarize
        epic_events = count(),
        login_success = countIf(Action == "Login Success" OR Action == "HKU_LOGIN"),
        logins = countIf(isNotNull(Action)),
        by: { site = healthcare.site }
    | fieldsAdd epic_health = if(logins > 0, toDouble(login_success) / toDouble(logins) * 100.0, else: 100.0)
    | lookup [
        fetch logs
        | filter ${SNMP_FILTER}
        | sort timestamp desc
        | summarize avg_cpu = avg(toDouble(network.snmp.cpu)), by: { site = healthcare.site }
      ], sourceField: site, lookupField: site
    | fieldsRename network_cpu = lookup.avg_cpu
    | fieldsAdd network_health = if(isNotNull(network_cpu), 100.0 - network_cpu, else: 100.0)
    | fieldsAdd composite = epic_health * 0.4 + network_health * 0.3 + 85.0 * 0.3`,

  // ─── Cross-Correlation ────────────────────────────────────────────
  networkOutageEpicImpact: `fetch logs
    | filter log.source == "cisco_ios" AND ${NETWORK_FILTER}
    | filter matchesPhrase(content, "UPDOWN") OR matchesPhrase(content, "LINEPROTO")
    | filter network.interface.state == "down"
    | summarize interface_downs = count(), by: { site = healthcare.site, interval = bin(timestamp, 5m) }
    | lookup [
        fetch logs
        | filter ${EPIC_FILTER}
        | summarize epic_events = count(), by: { site = healthcare.site, interval = bin(timestamp, 5m) }
      ], sourceField: site, lookupField: site
    | fieldsRename epic_count = lookup.epic_events
    | filter interface_downs > 0
    | sort interval desc`,

  deviceCpuVsFhirLatency: `fetch logs
    | filter ${SNMP_FILTER}
    | summarize avg_cpu = avg(toDouble(network.snmp.cpu)), by: { interval = bin(timestamp, 5m) }
    | lookup [
        fetch logs
        | filter ${EPIC_FILTER} AND isNotNull(response_time_ms)
        | summarize p95_response = percentile(toDouble(response_time_ms), 95), by: { interval = bin(timestamp, 5m) }
      ], sourceField: interval, lookupField: interval
    | fieldsRename fhir_p95 = lookup.p95_response
    | sort interval desc`,

  // ─── Problems ─────────────────────────────────────────────────────
  activeProblemsList: `fetch dt.davis.problems
    | filter event.status == "ACTIVE"
    | fields event.name, event.status, event.category, event.start, management_zone, affected_entity
    | sort event.start desc`,

  problemHistory: `fetch dt.davis.problems
    | filter event.status == "CLOSED"
    | summarize
        problem_count = count(),
        avg_duration_min = avg(toDouble(event.end - event.start) / 60000000000.0),
        by: { event.category }`,

  // ─── Explore Presets ──────────────────────────────────────────────
  allEpicEvents: `fetch logs
    | filter ${EPIC_FILTER}
    | fields timestamp, Action, EMPid, IP, WorkstationID, DEPARTMENT, healthcare.site, content
    | sort timestamp desc
    | limit 100`,

  allNetworkEvents: `fetch logs
    | filter ${NETWORK_FILTER}
    | fields timestamp, log.source, hostname, facility, mnemonic, network.firewall.action, network.security.event_type, healthcare.site, content
    | sort timestamp desc
    | limit 100`,

  eventsBySite: `fetch logs
    | filter ${EPIC_FILTER} OR ${NETWORK_FILTER}
    | summarize
        epic = countIf(${EPIC_FILTER}),
        network = countIf(${NETWORK_FILTER}),
        total = count(),
        by: { site = healthcare.site }
    | sort total desc`,
};
