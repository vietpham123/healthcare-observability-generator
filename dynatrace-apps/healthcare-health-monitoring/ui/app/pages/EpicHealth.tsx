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
      <KpiCard query={f(queries.epicLoginSuccessRate)} label="Login Success Rate" field="success_rate" format="percent" thresholds={{ green: 65, amber: 45 }} icon="🔐" />
      <KpiCard query={f(queries.totalEpicEvents)} label="Total Epic Events" field="total" format="number" icon="📊" />
      <KpiCard query={f(queries.activeUsers)} label="Active Users" field="unique_users" format="number" icon="👥" />
      <KpiCard query={f(queries.statOrderRate)} label="STAT Order %" field="stat_pct" format="percent" thresholds={{ green: 5, amber: 10 }} invertThresholds icon="🚑" />
    </Flex>

    {/* Authentication Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <Flex alignItems="center">
        <TitleBar><TitleBar.Title>Authentication</TitleBar.Title><TitleBar.Subtitle>Login success/failure trends and site distribution</TitleBar.Subtitle></TitleBar>
        <SectionHealth query={f(queries.epicLoginSuccessRate)} field="success_rate" green={65} amber={45} description="Tracks all Epic login outcomes (BCA_LOGIN_SUCCESS, FAILEDLOGIN, LOGIN_BLOCKED, WPSEC_LOGIN_FAIL). Degrades when failed or blocked logins spike — often the first sign of credential stuffing or account lockout events." />
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Login Volume Over Time</Text>
          <TsChart query={f(queries.loginVolumeOverTime)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Logins by Site</Text>
          <BarChart query={f(queries.loginBySite)} />
        </div>
      </Flex>
    </Surface>

    {/* Clinical Activity Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <Flex alignItems="center">
        <TitleBar><TitleBar.Title>Clinical Activity</TitleBar.Title><TitleBar.Subtitle>Orders, HL7 message types, and department workload</TitleBar.Subtitle></TitleBar>
        <SectionHealth query={f(queries.statOrderRate)} field="stat_pct" green={5} amber={10} invert description="Percentage of clinical orders marked STAT (urgent). A normal baseline is under 5%. A surge suggests an ED mass-casualty event or system-wide clinical escalation." />
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Clinical Order Volume</Text>
          <TsChart query={f(queries.orderVolumeOverTime)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>HL7 by Message Type</Text>
          <TsChart query={f(queries.hl7ByMessageType)} />
        </div>
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Department Activity</Text>
          <BarChart query={f(queries.departmentActivity)} />
        </div>
      </Flex>
    </Surface>

    {/* SIEM & Security Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>SIEM & Security Audit</TitleBar.Title><TitleBar.Subtitle>All Epic audit event types (E1Mid) and security incidents</TitleBar.Subtitle></TitleBar>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 2 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Event Types (E1Mid)</Text>
          <BarChart query={f(queries.siemEventsByType)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Security Events</Text>
          <SecurityTable site={site} />
        </div>
      </Flex>
    </Surface>

    {/* Service Audit Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>Interconnect Service Audit</TitleBar.Title><TitleBar.Subtitle>API service category, type, and instance distribution from IC_SERVICE_AUDIT events</TitleBar.Subtitle></TitleBar>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Service Category Over Time</Text>
          <TsChart query={f(queries.serviceCategoryOverTime)} />
        </div>
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>API Category Breakdown</Text>
          <BarChart query={f(queries.apiCategoryBreakdown)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Service Type</Text>
          <BarChart query={f(queries.serviceTypeDistribution)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Instance URN</Text>
          <BarChart query={f(queries.instanceUrnDistribution)} />
        </div>
      </Flex>
    </Surface>

    {/* Workstation Activity Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>Workstation Activity</TitleBar.Title><TitleBar.Subtitle>Login volume per workstation and failure hotspots</TitleBar.Subtitle></TitleBar>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Top Workstations by Login Volume</Text>
          <BarChart query={f(queries.loginByWorkstation)} />
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
