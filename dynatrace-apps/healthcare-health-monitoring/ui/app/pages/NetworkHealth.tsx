import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Heading, Text } from "@dynatrace/strato-components/typography";
import {
  TimeseriesChart,
  PieChart,
  convertToTimeseries,
} from "@dynatrace/strato-components-preview/charts";
import { DataTable, convertToColumns } from "@dynatrace/strato-components-preview/tables";
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
  const cpuTimeline = useDql({ query: queries.snmpCpuOverTime });
  const memTimeline = useDql({ query: queries.snmpMemOverTime });
  const sessionsTimeline = useDql({ query: queries.snmpSessionsOverTime });
  const deviceSnapshot = useDql({ query: queries.snmpDeviceSnapshot });
  const ifTrafficIn = useDql({ query: queries.snmpIfTrafficIn });
  const ifTrafficOut = useDql({ query: queries.snmpIfTrafficOut });
  const interfaceChanges = useDql({ query: queries.interfaceStateChanges });
  const linkFlaps = useDql({ query: queries.linkFlapDetection });
  const routingTimeline = useDql({ query: queries.routingEventsTimeline });
  const routingNeighbors = useDql({ query: queries.routingNeighborTable });
  const connRate = useDql({ query: queries.connectionRateOverTime });
  const netflowVolume = useDql({ query: queries.netflowVolumeOverTime });
  const netflowProto = useDql({ query: queries.netflowProtocolDist });

  return (
    <Flex flexDirection="column" gap={24} padding={24}>
      <Heading level={1}>Network Infrastructure Health</Heading>
      <Text>
        SNMP device health, interface utilization, routing protocol stability,
        firewall connections, and traffic volume across all KCRMC sites.
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

      {/* Device Health (SNMP) */}
      <Section title="Device Health (SNMP)" subtitle="CPU, memory, and session utilization per device">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>CPU Over Time</Heading>
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
            <Heading level={3}>Memory Over Time</Heading>
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
        <Heading level={3}>Sessions Over Time</Heading>
        <div style={{ height: 250 }}>
          {sessionsTimeline.isLoading ? <ProgressCircle /> :
            sessionsTimeline.data?.records ? (
              <TimeseriesChart
                data={convertToTimeseries(sessionsTimeline.data.records, sessionsTimeline.data.types)}
                variant="line"
                gapPolicy="connect"
              />
            ) : <Text>No data</Text>}
        </div>
        <Heading level={3}>Device Snapshot</Heading>
        {deviceSnapshot.isLoading ? <ProgressCircle /> :
          deviceSnapshot.data?.records?.length ? (
            <DataTable data={deviceSnapshot.data.records} columns={convertToColumns(deviceSnapshot.data.types)} />
          ) : <Text>No data</Text>}
      </Section>

      {/* Interface Health */}
      <Section title="Interface Health" subtitle="Traffic volume and state changes">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Traffic In (bytes)</Heading>
            <div style={{ height: 250 }}>
              {ifTrafficIn.isLoading ? <ProgressCircle /> :
                ifTrafficIn.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(ifTrafficIn.data.records, ifTrafficIn.data.types)}
                    variant="area"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Traffic Out (bytes)</Heading>
            <div style={{ height: 250 }}>
              {ifTrafficOut.isLoading ? <ProgressCircle /> :
                ifTrafficOut.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(ifTrafficOut.data.records, ifTrafficOut.data.types)}
                    variant="area"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
        <Heading level={3}>Interface State Changes</Heading>
        {interfaceChanges.isLoading ? <ProgressCircle /> :
          interfaceChanges.data?.records?.length ? (
            <DataTable data={interfaceChanges.data.records} columns={convertToColumns(interfaceChanges.data.types)} />
          ) : <Text>No recent state changes</Text>}
        {linkFlaps.data?.records?.length ? (
          <>
            <Heading level={3} style={{ color: "var(--dt-colors-charts-status-critical)" }}>
              Link Flap Alerts
            </Heading>
            <DataTable data={linkFlaps.data.records} columns={convertToColumns(linkFlaps.data.types)} />
          </>
        ) : null}
      </Section>

      {/* Routing Protocol Health */}
      <Section title="Routing Protocol Health" subtitle="OSPF/BGP neighbor stability">
        <div style={{ height: 250 }}>
          {routingTimeline.isLoading ? <ProgressCircle /> :
            routingTimeline.data?.records ? (
              <TimeseriesChart
                data={convertToTimeseries(routingTimeline.data.records, routingTimeline.data.types)}
                variant="bar"
                gapPolicy="connect"
              />
            ) : <Text>No data</Text>}
        </div>
        <Heading level={3}>Routing Neighbors</Heading>
        {routingNeighbors.isLoading ? <ProgressCircle /> :
          routingNeighbors.data?.records?.length ? (
            <DataTable data={routingNeighbors.data.records} columns={convertToColumns(routingNeighbors.data.types)} />
          ) : <Text>No routing events</Text>}
      </Section>

      {/* Firewall Connection Health */}
      <Section title="Firewall Connection Health" subtitle="Connection build/teardown rates">
        <div style={{ height: 250 }}>
          {connRate.isLoading ? <ProgressCircle /> :
            connRate.data?.records ? (
              <TimeseriesChart
                data={convertToTimeseries(connRate.data.records, connRate.data.types)}
                variant="bar"
                gapPolicy="connect"
              />
            ) : <Text>No data</Text>}
        </div>
      </Section>

      {/* Network Traffic (NetFlow) */}
      <Section title="Network Traffic Volume" subtitle="NetFlow bytes and packets over time">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <div style={{ height: 250 }}>
              {netflowVolume.isLoading ? <ProgressCircle /> :
                netflowVolume.data?.records?.length ? (
                  <DataTable data={netflowVolume.data.records} columns={convertToColumns(netflowVolume.data.types)} />
                ) : <Text>No NetFlow data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Protocol Distribution</Heading>
            <div style={{ height: 250 }}>
              {netflowProto.isLoading ? <ProgressCircle /> :
                netflowProto.data?.records?.length ? (
                  <PieChart
                    data={{
                      slices: netflowProto.data.records.map((r: any) => ({
                        category: String(r["network.flow.protocol"] ?? "Unknown"),
                        value: Number(r.total_bytes ?? 0),
                      }))
                    }}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
      </Section>
    </Flex>
  );
};
