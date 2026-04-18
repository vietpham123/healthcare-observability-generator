import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart, HoneycombChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { SiteFilter } from "../components/SiteFilter";
import { toTimeseries, toDonutData, toBarData } from "../utils/chartHelpers";
import { withSiteFilter } from "../utils/queryHelpers";

export const NetworkHealth = () => {
  const [site, setSite] = useState<string | null>(null);
  const fn = (q: string) => withSiteFilter(q, site, "network");
  const ff = (q: string) => withSiteFilter(q, site, "netflow");

  return (
  <Flex flexDirection="column" gap={16} padding={16}>
    <Text style={{ fontSize: 13, opacity: 0.6, marginBottom: -8 }}>
      Network infrastructure monitoring — device fleet health (CPU, memory, traffic), vendor distribution, and NetFlow traffic analysis including protocol breakdown, top destination ports, and geographic traffic sources.
    </Text>
    <SiteFilter value={site} onChange={setSite} />
    <Flex gap={12} flexWrap="wrap">
      <KpiCard query={fn(queries.networkDeviceUpRatio)} label="Devices Up" field="up_ratio" format="percent" thresholds={{ green: 95, amber: 80 }} icon="📡" />
      <KpiCard query={fn(queries.avgDeviceCpu)} label="Avg CPU" field="avg_cpu" format="percent" thresholds={{ green: 80, amber: 60 }} icon="💻" />
      <KpiCard query={fn(queries.avgDeviceMem)} label="Avg Memory" field="avg_mem" format="percent" thresholds={{ green: 85, amber: 70 }} icon="🧠" />
      <KpiCard query={fn(queries.totalNetworkEvents)} label="Network Events" field="total" format="number" icon="📋" />
      <KpiCard query={ff(queries.netflowTotalFlows)} label="NetFlow Records" field="total" format="number" icon="🌐" />
    </Flex>

    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>Device Fleet — CPU Utilization</TitleBar.Title><TitleBar.Subtitle>Honeycomb view of all network devices by average CPU load</TitleBar.Subtitle></TitleBar>
      <DeviceHoneycomb />
    </Surface>

    <Flex gap={16}>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>CPU by Device</TitleBar.Title></TitleBar>
        <TsChart query={queries.deviceCpuOverTime} />
      </Surface>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Memory by Device</TitleBar.Title></TitleBar>
        <TsChart query={queries.deviceMemOverTime} />
      </Surface>
    </Flex>

    <Flex gap={16}>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Traffic In</TitleBar.Title></TitleBar>
        <TsChart query={queries.trafficInOverTime} />
      </Surface>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Traffic Out</TitleBar.Title></TitleBar>
        <TsChart query={queries.trafficOutOverTime} />
      </Surface>
    </Flex>

    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>NetFlow Traffic Analysis</TitleBar.Title><TitleBar.Subtitle>Per-flow records showing source/destination IPs, protocols, and traffic volume across all sites</TitleBar.Subtitle></TitleBar>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 2 }}><TsChart query={ff(queries.netflowTimeline)} /></div>
        <div style={{ flex: 1 }}><ProtocolDonut site={site} /></div>
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Top Destination Ports</Text>
          <BarChart query={ff(queries.netflowTopDstPorts)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Flows by Site</Text>
          <BarChart query={ff(queries.netflowBySite)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>External Source Countries</Text>
          <BarChart query={ff(queries.netflowTopSrcCountries)} />
        </div>
      </Flex>
      <FlowTable site={site} />
    </Surface>

    <Flex gap={16}>
      <Surface style={{ flex: 2, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Network Log Timeline</TitleBar.Title></TitleBar>
        <TsChart query={fn(queries.networkLogTimeline)} />
      </Surface>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Vendor Distribution</TitleBar.Title></TitleBar>
        <VendorDonut site={site} />
      </Surface>
    </Flex>

    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>Device Inventory</TitleBar.Title></TitleBar>
      <DeviceTable site={site} />
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

const VendorDonut = ({ site }: { site: string | null }) => {
  const { data, isLoading } = useDql({ query: withSiteFilter(queries.networkVendorDistribution, site, "network") });
  if (isLoading) return <ProgressCircle />;
  return <DonutChart data={toDonutData(data?.records ?? [])} />;
};

const ProtocolDonut = ({ site }: { site: string | null }) => {
  const { data, isLoading } = useDql({ query: withSiteFilter(queries.netflowProtocolDist, site, "netflow") });
  if (isLoading) return <ProgressCircle />;
  return <DonutChart data={toDonutData(data?.records ?? [])} />;
};

const DeviceHoneycomb = () => {
  const { data, isLoading } = useDql({ query: queries.deviceSnapshot });
  if (isLoading) return <Flex justifyContent="center" style={{ height: 200 }}><ProgressCircle /></Flex>;
  const records = data?.records ?? [];
  if (records.length === 0) return <Text>No device data</Text>;
  const cpuValues = records.map((r: any) => Number(r.avg_cpu) || 0);
  return (
    <div style={{ height: 280 }}>
      <HoneycombChart data={cpuValues} />
    </div>
  );
};

const DeviceTable = ({ site }: { site: string | null }) => {
  const { data, isLoading } = useDql({ query: withSiteFilter(queries.networkDeviceList, site, "network") });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  return (
    <div style={{ maxHeight: 400, overflow: "auto", fontSize: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr><th style={TH}>Hostname</th><th style={TH}>Vendor</th><th style={TH}>Role</th><th style={TH}>Site</th><th style={TH}>Events</th><th style={TH}>Last Seen</th></tr></thead>
        <tbody>
          {records.map((r: any, i: number) => (
            <tr key={i}>
              <td style={TD}>{r.hostname}</td><td style={TD}>{r.vendor}</td><td style={TD}>{r.role}</td>
              <td style={TD}>{r.site}</td><td style={TD}>{r.events}</td>
              <td style={TD}>{r.last_seen ? new Date(r.last_seen).toLocaleString() : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const FlowTable = ({ site }: { site: string | null }) => {
  const { data, isLoading } = useDql({ query: withSiteFilter(queries.netflowRecentFlows, site, "netflow") });
  if (isLoading) return <ProgressCircle />;
  const records = data?.records ?? [];
  if (records.length === 0) return <Text style={{ padding: 16, opacity: 0.5 }}>No flow records yet — data may take a few minutes to appear</Text>;
  return (
    <div style={{ maxHeight: 300, overflow: "auto", fontSize: 12, marginTop: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr><th style={TH}>Time</th><th style={TH}>Src IP</th><th style={TH}>Dst IP</th><th style={TH}>Port</th><th style={TH}>Proto</th><th style={TH}>Bytes</th><th style={TH}>Device</th><th style={TH}>Site</th></tr></thead>
        <tbody>
          {records.map((r: any, i: number) => (
            <tr key={i}>
              <td style={TD}>{new Date(r.timestamp).toLocaleTimeString()}</td>
              <td style={TD}>{r["network.flow.src_ip"]}</td>
              <td style={TD}>{r["network.flow.dst_ip"]}</td>
              <td style={TD}>{r["network.flow.dst_port"]}</td>
              <td style={TD}>{r["network.flow.protocol"]}</td>
              <td style={TD}>{Number(r["network.flow.bytes"]).toLocaleString()}</td>
              <td style={TD}>{r["network.device.hostname"]}</td>
              <td style={TD}>{r["network.device.site"]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const TH: React.CSSProperties = { padding: "6px 8px", textAlign: "left", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", fontWeight: 600 };
const TD: React.CSSProperties = { padding: "4px 8px", borderBottom: "1px solid var(--dt-colors-border-neutral-default)" };
