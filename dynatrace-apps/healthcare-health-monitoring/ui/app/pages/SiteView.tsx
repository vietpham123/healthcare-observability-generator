import React, { useState } from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Heading, Text } from "@dynatrace/strato-components/typography";
import {
  TimeseriesChart,
  convertToTimeseries,
} from "@dynatrace/strato-components-preview/charts";
import { DataTable } from "@dynatrace/strato-components-preview/tables";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries, EPIC_FILTER } from "../queries";
import { SiteCard } from "../components/SiteCard";

const SITES = [
  { code: "kcrmc-main", name: "Kansas City — Main Campus", beds: 500, profile: "Level I Trauma" },
  { code: "tpk-clinic", name: "Topeka Specialty Clinic", beds: 0, profile: "Cardiology/Oncology" },
  { code: "wch-clinic", name: "Wichita Urgent Care", beds: 0, profile: "Urgent Care + Family Medicine" },
  { code: "lwr-clinic", name: "Lawrence Primary Care", beds: 0, profile: "Primary Care + Pediatrics" },
];

function SiteDetail({ siteCode, siteName }: { siteCode: string; siteName: string }) {
  const loginTimeline = useDql({
    query: `fetch logs, scanLimitGBytes: -1, samplingRatio: 1
      | filter ${EPIC_FILTER} AND healthcare.site == "${siteCode}"
      | filter isNotNull(Action)
      | makeTimeseries logins = count(), by: { Action }, interval: 5m`,
  });
  const siteCpu = useDql({
    query: `timeseries cpu = avg(healthcare.network.device.cpu.utilization), by: {device}, from: now()-2h
      | filter site == "${siteCode}"`,
  });
  const deviceSnap = useDql({
    query: `timeseries
        cpu = avg(healthcare.network.device.cpu.utilization),
        mem = avg(healthcare.network.device.memory.utilization),
        by: {device, site, vendor}, from: now()-15m
      | filter site == "${siteCode}"
      | fieldsAdd avg_cpu = arrayAvg(cpu), avg_mem = arrayAvg(mem)
      | fields device, vendor, avg_cpu, avg_mem`,
  });

  return (
    <Flex flexDirection="column" gap={16}>
      <Heading level={2}>{siteName}</Heading>
      <Text style={{ opacity: 0.6 }}>Site code: {siteCode}</Text>

      <Flex flexDirection="column" style={{
        background: "var(--dt-colors-surface-default)",
        borderRadius: 12,
        padding: 20,
      }}>
        <Heading level={3}>Login Activity</Heading>
        <div style={{ height: 280 }}>
          {loginTimeline.isLoading ? <ProgressCircle /> :
            loginTimeline.data?.records ? (
              <TimeseriesChart
                data={convertToTimeseries(loginTimeline.data.records, loginTimeline.data.types)}
                variant="bar"
                gapPolicy="connect"
              />
            ) : <Text>No data for this site</Text>}
        </div>
      </Flex>

      <Flex flexDirection="column" style={{
        background: "var(--dt-colors-surface-default)",
        borderRadius: 12,
        padding: 20,
      }}>
        <Heading level={3}>Device CPU Utilization</Heading>
        <div style={{ height: 280 }}>
          {siteCpu.isLoading ? <ProgressCircle /> :
            siteCpu.data?.records ? (
              <TimeseriesChart
                data={convertToTimeseries(siteCpu.data.records, siteCpu.data.types)}
                variant="line"
                gapPolicy="connect"
              />
            ) : <Text>No metric data for this site</Text>}
        </div>
      </Flex>

      <Flex flexDirection="column" style={{
        background: "var(--dt-colors-surface-default)",
        borderRadius: 12,
        padding: 20,
      }}>
        <Heading level={3}>Network Devices</Heading>
        {deviceSnap.isLoading ? <ProgressCircle /> :
          deviceSnap.data?.records?.length ? (
            <DataTable data={deviceSnap.data.records} columns={[
              { id: "device", accessor: "device", header: "Device" },
              { id: "vendor", accessor: "vendor", header: "Vendor" },
              { id: "avg_cpu", accessor: "avg_cpu", header: "CPU %" },
              { id: "avg_mem", accessor: "avg_mem", header: "Memory %" },
            ]} />
          ) : <Text>No devices at this site</Text>}
      </Flex>
    </Flex>
  );
}

export const SiteView = () => {
  const [selectedSite, setSelectedSite] = useState<string | null>(null);

  const epicBySite = useDql({ query: queries.epicEventsBySite });
  const networkBySite = useDql({ query: queries.networkHealthBySite });

  const epicMap: Record<string, { login_rate: number }> = {};
  if (epicBySite.data?.records) {
    for (const r of epicBySite.data.records as any[]) {
      epicMap[r.site] = { login_rate: r.login_rate ?? 100 };
    }
  }
  const networkMap: Record<string, { avg_cpu: number }> = {};
  if (networkBySite.data?.records) {
    for (const r of networkBySite.data.records as any[]) {
      networkMap[r.site] = { avg_cpu: r.avg_cpu ?? 0 };
    }
  }

  const selectedSiteInfo = SITES.find(s => s.code === selectedSite);

  return (
    <Flex flexDirection="column" gap={24} padding={24}>
      <Heading level={1}>Site View</Heading>
      <Text>
        Per-site health comparison across Kansas City Regional Medical Center network.
        Click a site card to drill down.
      </Text>

      <Flex gap={16} flexWrap="wrap">
        {SITES.map(site => {
          const epic = epicMap[site.code];
          const net = networkMap[site.code];
          return (
            <SiteCard
              key={site.code}
              name={site.name}
              code={site.code}
              epicHealth={epic?.login_rate ?? 100}
              networkHealth={net ? Math.max(0, 100 - net.avg_cpu) : 100}
              integrationHealth={85}
              activeProblems={0}
              onClick={() => setSelectedSite(selectedSite === site.code ? null : site.code)}
            />
          );
        })}
      </Flex>

      {selectedSiteInfo && (
        <SiteDetail
          siteCode={selectedSiteInfo.code}
          siteName={selectedSiteInfo.name}
        />
      )}
    </Flex>
  );
};
