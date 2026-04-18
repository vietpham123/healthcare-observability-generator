import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Heading, Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries, EPIC_FILTER, NETWORK_FILTER } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { SiteCard } from "../components/SiteCard";
import { computeHealthStatus, statusColor } from "../components/HealthBadge";
import { toTimeseries, toBarData } from "../utils/chartHelpers";

const SITES = [
  { code: "kcrmc-main", name: "KC Regional Medical Center", beds: 500, profile: "Level I Trauma" },
  { code: "tpk-clinic", name: "Topeka Specialty Clinic", beds: 50, profile: "Cardiology / Oncology" },
  { code: "wch-clinic", name: "Wichita Care Center", beds: 75, profile: "Urgent Care + Family Med" },
  { code: "lwr-clinic", name: "Lawrence Family Medicine", beds: 30, profile: "Primary Care + Pediatrics" },
];

export const SiteView = () => {
  const [selectedSite, setSelectedSite] = useState<string | null>(null);
  const siteHealth = useDql({ query: queries.siteHealthSummary });
  const netHealth = useDql({ query: queries.networkSiteHealth });
  const netDevices = useDql({ query: queries.networkDevicesBySite });

  const siteRecords = siteHealth.data?.records ?? [];
  const netRecords = netHealth.data?.records ?? [];
  const devRecords = netDevices.data?.records ?? [];

  const enrichedSites = SITES.map((s) => {
    const epicRec = siteRecords.find((r: any) => r.site === s.code);
    const netRec = netRecords.find((r: any) => r.site === s.code);
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

  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      <Heading level={3}>Hospital Sites</Heading>
      <Flex gap={16} flexWrap="wrap">
        {enrichedSites.map((site) => (
          <SiteCard key={site.code} name={site.name} code={site.code} events={site.events} users={site.users} loginRate={site.loginRate} avgCpu={site.avgCpu} devices={site.devices} onClick={() => setSelectedSite(site.code)} />
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
  const siteEpicQuery = `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${EPIC_FILTER}
    | filter healthcare.site == "${site.code}"
    | parse content, "LD '<E1Mid>' LD:e1mid '<'"
    | filter isNotNull(e1mid)
    | summarize cnt = count(), by: { e1mid }
    | sort cnt desc`;

  const siteNetLogsQuery = `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
    | filter ${NETWORK_FILTER}
    | filter healthcare.site == "${site.code}"
    | makeTimeseries events = count(), by: { vendor = network.device.vendor }, interval: 5m`;

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
        ].map((m) => (
          <Flex key={m.label} flexDirection="column" alignItems="center" style={{ background: "var(--dt-colors-surface-default)", borderRadius: 12, padding: 16, minWidth: 130, flex: 1 }}>
            <Text style={{ fontSize: 10, opacity: 0.5, textTransform: "uppercase" }}>{m.label}</Text>
            <Text style={{ fontSize: 28, fontWeight: 700, color: (m as any).color }}>{m.value}</Text>
          </Flex>
        ))}
      </Flex>

      <Flex gap={16}>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Epic Event Types</TitleBar.Title></TitleBar>
          <BarChart query={siteEpicQuery} />
        </Surface>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Network Events</TitleBar.Title></TitleBar>
          <TsChart query={siteNetLogsQuery} />
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
