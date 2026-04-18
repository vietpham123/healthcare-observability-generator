import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Text, Heading } from "@dynatrace/strato-components/typography";
import { HealthBadge, computeHealthStatus } from "./HealthBadge";

interface SiteCardProps {
  name: string;
  code: string;
  events: number;
  users: number;
  loginRate: number;
  avgCpu: number;
  devices: number;
  onClick?: () => void;
}

export const SiteCard = ({
  name,
  code,
  events,
  users,
  loginRate,
  avgCpu,
  devices,
  onClick,
}: SiteCardProps) => {
  const status = computeHealthStatus(loginRate, 90, 70);

  return (
    <Flex
      flexDirection="column"
      gap={8}
      onClick={onClick}
      style={{
        background: "var(--dt-colors-surface-default)",
        borderRadius: 12,
        padding: 20,
        minWidth: 240,
        flex: 1,
        cursor: onClick ? "pointer" : "default",
        border: "1px solid var(--dt-colors-border-neutral-default)",
        transition: "box-shadow 0.2s",
      }}
    >
      <Flex justifyContent="space-between" alignItems="center">
        <Heading level={4}>{name}</Heading>
        <HealthBadge status={status} />
      </Flex>
      <Text style={{ fontSize: 12, opacity: 0.5 }}>{code}</Text>

      <Flex gap={20} style={{ marginTop: 8 }}>
        <Flex flexDirection="column" alignItems="center">
          <Text style={{ fontSize: 22, fontWeight: 600, color: "#2ab06f" }}>{events}</Text>
          <Text style={{ fontSize: 10, opacity: 0.5 }}>Events</Text>
        </Flex>
        <Flex flexDirection="column" alignItems="center">
          <Text style={{ fontSize: 22, fontWeight: 600 }}>{users}</Text>
          <Text style={{ fontSize: 10, opacity: 0.5 }}>Users</Text>
        </Flex>
        <Flex flexDirection="column" alignItems="center">
          <Text style={{ fontSize: 22, fontWeight: 600, color: loginRate >= 90 ? "#2ab06f" : loginRate >= 70 ? "#f5a623" : "#dc3545" }}>
            {loginRate.toFixed(0)}%
          </Text>
          <Text style={{ fontSize: 10, opacity: 0.5 }}>Login</Text>
        </Flex>
        <Flex flexDirection="column" alignItems="center">
          <Text style={{ fontSize: 22, fontWeight: 600 }}>{devices}</Text>
          <Text style={{ fontSize: 10, opacity: 0.5 }}>Devices</Text>
        </Flex>
      </Flex>
    </Flex>
  );
};
