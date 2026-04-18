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

export const IntegrationHealth = () => {
  const hl7Volume = useDql({ query: queries.hl7VolumeOverTime });
  const hl7Types = useDql({ query: queries.hl7MessageTypes });
  const hl7Errors = useDql({ query: queries.hl7Errors });
  const fhirRate = useDql({ query: queries.fhirRequestRateOverTime });
  const fhirStatus = useDql({ query: queries.fhirStatusDistribution });
  const fhirResponseTimes = useDql({ query: queries.fhirResponseTimePercentiles });
  const fhirSlow = useDql({ query: queries.fhirSlowRequests });
  const fhirClients = useDql({ query: queries.fhirClientUsage });
  const etlStatus = useDql({ query: queries.etlJobStatusOverTime });
  const etlDuration = useDql({ query: queries.etlJobDurationTrends });
  const etlFailed = useDql({ query: queries.etlFailedJobs });

  return (
    <Flex flexDirection="column" gap={24} padding={24}>
      <Heading level={1}>Integration Health</Heading>
      <Text>HL7v2 interfaces, FHIR API endpoints, and ETL batch pipelines connecting Epic to downstream systems.</Text>

      {/* KPI Row */}
      <Flex gap={16} flexWrap="wrap">
        <KpiCard
          query={queries.hl7AckRate}
          label="HL7 ACK Rate"
          field="ack_rate"
          format="percent"
          thresholds={{ green: 99.5, amber: 98 }}
        />
        <KpiCard
          query={queries.fhirHealthRate}
          label="FHIR Success Rate"
          field="success_rate"
          format="percent"
          thresholds={{ green: 99, amber: 97 }}
        />
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

      {/* HL7v2 Interface Health */}
      <Section title="HL7v2 Interface Health">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 2 }}>
            <Heading level={3}>Message Volume Over Time</Heading>
            <div style={{ height: 280 }}>
              {hl7Volume.isLoading ? <ProgressCircle /> :
                hl7Volume.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(hl7Volume.data.records, hl7Volume.data.types)}
                    variant="bar"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Message Types</Heading>
            <div style={{ height: 280 }}>
              {hl7Types.isLoading ? <ProgressCircle /> :
                hl7Types.data?.records?.length ? (
                  <PieChart
                    data={{
                      slices: hl7Types.data.records.map((r: any) => ({
                        category: String(r.message_type ?? "Unknown"),
                        value: Number(r.cnt ?? 0),
                      }))
                    }}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
        <Heading level={3}>HL7 Errors / NAKs</Heading>
        {hl7Errors.isLoading ? <ProgressCircle /> :
          hl7Errors.data?.records?.length ? (
            <DataTable data={hl7Errors.data.records} columns={convertToColumns(hl7Errors.data.types)} />
          ) : <Text>No HL7 errors</Text>}
      </Section>

      {/* FHIR API Health */}
      <Section title="FHIR API Health">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Request Rate Over Time</Heading>
            <div style={{ height: 280 }}>
              {fhirRate.isLoading ? <ProgressCircle /> :
                fhirRate.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(fhirRate.data.records, fhirRate.data.types)}
                    variant="bar"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Response Status</Heading>
            <div style={{ height: 280 }}>
              {fhirStatus.isLoading ? <ProgressCircle /> :
                fhirStatus.data?.records?.length ? (
                  <PieChart
                    data={{
                      slices: fhirStatus.data.records.map((r: any) => ({
                        category: String(r.status_group ?? "Unknown"),
                        value: Number(r.cnt ?? 0),
                      }))
                    }}
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
        <Heading level={3}>Response Time Percentiles</Heading>
        <div style={{ height: 280 }}>
          {fhirResponseTimes.isLoading ? <ProgressCircle /> :
            fhirResponseTimes.data?.records ? (
              <TimeseriesChart
                data={convertToTimeseries(fhirResponseTimes.data.records, fhirResponseTimes.data.types)}
                variant="line"
                gapPolicy="connect"
              />
            ) : <Text>No data</Text>}
        </div>
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Slow Requests ({">"}2s)</Heading>
            {fhirSlow.isLoading ? <ProgressCircle /> :
              fhirSlow.data?.records?.length ? (
                <DataTable data={fhirSlow.data.records} columns={convertToColumns(fhirSlow.data.types)} />
              ) : <Text>No slow requests</Text>}
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Client Usage</Heading>
            {fhirClients.isLoading ? <ProgressCircle /> :
              fhirClients.data?.records?.length ? (
                <DataTable data={fhirClients.data.records} columns={convertToColumns(fhirClients.data.types)} />
              ) : <Text>No data</Text>}
          </Flex>
        </Flex>
      </Section>

      {/* ETL/Integration Job Health */}
      <Section title="ETL / Integration Jobs">
        <Flex gap={16}>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Job Status Over Time</Heading>
            <div style={{ height: 280 }}>
              {etlStatus.isLoading ? <ProgressCircle /> :
                etlStatus.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(etlStatus.data.records, etlStatus.data.types)}
                    variant="bar"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
          <Flex flexDirection="column" style={{ flex: 1 }}>
            <Heading level={3}>Job Duration Trends</Heading>
            <div style={{ height: 280 }}>
              {etlDuration.isLoading ? <ProgressCircle /> :
                etlDuration.data?.records ? (
                  <TimeseriesChart
                    data={convertToTimeseries(etlDuration.data.records, etlDuration.data.types)}
                    variant="line"
                    gapPolicy="connect"
                  />
                ) : <Text>No data</Text>}
            </div>
          </Flex>
        </Flex>
        <Heading level={3}>Failed Jobs</Heading>
        {etlFailed.isLoading ? <ProgressCircle /> :
          etlFailed.data?.records?.length ? (
            <DataTable data={etlFailed.data.records} columns={convertToColumns(etlFailed.data.types)} />
          ) : <Text>No failed ETL jobs</Text>}
      </Section>
    </Flex>
  );
};
