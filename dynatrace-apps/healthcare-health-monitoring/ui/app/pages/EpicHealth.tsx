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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Flex flexDirection="column" gap={12} style={{
      background: "var(--dt-colors-surface-default)",
      borderRadius: 12,
      padding: 20,
    }}>
      <Heading level={2}>{title}</Heading>
      {children}
    </Flex>
  );
}

export const EpicHealth = () => {
  const loginTimeline = useDql({ query: queries.loginVolumeOverTime });
  const loginBySite = useDql({ query: queries.loginBySite });
  const orderVolume = useDql({ query: queries.orderVolumeOverTime });
  const deptActivity = useDql({ query: queries.departmentActivity });
  const clinicalTypes = useDql({ query: queries.clinicalEventTypes });
  const myChartSessions = useDql({ query: queries.myChartSessionsOverTime });
  const myChartDevices = useDql({ query: queries.myChartDeviceTypes });

  return (
    <Flex flexDirection="column" gap={24} padding={24}>
      <Heading level={1}>Epic EHR System Health</Heading>
      <Text>Clinical system availability, authentication health, workflow throughput, and patient portal performance.</Text>

      {/* KPI Row */}
      <Flex gap={16} flexWrap="wrap">
        <KpiCard
          query={queries.epicLoginSuccessRate}
          label="Login Success Rate"
          field="success_rate"
          format="percent"
          thresholds={{ green: 99, amber: 95 }}
        />
        <KpiCard query={queries.activeUsers} label="Active Users" field="unique_users" />
        <KpiCard
          query={queries.fhirErrorRate}
          label="FHIR Error Rate"
          field="error_rate"
          format="percent"
        />
        <KpiCard
          query={queries.etlSuccessRate}
          label="ETL Success Rate"
          field="success_rate"
          format="percent"
          thresholds={{ green: 99, amber: 90 }}
        />
      </Flex>

      {/* Login & Auth Health */}
      <Section title="Login & Authentication Health">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <Heading level={3}>Login Volume Over Time</Heading>
            <div style={{ height: 280 }}>
              {loginTimeline.isLoading ? <ProgressCircle /> :
                loginTimeline.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(loginTimeline.data.records, loginTimeline.data.types)}
                    variant="stacked-bar"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Logins by Site</Heading>
            {loginBySite.isLoading ? <ProgressCircle /> :
              loginBySite.data?.records?.length ? (
                <DataTable data={loginBySite.data.records} columns={[
                  { accessor: "site", header: "Site" },
                  { accessor: "logins", header: "Count" },
                ]} />
              ) : <Text>No data</Text>}
          </Flex>
        </Flex>
      </Section>

      {/* Clinical Workflow Throughput */}
      <Section title="Clinical Workflow Throughput">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <Heading level={3}>Order Volume Over Time</Heading>
            <div style={{ height: 280 }}>
              {orderVolume.isLoading ? <ProgressCircle /> :
                orderVolume.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(orderVolume.data.records, orderVolume.data.types)}
                    variant="stacked-bar"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Event Types</Heading>
            <div style={{ height: 280 }}>
              {clinicalTypes.isLoading ? <ProgressCircle /> :
                clinicalTypes.data?.records?.length ? (
                  <PieChart
                    data={clinicalTypes.data.records.map((r: any) => ({
                      name: r.clinical_type || "Unknown",
                      value: r.cnt || 0,
                    }))}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
        <Heading level={3}>Department Activity</Heading>
        {deptActivity.isLoading ? <ProgressCircle /> :
          deptActivity.data?.records?.length ? (
            <DataTable data={deptActivity.data.records} columns={[
              { accessor: "DEPARTMENT", header: "Department" },
              { accessor: "events", header: "Events" },
            ]} />
          ) : <Text>No data</Text>}
      </Section>

      {/* MyChart Portal Health */}
      <Section title="MyChart Portal Health">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <Heading level={3}>Portal Sessions Over Time</Heading>
            <div style={{ height: 280 }}>
              {myChartSessions.isLoading ? <ProgressCircle /> :
                myChartSessions.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(myChartSessions.data.records, myChartSessions.data.types)}
                    variant="area"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Device Types</Heading>
            <div style={{ height: 280 }}>
              {myChartDevices.isLoading ? <ProgressCircle /> :
                myChartDevices.data?.records?.length ? (
                  <PieChart
                    data={myChartDevices.data.records.map((r: any) => ({
                      name: r.device_type || "Unknown",
                      value: r.cnt || 0,
                    }))}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
      </Section>
    </Flex>
  );
};
