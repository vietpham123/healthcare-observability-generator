import React from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, CategoricalBarChart, DonutChart, HoneycombChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { toTimeseries, toDonutData, toBarData } from "../utils/chartHelpers";

export const NetworkHealth = () => (
  <Flex flexDirection="column" gap={16} padding={16}>
    <Flex gap={12} flexWrap="wrap">
      <KpiCard query={queries.networkDeviceUpRatio} label="Devices Up" field="up_ratio" format="percent" thresholds={{ green: 95, amber: 80 }} icon="📡" />
      <KpiCard query={queries.avgDeviceCpu} label="Avg CPU" field="avg_cpu" format="percent" thresholds={{ green: 80, amber: 60 }} icon="💻" />
      <KpiCard query={queries.avgDeviceMem} label="Avg Memory" field="avg_mem" format="percent" thresholds={{ green: 85, amber: 70 }} icon="🧠" />
      <KpiCard query={queries.totalNetworkEvents} label="Network Events" field="total" format="number" icon="📋" />
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

    <Flex gap={16}>
      <Surface style={{ flex: 2, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Network Log Timeline</TitleBar.Title></TitleBar>
        <TsChart query={queries.networkLogTimeline} />
      </Surface>
      <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Vendor Distribution</TitleBar.Title></TitleBar>
        <VendorDonut />
      </Surface>
    </Flex>

    <Surface style={{ padding: 16, borderRadius: 12 }}>
      <TitleBar><TitleBar.Title>Device Inventory</TitleBar.Title></TitleBar>
      <DeviceTable />
    </Surface>
  </Flex>
);

const TsChart = ({ query }: { query: string }) => {
  const result = useDql({ query });
  if (result.isLoading) return <ProgressCircle />;
  return <TimeseriesChart data={toTimeseries(result.data)} />;
};

const VendorDonut = () => {
  const { data, isLoading } = useDql({ query: queries.networkVendorDistribution });
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

const DeviceTable = () => {
  const { data, isLoading } = useDql({ query: queries.networkDeviceList });
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

const TH: React.CSSProperties = { padding: "6px 8px", textAlign: "left", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", fontWeight: 600 };
const TD: React.CSSProperties = { padding: "4px 8px", borderBottom: "1px solid var(--dt-colors-border-neutral-default)" };
