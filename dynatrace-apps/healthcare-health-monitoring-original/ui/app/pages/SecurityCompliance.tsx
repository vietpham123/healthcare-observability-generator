import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries, EPIC_FILTER } from "../queries";
import { KpiCard } from "../components/KpiCard";import { SiteFilter } from "../components/SiteFilter";
import { toTimeseries, toDonutData, toBarData } from "../utils/chartHelpers";
import { withSiteFilter } from "../utils/queryHelpers";
import { SectionHealth } from "../components/SectionHealth";

// ── Security-specific DQL queries ─────────────────────────────────

const securityQueries = {
  breakTheGlassCount: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT"
    | summarize total = count()`,

  failedLoginCount: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "FAILEDLOGIN" OR e1mid == "LOGIN_BLOCKED" OR e1mid == "WPSEC_LOGIN_FAIL"
    | summarize total = count()`,

  securityEventsOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT" OR e1mid == "FAILEDLOGIN" OR e1mid == "LOGIN_BLOCKED" OR e1mid == "WPSEC_LOGIN_FAIL"
    | fieldsAdd event_category = if(
        e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT",
        "Break-the-Glass",
        else: if(e1mid == "FAILEDLOGIN", "Failed Login",
        else: if(e1mid == "LOGIN_BLOCKED", "Login Blocked",
        else: "Security Fail")))
    | makeTimeseries events = count(), by: { event_category }, interval: 5m`,

  breakTheGlassByUser: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT"
    | summarize count = count(), by: { user = EMPid }
    | sort count desc
    | limit 15`,

  failedLoginsByHour: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "FAILEDLOGIN" OR e1mid == "LOGIN_BLOCKED" OR e1mid == "WPSEC_LOGIN_FAIL"
    | fieldsAdd hour = getHour(timestamp)
    | summarize count = count(), by: { hour }
    | sort hour asc`,

  securityBySite: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT" OR e1mid == "FAILEDLOGIN" OR e1mid == "LOGIN_BLOCKED" OR e1mid == "WPSEC_LOGIN_FAIL"
    | fieldsAdd event_category = if(
        e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT",
        "Break-the-Glass",
        else: "Auth Failure")
    | summarize count = count(), by: { site = healthcare.site, event_category }
    | sort count desc`,

  afterHoursAccess: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT"
    | fieldsAdd hour = getHour(timestamp)
    | filter hour >= 22 OR hour < 6
    | fields timestamp, e1mid, EMPid, healthcare.site
    | sort timestamp desc
    | limit 30`,

  recentSecurityEvents: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT" OR e1mid == "FAILEDLOGIN" OR e1mid == "LOGIN_BLOCKED" OR e1mid == "WPSEC_LOGIN_FAIL"
    | fields timestamp, e1mid, EMPid, DEPARTMENT, healthcare.site
    | sort timestamp desc
    | limit 50`,

  /** Total security event count — drives Security Events section health */
  totalSecurityEventCount: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "AC_BREAK_THE_GLASS_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_FAILED_ACCESS" OR e1mid == "AC_BREAK_THE_GLASS_INAPPROPRIATE_ATTEMPT" OR e1mid == "FAILEDLOGIN" OR e1mid == "LOGIN_BLOCKED" OR e1mid == "WPSEC_LOGIN_FAIL"
    | summarize security_total = count()`,
};

export const SecurityCompliance = () => {
  const [site, setSite] = useState<string | null>(null);
  const f = (q: string) => withSiteFilter(q, site, "epic");

  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      <Text style={{ fontSize: 13, opacity: 0.6, marginBottom: -8 }}>
        Security & Compliance — break-the-glass access audit, failed login analysis, after-hours access detection, and HIPAA-relevant security events.
      </Text>
      <SiteFilter value={site} onChange={setSite} />

      {/* KPI Row */}
      <Flex gap={12} flexWrap="wrap">
        <KpiCard query={f(securityQueries.breakTheGlassCount)} label="Break-the-Glass Events" field="total" format="number" icon="🔓" />
        <KpiCard query={f(securityQueries.failedLoginCount)} label="Failed Logins" field="total" format="number" thresholds={{ green: 50, amber: 150 }} invertThresholds icon="🚫" />
        <KpiCard query={f(queries.epicLoginSuccessRate)} label="Login Success Rate" field="success_rate" format="percent" thresholds={{ green: 95, amber: 85 }} icon="🔐" />
        <KpiCard query={f(queries.afterHoursBtgCount)} label="After-Hours BTG" field="btg_after_hours" format="number" thresholds={{ green: 10, amber: 30 }} invertThresholds icon="🌙" />
        <KpiCard query={f(queries.activeWorkstationCount)} label="Active Workstations" field="active_ws" format="number" icon="🖥️" />
        <KpiCard query={f(queries.authFailedLoginCount)} label="Auth Failures" field="total" format="number" thresholds={{ green: 50, amber: 150 }} invertThresholds icon="⛔" />
      </Flex>

      {/* Security Events Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <Flex alignItems="center">
          <TitleBar>
            <TitleBar.Title>Security Events</TitleBar.Title>
            <TitleBar.Subtitle>Break-the-glass, failed logins, blocked accounts over time</TitleBar.Subtitle>
          </TitleBar>
          <SectionHealth query={f(securityQueries.totalSecurityEventCount)} field="security_total" green={100} amber={300} invert description="Total security events (BTG + failed logins + blocked accounts) in the current timeframe. High absolute counts indicate active security incidents regardless of overall login success rate." />
        </Flex>
        <TsChart query={f(securityQueries.securityEventsOverTime)} />
        <Flex gap={16} style={{ marginTop: 16 }}>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Break-the-Glass by User</Text>
            <BarChart query={f(securityQueries.breakTheGlassByUser)} />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Failed Logins by Hour</Text>
            <BarChart query={f(securityQueries.failedLoginsByHour)} />
          </div>
        </Flex>
        <div style={{ marginTop: 16 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Security Events by Site</Text>
          <BarChart query={f(securityQueries.securityBySite)} />
        </div>
      </Surface>

      {/* Login Analysis Section (merged from Login Failure Analysis + Auth Trends) */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <Flex alignItems="center">
          <TitleBar>
            <TitleBar.Title>Login Analysis</TitleBar.Title>
            <TitleBar.Subtitle>Login success vs failure trends, error breakdown, and authentication context</TitleBar.Subtitle>
          </TitleBar>
          <SectionHealth query={f(queries.authLoginSuccessRate)} field="success_rate" green={95} amber={85} description="BCA_LOGIN_SUCCESS vs FAILEDLOGIN ratio from Epic SIEM audit logs. Monitors the core authentication layer — degrades during LDAP outages, password policy changes, or targeted credential attacks." />
        </Flex>
        <div style={{ marginTop: 12 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Login Success vs Failure</Text>
          <TsChart query={f(queries.loginSuccessVsFailure)} />
        </div>
        <Flex gap={16} style={{ marginTop: 16 }}>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Login Error Type</Text>
            <BarChart query={f(queries.loginErrorTypeBreakdown)} />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Client Type</Text>
            <PieChart query={f(queries.loginClientTypeDistribution)} />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Login Context</Text>
            <BarChart query={f(queries.loginContextDistribution)} />
          </div>
        </Flex>
      </Surface>

      {/* After-Hours & Audit Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <Flex alignItems="center">
          <TitleBar>
            <TitleBar.Title>After-Hours Audit</TitleBar.Title>
            <TitleBar.Subtitle>Off-hours access monitoring and full security event log</TitleBar.Subtitle>
          </TitleBar>
          <SectionHealth query={f(queries.btgTotalCount)} field="btg_total" green={200} amber={400} invert description="Total Break-the-Glass (BTG) events in the current timeframe. BTG allows emergency chart access bypassing normal authorization. Elevated counts may indicate snooping, insider threats, or an actual mass-casualty event requiring emergency access." />
        </Flex>
        <Flex gap={16} style={{ marginTop: 12 }}>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>After-Hours Access (10PM–6AM)</Text>
            <EventTable query={f(securityQueries.afterHoursAccess)} />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Recent Security Events</Text>
            <EventTable query={f(securityQueries.recentSecurityEvents)} />
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

const EventTable = ({ query }: { query: string }) => {
  const { data, isLoading } = useDql({ query });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <div style={{ padding: 20, opacity: 0.5 }}>No events found in this timeframe</div>;
  const keys = Object.keys(records[0]).filter(k => k !== "timestamp");
  return (
    <div style={{ maxHeight: 350, overflow: "auto", fontSize: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={TH}>Time</th>
            {keys.map(k => <th key={k} style={TH}>{k}</th>)}
          </tr>
        </thead>
        <tbody>
          {records.map((r: any, i: number) => (
            <tr key={i}>
              <td style={TD}>{new Date(r.timestamp).toLocaleTimeString()}</td>
              {keys.map(k => (
                <td key={k} style={{
                  ...TD,
                  color: isSecurityEvent(r[k]) ? "#dc3545" : undefined,
                }}>{r[k] ?? "—"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

function isSecurityEvent(val: any): boolean {
  if (typeof val !== "string") return false;
  return val.includes("BREAK_THE_GLASS") || val === "FAILEDLOGIN" || val === "LOGIN_BLOCKED" || val.includes("WPSEC");
}

const TH: React.CSSProperties = { padding: "6px 8px", textAlign: "left", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", fontWeight: 600 };
const TD: React.CSSProperties = { padding: "4px 8px", borderBottom: "1px solid var(--dt-colors-border-neutral-default)" };
