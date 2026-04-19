import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { EPIC_FILTER } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { SiteFilter } from "../components/SiteFilter";
import { toTimeseries, toDonutData, toBarData } from "../utils/chartHelpers";
import { withSiteFilter } from "../utils/queryHelpers";
import { SectionHealth } from "../components/SectionHealth";

// ── MyChart e1mid values ──────────────────────────────────────────
const MYCHART_E1MIDS = `e1mid == "MYCHART_LOGIN" OR e1mid == "MYCHART_MSG_SEND" OR e1mid == "MYCHART_MSG_READ" OR e1mid == "MYCHART_APPT_SCHEDULE" OR e1mid == "MYCHART_RESULT_VIEW" OR e1mid == "MYCHART_PROXY_ACCESS" OR e1mid == "MYCHART_RX_REFILL"`;

const MYCHART_BASE = `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter ${MYCHART_E1MIDS}`;

// ── MyChart-specific DQL queries ──────────────────────────────────

const myChartQueries = {
  totalPortalEvents: `${MYCHART_BASE}
    | summarize total = count()`,

  uniquePatients: `${MYCHART_BASE}
    | parse content, "LD '<UserLoginID>' LD:user_id '<'"
    | filter isNotNull(user_id)
    | summarize unique_patients = countDistinct(user_id)`,

  loginSuccessRate: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "MYCHART_LOGIN" OR e1mid == "FAILEDLOGIN" OR e1mid == "LOGIN_BLOCKED" OR e1mid == "WPSEC_LOGIN_FAIL"
    | summarize
        successes = countIf(e1mid == "MYCHART_LOGIN"),
        total = count()
    | fieldsAdd success_rate = if(total > 0, toDouble(successes) / toDouble(total) * 100.0, else: 0.0)`,

  portalActivityOverTime: `${MYCHART_BASE}
    | fieldsAdd action_type = if(e1mid == "MYCHART_LOGIN", "Login",
        else: if(e1mid == "MYCHART_MSG_SEND" OR e1mid == "MYCHART_MSG_READ", "Messaging",
        else: if(e1mid == "MYCHART_APPT_SCHEDULE", "Scheduling",
        else: if(e1mid == "MYCHART_RESULT_VIEW", "Results",
        else: if(e1mid == "MYCHART_PROXY_ACCESS", "Proxy Access",
        else: if(e1mid == "MYCHART_RX_REFILL", "Rx Refill",
        else: "Other"))))))
    | makeTimeseries events = count(), by: { action_type }, interval: 5m`,

  actionDistribution: `${MYCHART_BASE}
    | fieldsAdd action_type = if(e1mid == "MYCHART_LOGIN", "Login",
        else: if(e1mid == "MYCHART_MSG_SEND", "Send Message",
        else: if(e1mid == "MYCHART_MSG_READ", "Read Message",
        else: if(e1mid == "MYCHART_APPT_SCHEDULE", "Schedule Appt",
        else: if(e1mid == "MYCHART_RESULT_VIEW", "View Results",
        else: if(e1mid == "MYCHART_PROXY_ACCESS", "Proxy Access",
        else: if(e1mid == "MYCHART_RX_REFILL", "Rx Refill",
        else: "Other")))))))
    | summarize cnt = count(), by: { action_type }
    | sort cnt desc`,

  portalBySite: `${MYCHART_BASE}
    | summarize events = count(), by: { site = healthcare.site }
    | sort events desc`,

  loginVolumeOverTime: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter e1mid == "MYCHART_LOGIN" OR e1mid == "FAILEDLOGIN" OR e1mid == "LOGIN_BLOCKED" OR e1mid == "WPSEC_LOGIN_FAIL"
    | fieldsAdd status = if(e1mid == "MYCHART_LOGIN", "success", else: "failure")
    | makeTimeseries logins = count(), by: { status }, interval: 5m`,

  messagingActivity: `${MYCHART_BASE}
    | filter e1mid == "MYCHART_MSG_SEND" OR e1mid == "MYCHART_MSG_READ"
    | fieldsAdd direction = if(e1mid == "MYCHART_MSG_SEND", "Sent", else: "Read")
    | makeTimeseries messages = count(), by: { direction }, interval: 5m`,

  recentPortalEvents: `${MYCHART_BASE}
    | parse content, "LD '<UserLoginID>' LD:user_id '<'"
    | fieldsAdd action_type = if(e1mid == "MYCHART_LOGIN", "Login",
        else: if(e1mid == "MYCHART_MSG_SEND", "Send Message",
        else: if(e1mid == "MYCHART_MSG_READ", "Read Message",
        else: if(e1mid == "MYCHART_APPT_SCHEDULE", "Schedule Appt",
        else: if(e1mid == "MYCHART_RESULT_VIEW", "View Results",
        else: if(e1mid == "MYCHART_PROXY_ACCESS", "Proxy Access",
        else: if(e1mid == "MYCHART_RX_REFILL", "Rx Refill",
        else: "Other")))))))
    | fields timestamp, action_type, user_id, healthcare.site
    | sort timestamp desc
    | limit 50`,
};

export const MyChartPortal = () => {
  const [site, setSite] = useState<string | null>(null);
  const f = (q: string) => withSiteFilter(q, site, "epic");

  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      <Text style={{ fontSize: 13, opacity: 0.6, marginBottom: -8 }}>
        MyChart Patient Portal — login activity, messaging, appointment scheduling, results viewing, proxy access, and prescription refill tracking.
      </Text>
      <SiteFilter value={site} onChange={setSite} />

      {/* KPI Row */}
      <Flex gap={12} flexWrap="wrap">
        <KpiCard query={f(myChartQueries.totalPortalEvents)} label="Portal Events" field="total" format="number" icon="📱" />
        <KpiCard query={f(myChartQueries.uniquePatients)} label="Unique Patients" field="unique_patients" format="number" icon="👤" />
        <KpiCard query={f(myChartQueries.loginSuccessRate)} label="Portal Login Rate" field="success_rate" format="percent" thresholds={{ green: 95, amber: 80 }} icon="🔐" />
      </Flex>

      {/* Portal Activity Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <Flex alignItems="center">
          <TitleBar>
            <TitleBar.Title>Portal Activity</TitleBar.Title>
            <TitleBar.Subtitle>All MyChart actions — login, messaging, scheduling, results, refills</TitleBar.Subtitle>
          </TitleBar>
          <SectionHealth query={f(myChartQueries.loginSuccessRate)} field="success_rate" green={95} amber={80} />
        </Flex>
        <Flex gap={16} style={{ marginTop: 12 }}>
          <div style={{ flex: 2 }}>
            <TsChart query={f(myChartQueries.portalActivityOverTime)} />
          </div>
          <div style={{ flex: 1 }}>
            <DonutChartWrap query={f(myChartQueries.actionDistribution)} />
          </div>
        </Flex>
        <Flex gap={16} style={{ marginTop: 16 }}>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Login Volume (Success vs Failure)</Text>
            <TsChart query={f(myChartQueries.loginVolumeOverTime)} />
          </div>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Usage by Site</Text>
            <BarChart query={f(myChartQueries.portalBySite)} />
          </div>
        </Flex>
      </Surface>

      {/* Messaging Section */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar>
          <TitleBar.Title>Patient Messaging Activity</TitleBar.Title>
          <TitleBar.Subtitle>Messages sent vs read over time</TitleBar.Subtitle>
        </TitleBar>
        <TsChart query={f(myChartQueries.messagingActivity)} />
      </Surface>

      {/* Recent Portal Events Table */}
      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar>
          <TitleBar.Title>Recent Portal Events</TitleBar.Title>
          <TitleBar.Subtitle>Live stream of MyChart patient portal activity</TitleBar.Subtitle>
        </TitleBar>
        <EventTable query={f(myChartQueries.recentPortalEvents)} />
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

const DonutChartWrap = ({ query }: { query: string }) => {
  const { data, isLoading } = useDql({ query });
  if (isLoading) return <ProgressCircle />;
  return <DonutChart data={toDonutData(data?.records ?? [])} />;
};

const EventTable = ({ query }: { query: string }) => {
  const { data, isLoading } = useDql({ query });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <div style={{ padding: 20, opacity: 0.5 }}>No MyChart events found in this timeframe</div>;

  return (
    <div style={{ maxHeight: 350, overflow: "auto", fontSize: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={TH}>Time</th>
            <th style={TH}>Action</th>
            <th style={TH}>Patient</th>
            <th style={TH}>Site</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r: any, i: number) => (
            <tr key={i}>
              <td style={TD}>{new Date(r.timestamp).toLocaleTimeString()}</td>
              <td style={{ ...TD, color: actionColor(r.action_type) }}>{r.action_type ?? "—"}</td>
              <td style={TD}>{r.user_id ?? "—"}</td>
              <td style={TD}>{r["healthcare.site"] ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

function actionColor(action: string): string {
  switch (action) {
    case "Login": return "#4f8cff";
    case "Send Message": return "#34d399";
    case "Read Message": return "#6ee7b7";
    case "Schedule Appt": return "#fbbf24";
    case "View Results": return "#a78bfa";
    case "Proxy Access": return "#f87171";
    case "Rx Refill": return "#fb923c";
    default: return "inherit";
  }
}

const TH: React.CSSProperties = { padding: "6px 8px", textAlign: "left", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", fontWeight: 600 };
const TD: React.CSSProperties = { padding: "4px 8px", borderBottom: "1px solid var(--dt-colors-border-neutral-default)" };
