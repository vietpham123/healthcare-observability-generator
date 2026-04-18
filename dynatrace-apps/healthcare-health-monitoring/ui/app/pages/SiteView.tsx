import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Heading, Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries, EPIC_FILTER, NETWORK_FILTER, NETFLOW_FILTER, epicSiteFilter, netflowSiteFilter, SITE_ALIAS as SITE_ALIAS_Q } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { SiteCard } from "../components/SiteCard";
import { computeHealthStatus, statusColor } from "../components/HealthBadge";
import { toTimeseries, toBarData, toDonutData } from "../utils/chartHelpers";

// Re-use the shared alias map
const SITE_ALIAS = SITE_ALIAS_Q;

function mergeRecords(records: any[], aliasMap: Record<string, string>, siteField: string, numericFields: string[]): any[] {
  const merged: Record<string, any> = {};
  for (const r of records) {
    const raw = r[siteField] ?? "";
    const code = aliasMap[raw] ?? raw;
    if (!merged[code]) {
      merged[code] = { [siteField]: code };
      for (const f of numericFields) merged[code][f] = 0;
    }
    for (const f of numericFields) merged[code][f] += Number(r[f]) || 0;
  }
  return Object.values(merged);
}

const SITES = [
  { code: "kcrmc-main", name: "KC Regional Medical Center", beds: 500, profile: "Level I Trauma Center" },
  { code: "oak-clinic", name: "Oakley Rural Health", beds: 25, profile: "Rural Health & Specialty Outreach" },
  { code: "wel-clinic", name: "Wellington Care Center", beds: 40, profile: "Urgent Care + Family Medicine" },
  { code: "bel-clinic", name: "Belleville Family Medicine", beds: 20, profile: "Primary Care + Pediatrics" },
];

export const SiteView = () => {
  const [selectedSite, setSelectedSite] = useState<string | null>(null);
  const siteHealth = useDql({ query: queries.siteHealthSummary });
  const netHealth = useDql({ query: queries.networkSiteHealth });
  const netDevices = useDql({ query: queries.networkDevicesBySite });

  const siteRecords = mergeRecords(siteHealth.data?.records ?? [], SITE_ALIAS, "site", ["events", "logins", "login_ok", "users"]);
  const netRecords = netHealth.data?.records ?? []; // timeseries — alias handled by site dimension
  const devRecords = mergeRecords(netDevices.data?.records ?? [], SITE_ALIAS, "site", ["devices"]);

  const enrichedSites = SITES.map((s) => {
    const epicRec = siteRecords.find((r: any) => r.site === s.code);
    const netRec = netRecords.find((r: any) => (SITE_ALIAS[r.site] ?? r.site) === s.code);
    const devRec = devRecords.find((r: any) => r.site === s.code);
    const events = Number(epicRec?.events) || 0;
    const users = Number(epicRec?.users) || 0;
    const logins = Number(epicRec?.logins) || 0;
    const loginOk = Number(epicRec?.login_ok) || 0;
    const loginRate = logins > 0 ? (loginOk / logins) * 100 : 100;
    const avgCpu = Number(netRec?.avg_cpu) || 0;
    const devices = Number(devRec?.devices) || 0;
    return { ...s, events, users, loginRate, avgCpu, devices };
  });

  if (siteHealth.isLoading) return <Flex justifyContent="center" style={{ padding: 60 }}><ProgressCircle /></Flex>;

  if (selectedSite) {
    const site = enrichedSites.find((s) => s.code === selectedSite);
    if (!site) return null;
    return <SiteDrillDown site={site} onBack={() => setSelectedSite(null)} />;
  }

  const mainSite = enrichedSites.find((s) => s.code === "kcrmc-main");
  const satellites = enrichedSites.filter((s) => s.code !== "kcrmc-main");

  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      <Text style={{ fontSize: 13, opacity: 0.6, marginBottom: -8 }}>
        Per-site breakdown of all hospital locations — KC Regional Medical Center (main campus) and three satellite clinics across Kansas. Click a site card to drill down into its Epic events and network activity.
      </Text>

      {/* Main campus — full width on top */}
      {mainSite && (
        <Flex>
          <div style={{ width: "100%" }}>
            <SiteCard key={mainSite.code} name={mainSite.name} code={mainSite.code} events={mainSite.events} users={mainSite.users} loginRate={mainSite.loginRate} avgCpu={mainSite.avgCpu} devices={mainSite.devices} onClick={() => setSelectedSite(mainSite.code)} />
          </div>
        </Flex>
      )}

      {/* Satellite clinics — three across */}
      <Flex gap={16} flexWrap="wrap">
        {satellites.map((site) => (
          <div key={site.code} style={{ flex: "1 1 280px", minWidth: 280 }}>
            <SiteCard name={site.name} code={site.code} events={site.events} users={site.users} loginRate={site.loginRate} avgCpu={site.avgCpu} devices={site.devices} onClick={() => setSelectedSite(site.code)} />
          </div>
        ))}
      </Flex>

      <Flex gap={16}>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>CPU by Site</TitleBar.Title></TitleBar>
          <TsChart query={queries.deviceCpuBySite} />
        </Surface>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Events by Site & Pipeline</TitleBar.Title></TitleBar>
          <BarChart query={queries.eventsBySite} />
        </Surface>
      </Flex>
    </Flex>
  );
};

interface DrillSite { code: string; name: string; profile: string; beds: number; events: number; users: number; loginRate: number; avgCpu: number; devices: number; }

const SiteDrillDown = ({ site, onBack }: { site: DrillSite; onBack: () => void }) => {
  const sf = epicSiteFilter(site.code);
  const nf = netflowSiteFilter(site.code);

  const siteEpicQuery = `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter ${sf}
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter isNotNull(e1mid)
    | summarize cnt = count(), by: { e1mid }
    | sort cnt desc`;

  const siteNetLogsQuery = `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | filter ${sf}
    | makeTimeseries events = count(), by: { vendor = network.device.vendor }, interval: 5m`;

  // Tier 1 queries
  const hl7Result = useDql({ query: queries.siteHL7Volume(sf) });
  const errorResult = useDql({ query: queries.siteErrorRate(sf) });
  const flowResult = useDql({ query: queries.siteNetflowVolume(nf) });
  const catResult = useDql({ query: queries.siteTopEventTypes(sf) });
  const flowTlResult = useDql({ query: queries.siteNetflowTimeline(nf) });

  const hl7Count = Number(hl7Result.data?.records?.[0]?.total) || 0;
  const errorRate = Number(errorResult.data?.records?.[0]?.error_rate) || 0;
  const flowCount = Number(flowResult.data?.records?.[0]?.total) || 0;

  const status = computeHealthStatus(site.loginRate, 90, 70);

  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      <Flex alignItems="center" gap={12}>
        <button onClick={onBack} style={{ background: "var(--dt-colors-surface-default)", border: "1px solid var(--dt-colors-border-neutral-default)", borderRadius: 6, padding: "6px 14px", cursor: "pointer", fontSize: 13, color: "var(--dt-colors-text-primary-default)" }}>← Back</button>
        <Heading level={3}>{site.name}</Heading>
        <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: statusColor(status) }} />
      </Flex>
      <Text style={{ opacity: 0.6 }}>{site.profile} · {site.beds} beds · {site.code}</Text>

      <Flex gap={12} flexWrap="wrap">
        {[
          { label: "Events", value: site.events },
          { label: "Users", value: site.users },
          { label: "Login Rate", value: `${site.loginRate.toFixed(0)}%`, color: statusColor(status) },
          { label: "Devices", value: site.devices },
          { label: "Avg CPU", value: `${site.avgCpu.toFixed(1)}%` },
          { label: "HL7 Msgs", value: hl7Count },
          { label: "Error Rate", value: `${errorRate.toFixed(1)}%`, color: errorRate > 10 ? "#dc3545" : errorRate > 5 ? "#f5a623" : "#2ab06f" },
          { label: "NetFlows", value: flowCount },
        ].map((m) => (
          <Flex key={m.label} flexDirection="column" alignItems="center" style={{ background: "var(--dt-colors-surface-default)", borderRadius: 12, padding: 16, minWidth: 110, flex: 1 }}>
            <Text style={{ fontSize: 10, opacity: 0.5, textTransform: "uppercase" }}>{m.label}</Text>
            <Text style={{ fontSize: 24, fontWeight: 700, color: (m as any).color }}>{m.value}</Text>
          </Flex>
        ))}
      </Flex>

      <Flex gap={16}>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Event Categories</TitleBar.Title><TitleBar.Subtitle>HL7, FHIR, Clinical, Login, ETL breakdown</TitleBar.Subtitle></TitleBar>
          <BarChart query={queries.siteTopEventTypes(sf)} />
        </Surface>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Epic Audit Events (E1Mid)</TitleBar.Title></TitleBar>
          <BarChart query={siteEpicQuery} />
        </Surface>
      </Flex>

      <Flex gap={16}>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Network Events by Vendor</TitleBar.Title></TitleBar>
          <TsChart query={siteNetLogsQuery} />
        </Surface>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>NetFlow Traffic</TitleBar.Title><TitleBar.Subtitle>Flow records over time for this site</TitleBar.Subtitle></TitleBar>
          <TsChart query={queries.siteNetflowTimeline(nf)} />
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
