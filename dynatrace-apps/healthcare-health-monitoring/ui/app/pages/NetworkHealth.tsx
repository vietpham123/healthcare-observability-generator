import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Heading, Text } from "@dynatrace/strato-components/typography";
import {
  TimeseriesChart,
  PieChart,
  convertToTimeseries,
} from "@dynatrace/strato-components-preview/charts";
import { DataTable } from "@dynatrace/strato-components-preview/tables";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <Flex flexDirection="column" gap={12} style={{
      background: "var(--dt-colors-surface-default)",
      borderRadius: 12,
      padding: 20,
    }}>
      <Heading level={2}>{title}</Heading>
      {subtitle && <Text style={{ opacity: 0.7 }}>{subtitle}</Text>}
      {children}
    </Flex>
  );
}

export const NetworkHealth = () => {
  const cpuTimeline = useDql({ query: queries.deviceCpuOverTime });
  const memTimeline = useDql({ query: queries.deviceMemOverTime });
  const trafficIn = useDql({ query: queries.trafficInOverTime });
  const trafficOut = useDql({ query: queries.trafficOutOverTime });
  const deviceSnap = useDql({ query: queries.deviceSnapshot });
  const deviceList = useDql({ query: queries.networkDeviceList });
  const logTimeline = useDql({ query: queries.networkLogTimeline });
  const vendorDist = useDql({ query: queries.networkVendorDistribution });
  const siteDist = useDql({ query: queries.networkSiteDistribution });
  const cpuBySite = useDql({ query: queries.deviceCpuBySite });

  return (
    <Flex flexDirection="column" gap={24} padding={24}>
      <Heading level={1}>Network Infrastructure Health</Heading>
      <Text>
        Device health metrics, traffic volume, and log event monitoring across all KCRMC sites.
        Metrics sourced from healthcare.network.* MINT ingest; logs from OpenPipeline-tagged network events.
      </Text>

      {/* KPI Row */}
      <Flex gap={16} flexWrap="wrap">
        <KpiCard
          query={queries.networkDeviceUpRatio}
          label="Devices Online"
          field="up_ratio"
          format="percent"
          thresholds={{ green: 100, amber: 90 }}
        />
        <KpiCard
          query={queries.avgDeviceCpu}
          label="Avg CPU"
          field="avg_cpu"
          format="percent"
        />
      </Flex>

      {/* Device Health (Metrics) */}
      <Section title="Device Health Metrics" subtitle="CPU, memory utilization per device from healthcare.network.* metrics">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>CPU Utilization</Heading>
            <div style={{ height: 250 }}>
              {cpuTimeline.isLoading ? <ProgressCircle /> :
                cpuTimeline.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(cpuTimeline.data.records, cpuTimeline.data.types)}
                    variant="line"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Memory Utilization</Heading>
            <div style={{ height: 250 }}>
              {memTimeline.isLoading ? <ProgressCircle /> :
                memTimeline.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(memTimeline.data.records, memTimeline.data.types)}
                    variant="line"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>

        <Heading level={3}>CPU by Site</Heading>
        <div style={{ height: 250 }}>
          {cpuBySite.isLoading ? <ProgressCircle /> :
            cpuBySite.data?.records ? (
              <TimeseriesChart
                data={convertToTimeseries(cpuBySite.data.records, cpuBySite.data.types)}
                variant="line"
                gapPolicy="connect"
              />
            ) : <Text>No data</Text>}
        </div>

        <Heading level={3}>Device Snapshot</Heading>
        {deviceSnap.isLoading ? <ProgressCircle /> :
          deviceSnap.data?.records?.length ? (
            <DataTable data={deviceSnap.data.records} columns={[
              { id: "device", accessor: "device", header: "Device" },
              { id: "vendor", accessor: "vendor", header: "Vendor" },
              { id: "site", accessor: "site", header: "Site" },
              { id: "avg_cpu", accessor: "avg_cpu", header: "CPU %" },
              { id: "avg_mem", accessor: "avg_mem", header: "Memory %" },
            ]} />
          ) : <Text>No data</Text>}
      </Section>

      {/* Traffic Volume */}
      <Section title="Interface Traffic" subtitle="Bytes in/out per device">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Traffic In (bytes)</Heading>
            <div style={{ height: 250 }}>
              {trafficIn.isLoading ? <ProgressCircle /> :
                trafficIn.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(trafficIn.data.records, trafficIn.data.types)}
                    variant="area"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Traffic Out (bytes)</Heading>
            <div style={{ height: 250 }}>
              {trafficOut.isLoading ? <ProgressCircle /> :
                trafficOut.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(trafficOut.data.records, trafficOut.data.types)}
                    variant="area"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
      </Section>

      {/* Log Events */}
      <Section title="Network Log Events" subtitle="Log volume and device inventory from OpenPipeline-tagged events">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <Heading level={3}>Log Event Timeline</Heading>
            <div style={{ height: 250 }}>
              {logTimeline.isLoading ? <ProgressCircle /> :
                logTimeline.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(logTimeline.data.records, logTimeline.data.types)}
                    variant="bar"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Vendor Distribution</Heading>
            <div style={{ height: 250 }}>
              {vendorDist.isLoading ? <ProgressCircle /> :
                vendorDist.data?.records?.length ? (
                  <PieChart
                    data={{ slices: vendorDist.data.records.map((r: any) => ({ category: r.vendor || "Unknown", value: r.cnt || 0 })) }}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>

        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Site Distribution</Heading>
            <div style={{ height: 250 }}>
              {siteDist.isLoading ? <ProgressCircle /> :
                siteDist.data?.records?.length ? (
                  <PieChart
                    data={{ slices: siteDist.data.records.map((r: any) => ({ category: r.site || "Unknown", value: r.cnt || 0 })) }}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <Heading level={3}>Device Inventory</Heading>
            {deviceList.isLoading ? <ProgressCircle /> :
              deviceList.data?.records?.length ? (
                <DataTable data={deviceList.data.records} columns={[
                  { id: "hostname", accessor: "hostname", header: "Hostname" },
                  { id: "vendor", accessor: "vendor", header: "Vendor" },
                  { id: "role", accessor: "role", header: "Role" },
                  { id: "model", accessor: "model", header: "Model" },
                  { id: "site", accessor: "site", header: "Site" },
                  { id: "events", accessor: "events", header: "Events" },
                ]} />
              ) : <Text>No devices</Text>}
          </Flex>
        </Flex>
      </Section>
    </Flex>
  );
};
