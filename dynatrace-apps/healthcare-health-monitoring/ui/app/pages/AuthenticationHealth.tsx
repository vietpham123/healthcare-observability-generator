import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { SiteFilter } from "../components/SiteFilter";
import { SectionHealth } from "../components/SectionHealth";
import { toTimeseries, toDonutData, toBarData } from "../utils/chartHelpers";
import { withSiteFilter } from "../utils/queryHelpers";

export const AuthenticationHealth = () => {
  const [site, setSite] = useState<string | null>(null);
  const f = (q: string) => withSiteFilter(q, site, "epic");

  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      <Text style={{ fontSize: 13, opacity: 0.6, marginBottom: -8 }}>
        Authentication Health — login success/failure analysis using Epic BCA_LOGIN_SUCCESS and FAILEDLOGIN events, workstation activity, client type distribution, and login context insights.
      </Text>
      <SiteFilter value={site} onChange={setSite} />

      {/* KPI Row */}
      <Flex gap={12} flexWrap="wrap">
        <KpiCard query={f(queries.authLoginSuccessRate)} label="Auth Success Rate" field="success_rate" format="percent" thresholds={{ green: 80, amber: 60 }} icon="🔐" />
        <KpiCard query={f(queries.authFailedLoginCount)} label="Failed Logins" field="total" format="number" thresholds={{ green: 200, amber: 500 }} invertThresholds icon="🚫" />
        <KpiCard query={f(queries.activeWorkstationCount)} label="Active Workstations" field="active_ws" format="number" icon="🖥️" />
        <KpiCard query={f(queries.ldapLoginCount)} label="LDAP Users" field="ldap_users" format="number" icon="👤" />
      </Flex>

      {/* Auth Trends Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <Flex alignItems="center">
          <TitleBar>
            <TitleBar.Title>Authentication Trends</TitleBar.Title>
            <TitleBar.Subtitle>Login success vs failure over time, error type analysis</TitleBar.Subtitle>
          </TitleBar>
          <SectionHealth query={f(queries.authLoginSuccessRate)} field="success_rate" green={80} amber={60} description="Measures BCA_LOGIN_SUCCESS vs FAILEDLOGIN ratio. A drop indicates credential issues, LDAP failures, or a brute-force attack targeting the Epic authentication layer." />
        </Flex>
        <div style={{ marginTop: 12 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Login Success vs Failure</Text>
          <TsChart query={f(queries.loginSuccessVsFailure)} />
        </div>
        <Flex gap={16} style={{ marginTop: 16 }}>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Login Error Types</Text>
            <BarChart query={f(queries.loginErrorTypeBreakdown)} />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Internet Area</Text>
            <PieChart query={f(queries.loginInternetAreaDistribution)} />
          </div>
        </Flex>
      </Surface>

      {/* Client & Context Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar>
          <TitleBar.Title>Login Sources & Context</TitleBar.Title>
          <TitleBar.Subtitle>Client type, login context, and login source distribution across authentication events</TitleBar.Subtitle>
        </TitleBar>
        <Flex gap={16} style={{ marginTop: 12 }}>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Client Type</Text>
            <PieChart query={f(queries.loginClientTypeDistribution)} />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Login Context</Text>
            <PieChart query={f(queries.loginContextDistribution)} />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Login Source</Text>
            <BarChart query={f(queries.loginSourceDistribution)} />
          </div>
        </Flex>
      </Surface>

      {/* Workstation Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar>
          <TitleBar.Title>Workstation Activity</TitleBar.Title>
          <TitleBar.Subtitle>Login volume and failure rates per workstation</TitleBar.Subtitle>
        </TitleBar>
        <Flex gap={16} style={{ marginTop: 12 }}>
          <div style={{ flex: 2 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Top Workstations (Total / Failures)</Text>
            <WorkstationTable query={f(queries.loginByWorkstation)} />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Failed Logins by Workstation</Text>
            <BarChart query={f(queries.failedLoginsByWorkstation)} />
          </div>
        </Flex>
      </Surface>
    </Flex>
  );
};

// ── Reusable chart wrappers ───────────────────────────────────────

const TsChart = ({ query }: { query: string }) => {
  const result = useDql({ query });
  if (result.isLoading) return <ProgressCircle />;
  return <TimeseriesChart data={toTimeseries(result.data)} gapPolicy="connect" />;
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

const WorkstationTable = ({ query }: { query: string }) => {
  const { data, isLoading } = useDql({ query });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <div style={{ padding: 20, opacity: 0.5 }}>No workstation data</div>;
  return (
    <div style={{ maxHeight: 350, overflow: "auto", fontSize: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={TH}>Workstation</th>
            <th style={TH}>Total</th>
            <th style={TH}>Failures</th>
            <th style={TH}>Fail %</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r: any, i: number) => {
            const total = Number(r.total) || 0;
            const failures = Number(r.failures) || 0;
            const failPct = total > 0 ? ((failures / total) * 100).toFixed(1) : "0.0";
            return (
              <tr key={i}>
                <td style={TD}>{r.WorkstationID ?? "—"}</td>
                <td style={TD}>{total}</td>
                <td style={{ ...TD, color: failures > 0 ? "#dc3545" : undefined }}>{failures}</td>
                <td style={{ ...TD, color: Number(failPct) > 20 ? "#dc3545" : Number(failPct) > 5 ? "#ffc107" : undefined }}>{failPct}%</td>
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
