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
import { toTimeseries, toTimeseriesWithThresholds, toDonutData, toBarData, type ThresholdLine } from "../utils/chartHelpers";
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
      <KpiCard query={fn(queries.networkDeviceUpRatio)} label="Devices Up" field="up_ratio" format="percent" thresholds={{ green: 100, amber: 95 }} icon="📡" />
      <KpiCard query={fn(queries.avgDeviceCpu)} label="Avg CPU" field="avg_cpu" format="percent" thresholds={{ green: 25, amber: 40 }} invertThresholds icon="💻" />
      <KpiCard query={fn(queries.avgDeviceMem)} label="Avg Memory" field="avg_mem" format="percent" thresholds={{ green: 45, amber: 60 }} invertThresholds icon="🧠" />
      <KpiCard query={fn(queries.totalNetworkEvents)} label="Network Events" field="total" format="number" icon="📋" />
      <KpiCard query={ff(queries.netflowTotalFlows)} label="NetFlow Records" field="total" format="number" icon="🌐" />
      <KpiCard query={fn(queries.portSecurityViolations)} label="Port Violations" field="violation_count" format="number" thresholds={{ green: 0, amber: 1 }} invertThresholds icon="🔒" />
    </Flex>

    {/* Device Fleet Health Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <Flex alignItems="center">
        <TitleBar><TitleBar.Title>Device Fleet Health</TitleBar.Title><TitleBar.Subtitle>CPU, memory, and traffic across all network devices</TitleBar.Subtitle></TitleBar>
        <SectionHealth query={fn(queries.peakDeviceCpu)} field="peak_cpu" green={50} amber={70} invert description="Peak CPU utilization across any single network device over the last 15 minutes. Even one device spiking above 70% signals potential overload from ransomware lateral movement, DDoS, or cascading failure after a core switch loss." />
      </Flex>
      <DeviceHoneycomb site={site} />
      <Flex gap={16} style={{ marginTop: 16 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>CPU by Device</Text>
          <TsChart query={fn(queries.deviceCpuOverTime)} thresholds={[{ label: "Warning 50%", value: 50 }, { label: "Critical 70%", value: 70 }]} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Memory by Device</Text>
          <TsChart query={fn(queries.deviceMemOverTime)} thresholds={[{ label: "Warning 65%", value: 65 }, { label: "Critical 80%", value: 80 }]} />
        </div>
      </Flex>
      <Flex gap={16} style={{ marginTop: 16 }}>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Traffic In</Text>
          <TsChart query={fn(queries.trafficInOverTime)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Traffic Out</Text>
          <TsChart query={fn(queries.trafficOutOverTime)} />
        </div>
      </Flex>
    </Surface>

    {/* NetFlow Analysis Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>NetFlow Traffic Analysis</TitleBar.Title><TitleBar.Subtitle>Per-flow records showing source/destination IPs, protocols, and traffic volume across all sites</TitleBar.Subtitle></TitleBar>
      <SectionHealth query={fn(queries.portSecurityViolations)} field="violation_count" green={0} amber={3} invert description="Port security violations detected across the network. Any violation may indicate unauthorized device connections, MAC flooding, or lateral movement attempts." />
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

    {/* Network Logs & Vendor Section */}
    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <Flex alignItems="center">
        <TitleBar><TitleBar.Title>Network Logs & Inventory</TitleBar.Title><TitleBar.Subtitle>Log timeline, vendor distribution, and device inventory</TitleBar.Subtitle></TitleBar>
        <SectionHealth query={fn(queries.networkDeviceUpRatio)} field="up_ratio" green={100} amber={95} description="Percentage of network devices that reported logs within the last 5 minutes. Any device going silent may indicate a power failure, link down, or device compromise. Healthy = all devices reporting." />
      </Flex>
      <Flex gap={16} style={{ marginTop: 12 }}>
        <div style={{ flex: 2 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Network Log Timeline</Text>
          <TsChart query={fn(queries.networkLogTimeline)} />
        </div>
        <div style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Vendor Distribution</Text>
          <VendorDonut site={site} />
        </div>
      </Flex>
      <div style={{ marginTop: 16 }}>
        <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, display: "block" }}>Device Inventory</Text>
        <DeviceTable site={site} />
      </div>
    </Surface>
  </Flex>
  );
};

const TsChart = ({ query, thresholds }: { query: string; thresholds?: ThresholdLine[] }) => {
  const result = useDql({ query });
  if (result.isLoading) return <ProgressCircle />;
  const series = thresholds ? toTimeseriesWithThresholds(result.data, thresholds) : toTimeseries(result.data);
  return <TimeseriesChart data={series} gapPolicy="connect" />;
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

const DeviceHoneycomb = ({ site }: { site: string | null }) => {
  const { data, isLoading } = useDql({ query: withSiteFilter(queries.deviceHealthGrid, site, "network") });
  if (isLoading) return <Flex justifyContent="center" style={{ height: 200 }}><ProgressCircle /></Flex>;
  const records = data?.records ?? [];
  if (records.length === 0) return <Text>No device data</Text>;

  const ROLE_ICONS: Record<string, string> = {
    core: "🔷", distribution: "🔶", access: "🟢", firewall: "🛡️", wireless: "📶",
  };

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, padding: "12px 0" }}>
      {records.map((r: any, i: number) => {
        const isDown = r.status === "down";
        const bg = isDown ? "var(--dt-colors-charts-categorical-color-11, #dc3545)" : "var(--dt-colors-charts-status-success, #2ab050)";
        const label = String(r.device ?? "").replace(/^kcrmc-/, "");
        const icon = ROLE_ICONS[r.role] ?? "📡";
        return (
          <div
            key={i}
            title={`${r.device}\n${r.vendor} • ${r.role} • ${r.site}\nStatus: ${isDown ? "DOWN" : "UP"}\nLast seen: ${Number(r.minutes_ago).toFixed(1)}m ago`}
            style={{
              width: 100, height: 70,
              background: bg, borderRadius: 8,
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              color: "#fff", fontSize: 11, fontWeight: 600,
              opacity: isDown ? 1 : 0.85,
              border: isDown ? "2px solid #ff4d4f" : "1px solid rgba(255,255,255,0.15)",
              cursor: "default",
              position: "relative",
            }}
          >
            <span style={{ fontSize: 16 }}>{isDown ? "🔴" : icon}</span>
            <span style={{ marginTop: 2, textAlign: "center", lineHeight: 1.2, maxWidth: 90, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</span>
            <span style={{ fontSize: 9, opacity: 0.8 }}>{isDown ? "DOWN" : "UP"}</span>
          </div>
        );
      })}
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
