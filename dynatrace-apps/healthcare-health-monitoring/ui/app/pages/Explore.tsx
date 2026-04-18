import React, { useState } from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Heading, Text } from "@dynatrace/strato-components/typography";
import { DataTable } from "@dynatrace/strato-components-preview/tables";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";

const PRESETS: Array<{ label: string; queryKey: keyof typeof queries; description: string }> = [
  { label: "All Epic Events", queryKey: "allEpicEvents", description: "Recent Epic SIEM events with key fields" },
  { label: "All Network Events", queryKey: "allNetworkEvents", description: "Recent network infrastructure events" },
  { label: "Events by Site", queryKey: "eventsBySite", description: "Event counts by healthcare site (Epic + Network)" },
  { label: "Login Activity", queryKey: "loginBySite", description: "Login counts per site" },
  { label: "SNMP Device Snapshot", queryKey: "snmpDeviceSnapshot", description: "Latest CPU/memory/sessions per device" },
  { label: "HL7 Errors", queryKey: "hl7Errors", description: "HL7 NAK/error messages" },
  { label: "FHIR Slow Requests", queryKey: "fhirSlowRequests", description: "FHIR API requests >2000ms" },
  { label: "FHIR Client Usage", queryKey: "fhirClientUsage", description: "Requests by FHIR client" },
  { label: "ETL Failed Jobs", queryKey: "etlFailedJobs", description: "Failed ETL/integration jobs" },
  { label: "Interface Changes", queryKey: "interfaceStateChanges", description: "Cisco IOS interface up/down events" },
  { label: "Link Flap Detection", queryKey: "linkFlapDetection", description: "Interfaces with >3 flaps in 30min" },
  { label: "Routing Neighbors", queryKey: "routingNeighborTable", description: "OSPF/BGP neighbor state events" },
  { label: "Active Problems", queryKey: "activeProblemsList", description: "Davis AI active problems" },
  { label: "Problem History", queryKey: "problemHistory", description: "Closed problems by category" },
  { label: "Cross: Network→Epic Impact", queryKey: "networkOutageEpicImpact", description: "Interface downs correlated with Epic event volume" },
  { label: "Cross: CPU vs FHIR Latency", queryKey: "deviceCpuVsFhirLatency", description: "Device CPU vs FHIR P95 response time" },
  { label: "Site Composite Health", queryKey: "siteCompositeHealth", description: "Combined Epic + Network health score per site" },
];

function QueryResult({ queryKey }: { queryKey: keyof typeof queries }) {
  const query = queries[queryKey];
  const { data, isLoading, error } = useDql({ query });

  if (isLoading) return <ProgressCircle />;
  if (error) return <Text style={{ color: "var(--dt-colors-charts-status-critical)" }}>Error: {String(error)}</Text>;
  if (!data?.records?.length) return <Text>No results</Text>;

  const columns = Object.keys(data.records[0] as object).map(key => ({
    accessor: key,
    header: key,
  }));

  return <DataTable data={data.records} columns={columns} />;
}

export const Explore = () => {
  const [activePreset, setActivePreset] = useState<keyof typeof queries | null>(null);

  return (
    <Flex flexDirection="column" gap={24} padding={24}>
      <Heading level={1}>Explore Health Data</Heading>
      <Text>
        Pre-built DQL queries for healthcare operations analysis. Select a preset
        to query Epic EHR, network infrastructure, and cross-correlation data.
      </Text>

      {/* Preset Buttons */}
      <Flex gap={8} flexWrap="wrap">
        {PRESETS.map(preset => (
          <button
            key={preset.queryKey}
            onClick={() => setActivePreset(
              activePreset === preset.queryKey ? null : preset.queryKey
            )}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              border: "1px solid var(--dt-colors-border-neutral-default)",
              background: activePreset === preset.queryKey
                ? "var(--dt-colors-surface-highlight)"
                : "var(--dt-colors-surface-default)",
              color: "inherit",
              cursor: "pointer",
              fontSize: 13,
            }}
            title={preset.description}
          >
            {preset.label}
          </button>
        ))}
      </Flex>

      {/* Active Query Info */}
      {activePreset && (
        <Flex flexDirection="column" gap={8} style={{
          background: "var(--dt-colors-surface-default)",
          borderRadius: 8,
          padding: 12,
        }}>
          <Text style={{ fontSize: 12, fontFamily: "monospace", opacity: 0.7 }}>
            {queries[activePreset]}
          </Text>
        </Flex>
      )}

      {/* Results */}
      {activePreset && (
        <Flex flexDirection="column" style={{
          background: "var(--dt-colors-surface-default)",
          borderRadius: 12,
          padding: 20,
        }}>
          <Heading level={2}>
            {PRESETS.find(p => p.queryKey === activePreset)?.label || "Results"}
          </Heading>
          <QueryResult queryKey={activePreset} />
        </Flex>
      )}
    </Flex>
  );
};
