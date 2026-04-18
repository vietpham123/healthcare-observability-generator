import React from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart } from "@dynatrace/strato-components-preview/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";

export const IntegrationHealth = () => {
  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      {/* KPI row */}
      <Flex gap={12} flexWrap="wrap">
        <KpiCard
          query={queries.hl7DeliveryRate}
          label="HL7 Delivery"
          field="delivery_rate"
          format="percent"
          thresholds={{ green: 95, amber: 80 }}
          icon="📡"
        />
        <KpiCard
          query={queries.fhirHealthRate}
          label="FHIR API Health"
          field="success_rate"
          format="percent"
          thresholds={{ green: 95, amber: 85 }}
          icon="🔗"
        />
        <KpiCard
          query={queries.fhirErrorRate}
          label="FHIR Error Rate"
          field="error_rate"
          format="percent"
          thresholds={{ green: 5, amber: 10 }}
          icon="⚠️"
        />
        <KpiCard
          query={queries.etlSuccessRate}
          label="ETL Success"
          field="success_rate"
          format="percent"
          thresholds={{ green: 95, amber: 80 }}
          icon="⚙️"
        />
      </Flex>

      {/* HL7 Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar>
          <TitleBar.Title>HL7 Interface</TitleBar.Title>
          <TitleBar.Subtitle>Message volume and ORC action types</TitleBar.Subtitle>
        </TitleBar>
        <Flex gap={16} style={{ marginTop: 12 }}>
          <div style={{ flex: 2 }}>
            <ChartW query={queries.hl7VolumeOverTime} type="timeseries" />
          </div>
          <div style={{ flex: 1 }}>
            <ChartW query={queries.hl7MessageBreakdown} type="donut" />
          </div>
        </Flex>
        <HL7Table />
      </Surface>

      {/* FHIR Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar>
          <TitleBar.Title>FHIR API</TitleBar.Title>
          <TitleBar.Subtitle>REST API request rates, response times, and status codes</TitleBar.Subtitle>
        </TitleBar>
        <Flex gap={16} style={{ marginTop: 12 }}>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Request Rate</Text>
            <ChartW query={queries.fhirRequestRateOverTime} type="timeseries" />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Response Percentiles</Text>
            <ChartW query={queries.fhirResponseTimePercentiles} type="timeseries" />
          </div>
        </Flex>
        <Flex gap={16} style={{ marginTop: 12 }}>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Status Codes</Text>
            <ChartW query={queries.fhirStatusDistribution} type="donut" />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Client Usage</Text>
            <ChartW query={queries.fhirClientUsage} type="bar" />
          </div>
        </Flex>
      </Surface>

      {/* ETL Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar>
          <TitleBar.Title>ETL Pipelines</TitleBar.Title>
          <TitleBar.Subtitle>Batch job status and duration trends</TitleBar.Subtitle>
        </TitleBar>
        <Flex gap={16} style={{ marginTop: 12 }}>
          <div style={{ flex: 1 }}>
            <ChartW query={queries.etlJobStatusOverTime} type="timeseries" />
          </div>
          <div style={{ flex: 1 }}>
            <ChartW query={queries.etlJobDurationTrends} type="timeseries" />
          </div>
        </Flex>
        <ETLFailedTable />
      </Surface>
    </Flex>
  );
};

const ChartW = ({ query, type }: { query: string; type: "timeseries" | "bar" | "donut" }) => {
  const { data, isLoading } = useDql({ query });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (type === "timeseries") return <TimeseriesChart data={records as any} />;
  if (type === "bar") return <CategoricalBarChart data={records as any} />;
  return <DonutChart data={records as any} />;
};

const HL7Table = () => {
  const { data, isLoading } = useDql({ query: queries.hl7RecentMessages });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <Text style={{ padding: 16, opacity: 0.5 }}>No HL7 messages</Text>;

  return (
    <div style={{ maxHeight: 250, overflow: "auto", fontSize: 12, marginTop: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={TH}>Time</th>
            <th style={TH}>Message Type</th>
            <th style={TH}>Control ID</th>
            <th style={TH}>ORC Action</th>
            <th style={TH}>Site</th>
          </tr>
        </thead>
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
        <thead>
          <tr>
            <th style={TH}>Time</th>
            <th style={TH}>Job</th>
            <th style={TH}>Source</th>
            <th style={TH}>Duration</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r: any, i: number) => (
            <tr key={i}>
              <td style={TD}>{new Date(r.timestamp).toLocaleTimeString()}</td>
              <td style={{ ...TD, color: "#dc3545" }}>{r.job_name}</td>
              <td style={TD}>{r.source_system ?? "—"}</td>
              <td style={TD}>{r.duration_seconds ? `${r.duration_seconds}s` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const TH: React.CSSProperties = { padding: "6px 8px", textAlign: "left", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", fontWeight: 600 };
const TD: React.CSSProperties = { padding: "4px 8px", borderBottom: "1px solid var(--dt-colors-border-neutral-default)" };
