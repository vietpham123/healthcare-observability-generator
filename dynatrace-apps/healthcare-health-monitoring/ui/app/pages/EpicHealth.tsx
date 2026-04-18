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

export const EpicHealth = () => {
  const loginVolume = useDql({ query: queries.loginVolumeOverTime });
  const loginTrend = useDql({ query: queries.loginSuccessRateTrend });
  const loginBySite = useDql({ query: queries.loginBySite });
  const orderVolume = useDql({ query: queries.orderVolumeOverTime });
  const deptActivity = useDql({ query: queries.departmentActivity });
  const clinicalTypes = useDql({ query: queries.clinicalEventTypes });
  const myChartSessions = useDql({ query: queries.myChartSessionsOverTime });
  const deviceTypes = useDql({ query: queries.myChartDeviceTypes });

  return (
    <Flex flexDirection="column" gap={24} padding={24}>
      <Heading level={1}>Epic EHR Health</Heading>
      <Text>
        Login authentication, clinical workflow throughput, and patient portal activity
        across Kansas City Regional Medical Center.
      </Text>

      {/* KPI Row */}
      <Flex gap={16} flexWrap="wrap">
        <KpiCard
          query={queries.epicLoginSuccessRate}
          label="Login Success Rate"
          field="success_rate"
          format="percent"
          thresholds={{ green: 99, amber: 95 }}
        />
        <KpiCard
          query={queries.activeUsers}
          label="Active Users"
          field="unique_users"
        />
      </Flex>

      {/* Login & Auth */}
      <Section title="Authentication & Access" subtitle="Login volume and success rates across sites">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <Heading level={3}>Login Volume Over Time</Heading>
            <div style={{ height: 280 }}>
              {loginVolume.isLoading ? <ProgressCircle /> :
                loginVolume.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(loginVolume.data.records, loginVolume.data.types)}
                    variant="bar"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Logins by Site</Heading>
            <div style={{ height: 280 }}>
              {loginBySite.isLoading ? <ProgressCircle /> :
                loginBySite.data?.records?.length ? (
                  <PieChart
                    data={{ slices: loginBySite.data.records.map((r: any) => ({ category: r.site || "Unknown", value: r.logins || 0 })) }}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
        <Heading level={3}>Login Success Rate Trend</Heading>
        <div style={{ height: 250 }}>
          {loginTrend.isLoading ? <ProgressCircle /> :
            loginTrend.data?.records ? (
              <TimeseriesChart
                data={convertToTimeseries(loginTrend.data.records, loginTrend.data.types)}
                variant="line"
                gapPolicy="connect"
              />
            ) : <Text>No data</Text>}
        </div>
      </Section>

      {/* Clinical Workflow */}
      <Section title="Clinical Workflow" subtitle="Order volume, department activity, and clinical event types">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <Heading level={3}>Order Volume Over Time</Heading>
            <div style={{ height: 280 }}>
              {orderVolume.isLoading ? <ProgressCircle /> :
                orderVolume.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(orderVolume.data.records, orderVolume.data.types)}
                    variant="bar"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Clinical Event Types</Heading>
            <div style={{ height: 280 }}>
              {clinicalTypes.isLoading ? <ProgressCircle /> :
                clinicalTypes.data?.records?.length ? (
                  <PieChart
                    data={{ slices: clinicalTypes.data.records.map((r: any) => ({ category: r.clinical_type || "Unknown", value: r.cnt || 0 })) }}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
        <Heading level={3}>Department Activity (Top 15)</Heading>
        {deptActivity.isLoading ? <ProgressCircle /> :
          deptActivity.data?.records?.length ? (
            <DataTable data={deptActivity.data.records} columns={[
              { id: "DEPARTMENT", accessor: "DEPARTMENT", header: "Department" },
              { id: "events", accessor: "events", header: "Events" },
            ]} />
          ) : <Text>No department data</Text>}
      </Section>

      {/* MyChart Portal */}
      <Section title="MyChart Patient Portal" subtitle="Portal session activity and device usage">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <Heading level={3}>Portal Sessions Over Time</Heading>
            <div style={{ height: 280 }}>
              {myChartSessions.isLoading ? <ProgressCircle /> :
                myChartSessions.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(myChartSessions.data.records, myChartSessions.data.types)}
                    variant="bar"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Device Types</Heading>
            <div style={{ height: 280 }}>
              {deviceTypes.isLoading ? <ProgressCircle /> :
                deviceTypes.data?.records?.length ? (
                  <PieChart
                    data={{ slices: deviceTypes.data.records.map((r: any) => ({ category: r.device_type || "Unknown", value: r.cnt || 0 })) }}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
      </Section>
    </Flex>
  );
};
