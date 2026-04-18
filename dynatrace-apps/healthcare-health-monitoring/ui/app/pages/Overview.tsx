import React from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { TimeseriesChart, DonutChart, CategoricalBarChart } from "@dynatrace/strato-components/charts";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";
import { KpiCard } from "../components/KpiCard";
import { CampusMap } from "../components/CampusMap";
import { toTimeseries, toDonutData, toBarData } from "../utils/chartHelpers";

const SITE_META: Record<string, { name: string; label: string; x: number; y: number }> = {
  "kcrmc-main": { name: "KC Regional Medical Center", label: "KC Main Campus", x: 450, y: 130 },
  "oak-clinic": { name: "Oakley Rural Health", label: "Oakley Clinic", x: 100, y: 130 },
  "wel-clinic": { name: "Wellington Care Center", label: "Wellington Clinic", x: 280, y: 260 },
  "bel-clinic": { name: "Belleville Family Medicine", label: "Belleville Clinic", x: 300, y: 60 },
};

export const Overview = () => {
  const siteHealth = useDql({ query: queries.siteHealthSummary });
  const netDevices = useDql({ query: queries.networkDevicesBySite });
  const siteRecords = siteHealth.data?.records ?? [];
  const devRecords = netDevices.data?.records ?? [];

  const campusSites = siteRecords.map((r: any) => {
    const code = r.site ?? "";
    const meta = SITE_META[code] ?? { name: code, label: code, x: 300, y: 160 };
    const logins = Number(r.logins) || 0;
    const loginOk = Number(r.login_ok) || 0;
    const devRec = devRecords.find((d: any) => d.site === code);
    return {
      code, name: meta.name, label: meta.label, x: meta.x, y: meta.y,
      events: Number(r.events) || 0,
      loginRate: logins > 0 ? (loginOk / logins) * 100 : 100,
      users: Number(r.users) || 0,
      devices: Number(devRec?.devices) || 0,
    };
  });

  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      <Text style={{ fontSize: 13, opacity: 0.6, marginBottom: -8 }}>
        System-wide view of Kansas City Regional Medical Center and satellite clinics — login health, device status, event distribution, and cross-system correlation.
      </Text>
      <Flex gap={12} flexWrap="wrap">
        <KpiCard query={queries.epicLoginSuccessRate} label="Epic Login Success" field="success_rate" format="percent" thresholds={{ green: 90, amber: 70 }} icon="🔐" />
        <KpiCard query={queries.hl7DeliveryRate} label="HL7 Delivery" field="delivery_rate" format="percent" thresholds={{ green: 95, amber: 80 }} icon="📡" />
        <KpiCard query={queries.fhirHealthRate} label="FHIR API Health" field="success_rate" format="percent" thresholds={{ green: 95, amber: 85 }} icon="🔗" />
        <KpiCard query={queries.etlSuccessRate} label="ETL Success" field="success_rate" format="percent" thresholds={{ green: 95, amber: 80 }} icon="⚙️" />
        <KpiCard query={queries.avgDeviceCpu} label="Avg Device CPU" field="avg_cpu" format="percent" thresholds={{ green: 80, amber: 60 }} icon="💻" />
        <KpiCard query={queries.activeUsers} label="Active Users" field="unique_users" format="number" icon="👥" />
      </Flex>

      <Flex gap={16}>
        <Surface style={{ flex: 2, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Campus Health Map</TitleBar.Title><TitleBar.Subtitle>Kansas Healthcare Network</TitleBar.Subtitle></TitleBar>
          {siteHealth.isLoading
            ? <Flex alignItems="center" justifyContent="center" style={{ height: 300 }}><ProgressCircle /></Flex>
            : <CampusMap sites={campusSites} />}
        </Surface>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Epic Event Distribution</TitleBar.Title></TitleBar>
          <EventDistChart />
        </Surface>
      </Flex>

      <Flex gap={16}>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>System Activity</TitleBar.Title><TitleBar.Subtitle>Epic vs Network event volume</TitleBar.Subtitle></TitleBar>
          <ActivityTimelineChart />
        </Surface>
        <Surface style={{ flex: 1, padding: 16, borderRadius: 12 }}>
          <TitleBar><TitleBar.Title>Events by Site & Pipeline</TitleBar.Title></TitleBar>
          <EventsBySiteChart />
        </Surface>
      </Flex>

      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar><TitleBar.Title>Epic ↔ Network Correlation</TitleBar.Title><TitleBar.Subtitle>Overlay of Epic workflow events with network infrastructure events</TitleBar.Subtitle></TitleBar>
        <CorrelationChart />
      </Surface>
    </Flex>
  );
};

const EventDistChart = () => {
  const { data, isLoading } = useDql({ query: queries.epicEventDistribution });
  if (isLoading) return <ProgressCircle />;
  return <DonutChart data={toDonutData(data?.records ?? [])} />;
};

const ActivityTimelineChart = () => {
  const result = useDql({ query: queries.systemActivityTimeline });
  if (result.isLoading) return <ProgressCircle />;
  return <TimeseriesChart data={toTimeseries(result.data)} />;
};

const EventsBySiteChart = () => {
  const { data, isLoading } = useDql({ query: queries.eventsBySite });
  if (isLoading) return <ProgressCircle />;
  return <CategoricalBarChart data={toBarData(data?.records ?? [])} />;
};

const CorrelationChart = () => {
  const result = useDql({ query: queries.epicNetworkCorrelation });
  if (result.isLoading) return <ProgressCircle />;
  return <TimeseriesChart data={toTimeseries(result.data)} variant="area" />;
};
