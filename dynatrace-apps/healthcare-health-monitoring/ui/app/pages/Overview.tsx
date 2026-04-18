import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Heading, Text } from "@dynatrace/strato-components/typography";
import {
  PieChart,
  TimeseriesChart,
  convertToTimeseries,
} from "@dynatrace/strato-components-preview/charts";
import { DataTable } from "@dynatrace/strato-components-preview/tables";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";

export const Overview = () => {
  const activityTimeline = useDql({ query: queries.systemActivityTimeline });
  const epicDist = useDql({ query: queries.epicEventDistribution });
  const networkDist = useDql({ query: queries.networkEventDistribution });
  const deviceSnapshot = useDql({ query: queries.snmpDeviceSnapshot });

  return (
    <Flex flexDirection="column" gap={24} padding={24}>
      <Heading level={1}>Healthcare Environment Health</Heading>
      <Text>
        Kansas City Regional Medical Center — real-time operational health
        combining Epic EHR telemetry and network infrastructure monitoring across
        4 sites.
      </Text>

      {/* KPI Row */}
      <Flex gap={16} flexWrap="wrap">
        <KpiCard
          query={queries.epicLoginSuccessRate}
          label="Epic Login Success"
          field="success_rate"
          format="percent"
          thresholds={{ green: 99, amber: 95 }}
        />
        <KpiCard
          query={queries.hl7AckRate}
          label="HL7 ACK Rate"
          field="ack_rate"
          format="percent"
          thresholds={{ green: 99.5, amber: 98 }}
        />
        <KpiCard
          query={queries.fhirHealthRate}
          label="FHIR API Health"
          field="success_rate"
          format="percent"
          thresholds={{ green: 99, amber: 97 }}
        />
        <KpiCard
          query={queries.networkDeviceUpRatio}
          label="Network Uptime"
          field="up_ratio"
          format="percent"
          thresholds={{ green: 100, amber: 90 }}
        />
        <KpiCard
          query={queries.avgDeviceCpu}
          label="Avg Device CPU"
          field="avg_cpu"
          format="percent"
        />
        <KpiCard
          query={queries.activeProblems}
          label="Active Problems"
          field="problem_count"
        />
      </Flex>

      {/* System Activity Timeline */}
      <Flex flexDirection="column" style={{
        background: "var(--dt-colors-surface-default)",
        borderRadius: 12,
        padding: 20,
      }}>
        <Heading level={2}>System Activity Timeline</Heading>
        <Text style={{ opacity: 0.7, marginBottom: 12 }}>
          Epic EHR events vs. network infrastructure events — 5-minute intervals
        </Text>
        <div style={{ height: 300 }}>
          {activityTimeline.isLoading ? (
            <ProgressCircle />
          ) : activityTimeline.data?.records ? (
            <TimeseriesChart
              data={convertToTimeseries(
                activityTimeline.data.records,
                activityTimeline.data.types
              )}
              variant="area"
              gapPolicy="connect"
            />
          ) : (
            <Text>No data available</Text>
          )}
        </div>
      </Flex>

      {/* Distribution Row */}
      <Flex gap={16}>
        <Flex flexDirection="column" style={{
          flex: 1,
          background: "var(--dt-colors-surface-default)",
          borderRadius: 12,
          padding: 20,
        }}>
          <Heading level={3}>Epic Event Types</Heading>
          <div style={{ height: 280 }}>
            {epicDist.isLoading ? (
              <ProgressCircle />
            ) : epicDist.data?.records?.length ? (
              <PieChart
                data={epicDist.data.records.map((r: any) => ({
                  name: r.event_category || "Unknown",
                  value: r.cnt || 0,
                }))}
              />
            ) : (
              <Text>No data</Text>
            )}
          </div>
        </Flex>
        <Flex flexDirection="column" style={{
          flex: 1,
          background: "var(--dt-colors-surface-default)",
          borderRadius: 12,
          padding: 20,
        }}>
          <Heading level={3}>Network Event Sources</Heading>
          <div style={{ height: 280 }}>
            {networkDist.isLoading ? (
              <ProgressCircle />
            ) : networkDist.data?.records?.length ? (
              <PieChart
                data={networkDist.data.records.map((r: any) => ({
                  name: r["log.source"] || "Unknown",
                  value: r.cnt || 0,
                }))}
              />
            ) : (
              <Text>No data</Text>
            )}
          </div>
        </Flex>
      </Flex>

      {/* SNMP Device Health Table */}
      <Flex flexDirection="column" style={{
        background: "var(--dt-colors-surface-default)",
        borderRadius: 12,
        padding: 20,
      }}>
        <Heading level={2}>Network Device Health</Heading>
        {deviceSnapshot.isLoading ? (
          <ProgressCircle />
        ) : deviceSnapshot.data?.records?.length ? (
          <DataTable data={deviceSnapshot.data.records} columns={[
            { accessor: "hostname", header: "Hostname" },
            { accessor: "vendor", header: "Vendor" },
            { accessor: "site", header: "Site" },
            { accessor: "cpu", header: "CPU %" },
            { accessor: "memory", header: "Memory %" },
            { accessor: "sessions", header: "Sessions" },
            { accessor: "interfaces_up", header: "Intf Up" },
            { accessor: "interfaces_total", header: "Intf Total" },
          ]} />
        ) : (
          <Text>No device data</Text>
        )}
      </Flex>
    </Flex>
  );
};
