import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { SiteFilter } from "../components/SiteFilter";
import { toTimeseries, toTimeseriesWithThresholds, toDonutData, toBarData, type ThresholdLine } from "../utils/chartHelpers";
import { withSiteFilter } from "../utils/queryHelpers";
import { SectionHealth } from "../components/SectionHealth";

export const IntegrationHealth = () => {
  const [site, setSite] = useState<string | null>(null);
  const f = (q: string) => withSiteFilter(q, site, "epic");

  return (
  <Flex flexDirection="column" gap={16} padding={16}>
    <Text style={{ fontSize: 13, opacity: 0.6, marginBottom: -8 }}>
      Integration pipeline health — HL7 message delivery and ORC action types, FHIR REST API request rates with response time percentiles, and ETL batch job status with failure tracking.
    </Text>
    <SiteFilter value={site} onChange={setSite} />
    <Flex gap={12} flexWrap="wrap">
      <KpiCard query={f(queries.hl7DeliveryRate)} label="HL7 Delivery" field="delivery_rate" format="percent" thresholds={{ green: 99, amber: 90 }} icon="📡" />
      <KpiCard query={f(queries.fhirHealthRate)} label="FHIR API Health" field="success_rate" format="percent" thresholds={{ green: 88, amber: 75 }} icon="🔗" />
      <KpiCard query={f(queries.fhirErrorRate)} label="FHIR Error Rate" field="error_rate" format="percent" thresholds={{ green: 12, amber: 20 }} invertThresholds icon="⚠️" />
      <KpiCard query={f(queries.etlSuccessRate)} label="ETL Success" field="success_rate" format="percent" thresholds={{ green: 90, amber: 80 }} icon="⚙️" />
      <KpiCard query={f(queries.hl7RecentVolume)} label="HL7 Vol/5min" field="hl7_volume" format="number" thresholds={{ green: 5, amber: 1 }} icon="📨" />
      <KpiCard query={queries.mirthChannelHealth} label="Mirth Channels" field="health_pct" format="percent" thresholds={{ green: 100, amber: 90 }} icon="🔌" />
    </Flex>

    {/* Mirth Connect Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <Flex alignItems="center">
        <TitleBar><TitleBar.Title>Mirth Connect</TitleBar.Title><TitleBar.Subtitle>Integration engine — queue depths, message latency, connector states, and retry storms</TitleBar.Subtitle></TitleBar>
        <SectionHealth query={queries.mirthChannelHealth} field="health_pct" green={100} amber={90} description="Percentage of Mirth Connect channels actively processing messages. Drops when HL7 VLAN network issues cause channel queues to back up and channels to stop." />
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Queue Depth</Text>
          <TsChart query={queries.mirthQueueDepth} thresholds={[{ label: "Warning", value: 100 }, { label: "Critical", value: 500 }]} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Error Rate</Text>
          <TsChart query={queries.mirthErrorRate} />
        </div>
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Processing Time (ms)</Text>
          <TsChart query={queries.mirthProcessingTime} thresholds={[{ label: "SLA 500ms", value: 500 }, { label: "Critical 2s", value: 2000 }]} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Send Attempts (retries)</Text>
          <TsChart query={queries.mirthSendAttempts} />
        </div>
      </Flex>
      <MirthTable />
    </Surface>

    {/* HL7 Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <Flex alignItems="center">
        <TitleBar><TitleBar.Title>HL7 Interface</TitleBar.Title><TitleBar.Subtitle>Message volume and ORC action types</TitleBar.Subtitle></TitleBar>
        <SectionHealth query={f(queries.hl7DeliveryRate)} field="delivery_rate" green={99} amber={90} description="Checks whether HL7 v2.x messages (ADT, ORM, ORU) are actively flowing in 5-minute intervals. Drops to 0% when the interface engine stops delivering messages, indicating a Bridges/Cloverleaf outage." />
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 2 }}><TsChart query={f(queries.hl7VolumeOverTime)} thresholds={[{ label: "Min Expected", value: 10 }]} /></div>
        <div style={{ flex: 1 }}><PieChart query={f(queries.hl7MessageBreakdown)} /></div>
      </Flex>
      <HL7Table site={site} />
    </Surface>

    {/* FHIR Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <Flex alignItems="center">
        <TitleBar><TitleBar.Title>FHIR API</TitleBar.Title><TitleBar.Subtitle>REST API request rates, response times, and status codes</TitleBar.Subtitle></TitleBar>
        <SectionHealth query={f(queries.fhirHealthRate)} field="success_rate" green={88} amber={75} description="Ratio of FHIR R4 API calls returning HTTP 2xx/3xx vs 4xx/5xx. Degradation signals API gateway issues, expired OAuth tokens, or backend Interconnect server overload." />
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Request Rate</Text>
          <TsChart query={f(queries.fhirRequestRateOverTime)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Response Percentiles</Text>
          <TsChart query={f(queries.fhirResponseTimePercentiles)} thresholds={[{ label: "SLA 500ms", value: 500 }]} />
        </div>
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Status Codes</Text>
          <PieChart query={f(queries.fhirStatusDistribution)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Client Usage</Text>
          <BarChart query={f(queries.fhirClientUsage)} />
        </div>
      </Flex>
    </Surface>

    {/* ETL Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <Flex alignItems="center">
        <TitleBar><TitleBar.Title>ETL Pipelines</TitleBar.Title><TitleBar.Subtitle>Batch job status and duration trends</TitleBar.Subtitle></TitleBar>
        <SectionHealth query={f(queries.etlSuccessRate)} field="success_rate" green={90} amber={80} description="Success rate of completed ETL batch jobs (excludes in-progress RUNNING jobs). Counts SUCCESS and SUCCESS_WITH_WARNINGS as healthy. Failures indicate Clarity/Caboodle load problems or source system timeouts." />
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}><TsChart query={f(queries.etlJobStatusOverTime)} /></div>
        <div style={{ flex: 1 }}><TsChart query={f(queries.etlJobDurationTrends)} /></div>
      </Flex>
      <ETLFailedTable site={site} />
    </Surface>
  </Flex>
  );
};

const TsChart = ({ query, thresholds }: { query: string; thresholds?: ThresholdLine[] }) => {
  const result = useDql({ query });
  if (result.isLoading) return <ProgressCircle />;
  const series = thresholds ? toTimeseriesWithThresholds(result.data, thresholds) : toTimeseries(result.data);
  return <TimeseriesChart data={series} gapPolicy="connect" />;
};

const BarChart = ({ query }: { query: string }) => {
  const { data, isLoading } = useDql({ query });
  if (isLoading) return <ProgressCircle />;
  return <CategoricalBarChart data={toBarData(data?.records ?? [])} />;
};

const PieChart = ({ query }: { query: string }) => {
  const { data, isLoading } = useDql({ query });
  if (isLoading) return <ProgressCircle />;
  return <DonutChart data={toDonutData(data?.records ?? [])} />;
};

const HL7Table = ({ site }: { site: string | null }) => {
  const { data, isLoading } = useDql({ query: withSiteFilter(queries.hl7RecentMessages, site, "epic") });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <Text style={{ padding: 16, opacity: 0.5 }}>No HL7 messages</Text>;
  return (
    <div style={{ maxHeight: 250, overflow: "auto", fontSize: 12, marginTop: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr><th style={TH}>Time</th><th style={TH}>Message Type</th><th style={TH}>Control ID</th><th style={TH}>ORC Action</th><th style={TH}>Site</th></tr></thead>
        <tbody>
          {records.map((r: any, i: number) => (
            <tr key={i}>
              <td style={TD}>{new Date(r.timestamp).toLocaleTimeString()}</td>
              <td style={TD}>{r["MSH.9"]}</td>
              <td style={TD}>{r["MSH.10"] ?? "—"}</td>
              <td style={TD}>{r.orc_action ?? "—"}</td>
              <td style={TD}>{r["healthcare.site"] ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const ETLFailedTable = ({ site }: { site: string | null }) => {
  const { data, isLoading } = useDql({ query: withSiteFilter(queries.etlFailedJobs, site, "epic") });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <Text style={{ padding: 16, opacity: 0.5, display: "block", marginTop: 12 }}>No failed ETL jobs — all passing ✓</Text>;
  return (
    <div style={{ maxHeight: 250, overflow: "auto", fontSize: 12, marginTop: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr><th style={TH}>Time</th><th style={TH}>Job</th><th style={TH}>Source</th><th style={TH}>Duration</th></tr></thead>
        <tbody>
          {records.map((r: any, i: number) => (
            <tr key={i}><td style={TD}>{new Date(r.timestamp).toLocaleTimeString()}</td><td style={{ ...TD, color: "#dc3545" }}>{r.job_name}</td><td style={TD}>{r.source_system ?? "—"}</td><td style={TD}>{r.duration_seconds ? `${r.duration_seconds}s` : "—"}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const CONNECTION_STATES: Record<number, { label: string; color?: string }> = {
  0: { label: "Idle" },
  1: { label: "Connected" },
  2: { label: "Sending" },
  3: { label: "Waiting" },
  4: { label: "Connecting", color: "#ffc107" },
  5: { label: "Disconnected", color: "#dc3545" },
  6: { label: "Failure", color: "#dc3545" },
};

const MirthTable = () => {
  const { data, isLoading } = useDql({ query: queries.mirthChannelSummary });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <Text style={{ padding: 16, opacity: 0.5 }}>No Mirth data yet</Text>;
  return (
    <div style={{ maxHeight: 250, overflow: "auto", fontSize: 12, marginTop: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr><th style={TH}>Channel</th><th style={TH}>State</th><th style={TH}>Recv/5m</th><th style={TH}>Err/5m</th><th style={TH}>Queue</th><th style={TH}>Latency</th><th style={TH}>Retries/5m</th></tr></thead>
        <tbody>
          {records.map((r: any, i: number) => {
            const stateNum = r.last_state != null ? Math.round(r.last_state) : null;
            const stateInfo = stateNum != null ? (CONNECTION_STATES[stateNum] ?? { label: `Unknown(${stateNum})` }) : null;
            const pt = r.last_pt != null ? Math.round(r.last_pt) : null;
            return (
            <tr key={i}>
              <td style={TD}>{r["channel.name"]}</td>
              <td style={{ ...TD, color: stateInfo?.color }}>{stateInfo?.label ?? "—"}</td>
              <td style={TD}>{r.last_received != null ? Math.round(r.last_received) : "—"}</td>
              <td style={{ ...TD, color: (r.last_errors ?? 0) > 5 ? "#dc3545" : undefined }}>{r.last_errors != null ? Math.round(r.last_errors) : "—"}</td>
              <td style={{ ...TD, color: (r.last_queue ?? 0) > 100 ? "#dc3545" : (r.last_queue ?? 0) > 20 ? "#ffc107" : undefined }}>{r.last_queue != null ? Math.round(r.last_queue) : "—"}</td>
              <td style={{ ...TD, color: pt != null && pt > 500 ? "#dc3545" : pt != null && pt > 200 ? "#ffc107" : undefined }}>{pt != null ? `${pt}ms` : "—"}</td>
              <td style={TD}>{r.last_attempts != null ? Math.round(r.last_attempts) : "—"}</td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const TH: React.CSSProperties = { padding: "6px 8px", textAlign: "left", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", fontWeight: 600 };
const TD: React.CSSProperties = { padding: "4px 8px", borderBottom: "1px solid var(--dt-colors-border-neutral-default)" };
