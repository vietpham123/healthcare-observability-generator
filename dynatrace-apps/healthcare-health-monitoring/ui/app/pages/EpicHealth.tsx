import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { SiteFilter } from "../components/SiteFilter";
import { toTimeseries, toDonutData, toBarData } from "../utils/chartHelpers";
import { withSiteFilter } from "../utils/queryHelpers";

export const EpicHealth = () => {
  const [site, setSite] = useState<string | null>(null);
  const f = (q: string) => withSiteFilter(q, site, "epic");

  return (
  <Flex flexDirection="column" gap={16} padding={16}>
    <Text style={{ fontSize: 13, opacity: 0.6, marginBottom: -8 }}>
      Epic EHR system health — authentication success rates, SIEM audit events (E1Mid), clinical order volume, department activity, and security events including break-the-glass access.
    </Text>
    <SiteFilter value={site} onChange={setSite} />
    <Flex gap={12} flexWrap="wrap">
      <KpiCard query={f(queries.epicLoginSuccessRate)} label="Login Success Rate" field="success_rate" format="percent" thresholds={{ green: 90, amber: 70 }} icon="🔐" />
      <KpiCard query={f(queries.totalEpicEvents)} label="Total Epic Events" field="total" format="number" icon="📊" />
      <KpiCard query={f(queries.activeUsers)} label="Active Users" field="unique_users" format="number" icon="👥" />
    </Flex>

    <Flex gap={16}>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Login Volume</TitleBar.Title><TitleBar.Subtitle>Success vs failure over time (parsed from E1Mid)</TitleBar.Subtitle></TitleBar>
        <TsChart query={f(queries.loginVolumeOverTime)} />
      </Surface>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Logins by Site</TitleBar.Title></TitleBar>
        <BarChart query={f(queries.loginBySite)} />
      </Surface>
    </Flex>

    <Flex gap={16}>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Clinical Order Volume</TitleBar.Title></TitleBar>
        <TsChart query={f(queries.orderVolumeOverTime)} />
      </Surface>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Department Activity</TitleBar.Title></TitleBar>
        <BarChart query={f(queries.departmentActivity)} />
      </Surface>
    </Flex>

    <Flex gap={16}>
      <Surface style={{ flex: 2, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>SIEM Event Types (E1Mid)</TitleBar.Title><TitleBar.Subtitle>All audit event types from Epic</TitleBar.Subtitle></TitleBar>
        <BarChart query={f(queries.siemEventsByType)} />
      </Surface>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Security Events</TitleBar.Title><TitleBar.Subtitle>Break-the-glass, failed logins, blocked</TitleBar.Subtitle></TitleBar>
        <SecurityTable site={site} />
      </Surface>
    </Flex>
  </Flex>
  );
};

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

const SecurityTable = ({ site }: { site: string | null }) => {
  const q = withSiteFilter(queries.securityEvents, site, "epic");
  const { data, isLoading } = useDql({ query: q });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <div style={{ padding: 20, opacity: 0.5 }}>No security events found</div>;
  return (
    <div style={{ maxHeight: 300, overflow: "auto", fontSize: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr><th style={TH}>Time</th><th style={TH}>Event</th><th style={TH}>User</th><th style={TH}>Site</th></tr></thead>
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
