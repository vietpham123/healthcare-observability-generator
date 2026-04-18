import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, DonutChart, CategoricalBarChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries, SITE_ALIAS as SITE_ALIAS_Q } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { CampusMap } from "../components/CampusMap";
import { SiteFilter } from "../components/SiteFilter";
import { toTimeseries, toDonutData, toBarData } from "../utils/chartHelpers";
import { withSiteFilter } from "../utils/queryHelpers";

// Re-use the shared alias map
const SITE_ALIAS = SITE_ALIAS_Q;

const SITE_META: Record<string, { name: string; label: string; x: number; y: number }> = {
  "kcrmc-main": { name: "KC Regional Medical Center", label: "KC Main Campus", x: 450, y: 130 },
  "oak-clinic": { name: "Oakley Rural Health", label: "Oakley Clinic", x: 100, y: 130 },
  "wel-clinic": { name: "Wellington Care Center", label: "Wellington Clinic", x: 280, y: 260 },
  "bel-clinic": { name: "Belleville Family Medicine", label: "Belleville Clinic", x: 300, y: 60 },
};

function mergeSiteRecords(records: any[], aliasMap: Record<string, string>): any[] {
  const merged: Record<string, any> = {};
  for (const r of records) {
    const raw = r.site ?? "";
    const code = aliasMap[raw] ?? raw;
    if (!merged[code]) {
      merged[code] = { site: code, events: 0, logins: 0, login_ok: 0, users: 0 };
    }
    merged[code].events += Number(r.events) || 0;
    merged[code].logins += Number(r.logins) || 0;
    merged[code].login_ok += Number(r.login_ok) || 0;
    merged[code].users += Number(r.users) || 0;
  }
  return Object.values(merged);
}

function mergeDeviceRecords(records: any[], aliasMap: Record<string, string>): any[] {
  const merged: Record<string, any> = {};
  for (const r of records) {
    const raw = r.site ?? "";
    const code = aliasMap[raw] ?? raw;
    if (!merged[code]) merged[code] = { site: code, devices: 0 };
    merged[code].devices += Number(r.devices) || 0;
  }
  return Object.values(merged);
}

export const Overview = () => {
  const [site, setSite] = useState<string | null>(null);
  const fe = (q: string) => withSiteFilter(q, site, "epic");
  const siteHealth = useDql({ query: queries.siteHealthSummary });
  const netDevices = useDql({ query: queries.networkDevicesBySite });
  const netflowBySite = useDql({ query: queries.netflowBySite });
  const siteRecords = mergeSiteRecords(siteHealth.data?.records ?? [], SITE_ALIAS);
  const devRecords = mergeDeviceRecords(netDevices.data?.records ?? [], SITE_ALIAS);

  const campusSites = siteRecords.map((r: any) => {
    const code = r.site ?? "";
    const meta = SITE_META[code] ?? { name: code, label: code, x: 300, y: 160 };
    const logins = Number(r.logins) || 0;
    const loginOk = Number(r.login_ok) || 0;
    const devRec = devRecords.find((d: any) => d.site === code);
    return {
      code, name: meta.name, label: meta.label, x: meta.x, y: meta.y,
      events: Number(r.events) || 0,
      loginRate: logins > 0 ? (loginOk / logins) * 100 : 100,
      users: Number(r.users) || 0,
      devices: Number(devRec?.devices) || 0,
    };
  });

  // Build real flow data from netflow query — hub-and-spoke from KC to satellites
  const flowRecords = netflowBySite.data?.records ?? [];
  const flowBySiteMap: Record<string, number> = {};
  for (const r of flowRecords) {
    const raw = String(r.site ?? "");
    const code = SITE_ALIAS[raw] ?? raw;
    flowBySiteMap[code] = (flowBySiteMap[code] || 0) + (Number(r.flows) || 0);
  }
  const campusFlows = Object.entries(flowBySiteMap)
    .filter(([code]) => code !== "kcrmc-main" && code !== "")
    .map(([code, flows]) => ({
      from: "kcrmc-main",
      to: code,
      volume: flows,
      label: `${flows} flows`,
    }));

  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      <Text style={{ fontSize: 13, opacity: 0.6, marginBottom: -8 }}>
        System-wide view of Kansas City Regional Medical Center and satellite clinics — login health, device status, event distribution, and cross-system correlation.
      </Text>
      <SiteFilter value={site} onChange={setSite} />
      <Flex gap={12} flexWrap="wrap">
        <KpiCard query={fe(queries.epicLoginSuccessRate)} label="Epic Login Success" field="success_rate" format="percent" thresholds={{ green: 90, amber: 70 }} icon="🔐" />
        <KpiCard query={fe(queries.hl7DeliveryRate)} label="HL7 Delivery" field="delivery_rate" format="percent" thresholds={{ green: 95, amber: 80 }} icon="📡" />
        <KpiCard query={fe(queries.fhirHealthRate)} label="FHIR API Health" field="success_rate" format="percent" thresholds={{ green: 95, amber: 85 }} icon="🔗" />
        <KpiCard query={fe(queries.etlSuccessRate)} label="ETL Success" field="success_rate" format="percent" thresholds={{ green: 95, amber: 80 }} icon="⚙️" />
        <KpiCard query={fe(queries.avgDeviceCpu)} label="Avg Device CPU" field="avg_cpu" format="percent" thresholds={{ green: 80, amber: 60 }} icon="💻" />
        <KpiCard query={fe(queries.activeUsers)} label="Active Users" field="unique_users" format="number" icon="👥" />
      </Flex>

      <Flex gap={16}>
        <Surface style={{ flex: 2, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Campus Health Map</TitleBar.Title><TitleBar.Subtitle>Kansas Healthcare Network</TitleBar.Subtitle></TitleBar>
          {siteHealth.isLoading
            ? <Flex alignItems="center" justifyContent="center" style={{ height: 300 }}><ProgressCircle /></Flex>
            : <CampusMap sites={campusSites} flows={campusFlows} />}
        </Surface>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Epic Event Distribution</TitleBar.Title></TitleBar>
          <EventDistChart site={site} />
        </Surface>
      </Flex>

      <Flex gap={16}>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>System Activity</TitleBar.Title><TitleBar.Subtitle>Epic vs Network event volume</TitleBar.Subtitle></TitleBar>
          <ActivityTimelineChart site={site} />
        </Surface>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Events by Site & Pipeline</TitleBar.Title></TitleBar>
          <EventsBySiteChart site={site} />
        </Surface>
      </Flex>

      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Epic ↔ Network Correlation</TitleBar.Title><TitleBar.Subtitle>Overlay of Epic workflow events with network infrastructure events</TitleBar.Subtitle></TitleBar>
        <CorrelationChart site={site} />
      </Surface>
    </Flex>
  );
};

const EventDistChart = ({ site }: { site: string | null }) => {
  const { data, isLoading } = useDql({ query: withSiteFilter(queries.epicEventDistribution, site, "epic") });
  if (isLoading) return <ProgressCircle />;
  return <DonutChart data={toDonutData(data?.records ?? [])} />;
};

const ActivityTimelineChart = ({ site }: { site: string | null }) => {
  const result = useDql({ query: withSiteFilter(queries.systemActivityTimeline, site, "epic") });
  if (result.isLoading) return <ProgressCircle />;
  return <TimeseriesChart data={toTimeseries(result.data)} gapPolicy="connect" />;
};

const EventsBySiteChart = ({ site }: { site: string | null }) => {
  const { data, isLoading } = useDql({ query: withSiteFilter(queries.eventsBySite, site, "epic") });
  if (isLoading) return <ProgressCircle />;
  return <CategoricalBarChart data={toBarData(data?.records ?? [])} />;
};

const CorrelationChart = ({ site }: { site: string | null }) => {
  const result = useDql({ query: withSiteFilter(queries.epicNetworkCorrelation, site, "epic") });
  if (result.isLoading) return <ProgressCircle />;
  return <TimeseriesChart data={toTimeseries(result.data)} variant="area" gapPolicy="connect" />;
};
