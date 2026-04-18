import React from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { toTimeseries, toDonutData, toBarData } from "../utils/chartHelpers";

export const IntegrationHealth = () => (
  <Flex flexDirection="column" gap={16} padding={16}>
    <Flex gap={12} flexWrap="wrap">
      <KpiCard query={queries.hl7DeliveryRate} label="HL7 Delivery" field="delivery_rate" format="percent" thresholds={{ green: 95, amber: 80 }} icon="📡" />
      <KpiCard query={queries.fhirHealthRate} label="FHIR API Health" field="success_rate" format="percent" thresholds={{ green: 95, amber: 85 }} icon="🔗" />
      <KpiCard query={queries.fhirErrorRate} label="FHIR Error Rate" field="error_rate" format="percent" thresholds={{ green: 5, amber: 10 }} icon="⚠️" />
      <KpiCard query={queries.etlSuccessRate} label="ETL Success" field="success_rate" format="percent" thresholds={{ green: 95, amber: 80 }} icon="⚙️" />
    </Flex>

    {/* HL7 Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>HL7 Interface</TitleBar.Title><TitleBar.Subtitle>Message volume and ORC action types</TitleBar.Subtitle></TitleBar>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 2 }}><TsChart query={queries.hl7VolumeOverTime} /></div>
        <div style={{ flex: 1 }}><PieChart query={queries.hl7MessageBreakdown} /></div>
      </Flex>
      <HL7Table />
    </Surface>

    {/* FHIR Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>FHIR API</TitleBar.Title><TitleBar.Subtitle>REST API request rates, response times, and status codes</TitleBar.Subtitle></TitleBar>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Request Rate</Text>
          <TsChart query={queries.fhirRequestRateOverTime} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Response Percentiles</Text>
          <TsChart query={queries.fhirResponseTimePercentiles} />
        </div>
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Status Codes</Text>
          <PieChart query={queries.fhirStatusDistribution} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Client Usage</Text>
          <BarChart query={queries.fhirClientUsage} />
        </div>
      </Flex>
    </Surface>

    {/* ETL Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>ETL Pipelines</TitleBar.Title><TitleBar.Subtitle>Batch job status and duration trends</TitleBar.Subtitle></TitleBar>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}><TsChart query={queries.etlJobStatusOverTime} /></div>
        <div style={{ flex: 1 }}><TsChart query={queries.etlJobDurationTrends} /></div>
      </Flex>
      <ETLFailedTable />
    </Surface>
  </Flex>
);

const TsChart = ({ query }: { query: string }) => {
  const result = useDql({ query });
  if (result.isLoading) return <ProgressCircle />;
  return <TimeseriesChart data={toTimeseries(result.data)} />;
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

const HL7Table = () => {
  const { data, isLoading } = useDql({ query: queries.hl7RecentMessages });
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

const ETLFailedTable = () => {
  const { data, isLoading } = useDql({ query: queries.etlFailedJobs });
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

const TH: React.CSSProperties = { padding: "6px 8px", textAlign: "left", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", fontWeight: 600 };
const TD: React.CSSProperties = { padding: "4px 8px", borderBottom: "1px solid var(--dt-colors-border-neutral-default)" };
