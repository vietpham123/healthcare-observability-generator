import React from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart } from "@dynatrace/strato-components-preview/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";

export const EpicHealth = () => {
  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      {/* KPIs */}
      <Flex gap={12} flexWrap="wrap">
        <KpiCard
          query={queries.epicLoginSuccessRate}
          label="Login Success Rate"
          field="success_rate"
          format="percent"
          thresholds={{ green: 90, amber: 70 }}
          icon="🔐"
        />
        <KpiCard
          query={queries.totalEpicEvents}
          label="Total Epic Events"
          field="total"
          format="number"
          icon="📊"
        />
        <KpiCard
          query={queries.activeUsers}
          label="Active Users"
          field="unique_users"
          format="number"
          icon="👥"
        />
      </Flex>

      {/* Login Section */}
      <Flex gap={16}>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar>
            <TitleBar.Title>Login Volume</TitleBar.Title>
            <TitleBar.Subtitle>Success vs failure over time (parsed from E1Mid)</TitleBar.Subtitle>
          </TitleBar>
          <ChartWrapper query={queries.loginVolumeOverTime} type="timeseries" />
        </Surface>

        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar>
            <TitleBar.Title>Logins by Site</TitleBar.Title>
          </TitleBar>
          <ChartWrapper query={queries.loginBySite} type="bar" />
        </Surface>
      </Flex>

      {/* Clinical Section */}
      <Flex gap={16}>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar>
            <TitleBar.Title>Clinical Order Volume</TitleBar.Title>
          </TitleBar>
          <ChartWrapper query={queries.orderVolumeOverTime} type="timeseries" />
        </Surface>

        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar>
            <TitleBar.Title>Department Activity</TitleBar.Title>
          </TitleBar>
          <ChartWrapper query={queries.departmentActivity} type="bar" />
        </Surface>
      </Flex>

      {/* SIEM Events Breakdown */}
      <Flex gap={16}>
        <Surface style={{ flex: 2, padding: 16, borderRadius: 12 }}>
          <TitleBar>
            <TitleBar.Title>SIEM Event Types (E1Mid)</TitleBar.Title>
            <TitleBar.Subtitle>All audit event types from Epic</TitleBar.Subtitle>
          </TitleBar>
          <ChartWrapper query={queries.siemEventsByType} type="bar" />
        </Surface>

        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar>
            <TitleBar.Title>Security Events</TitleBar.Title>
            <TitleBar.Subtitle>Break-the-glass, failed logins, blocked</TitleBar.Subtitle>
          </TitleBar>
          <SecurityTable />
        </Surface>
      </Flex>
    </Flex>
  );
};

const ChartWrapper = ({ query, type }: { query: string; type: "timeseries" | "bar" | "donut" }) => {
  const { data, isLoading } = useDql({ query });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (type === "timeseries") return <TimeseriesChart data={records as any} />;
  if (type === "bar") return <CategoricalBarChart data={records as any} />;
  return <DonutChart data={records as any} />;
};

const SecurityTable = () => {
  const { data, isLoading } = useDql({ query: queries.securityEvents });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <div style={{ padding: 20, opacity: 0.5 }}>No security events found</div>;

  return (
    <div style={{ maxHeight: 300, overflow: "auto", fontSize: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={TH}>Time</th>
            <th style={TH}>Event</th>
            <th style={TH}>User</th>
            <th style={TH}>Site</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r: any, i: number) => (
            <tr key={i}>
              <td style={TD}>{new Date(r.timestamp).toLocaleTimeString()}</td>
              <td style={{ ...TD, color: "#dc3545" }}>{r.e1mid}</td>
              <td style={TD}>{r.EMPid ?? "—"}</td>
              <td style={TD}>{r["healthcare.site"] ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const TH: React.CSSProperties = { padding: "6px 8px", textAlign: "left", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", fontWeight: 600 };
const TD: React.CSSProperties = { padding: "4px 8px", borderBottom: "1px solid var(--dt-colors-border-neutral-default)" };
