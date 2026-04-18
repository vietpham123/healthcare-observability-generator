import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Text, Heading } from "@dynatrace/strato-components/typography";
import { HealthBadge, computeHealthStatus } from "./HealthBadge";

interface SiteCardProps {
  name: string;
  code: string;
  epicHealth: number;
  networkHealth: number;
  integrationHealth: number;
  activeProblems: number;
  onClick?: () => void;
}

export const SiteCard = ({
  name,
  code,
  epicHealth,
  networkHealth,
  integrationHealth,
  activeProblems,
  onClick,
}: SiteCardProps) => {
  const composite = epicHealth * 0.4 + networkHealth * 0.3 + integrationHealth * 0.3;
  const status = computeHealthStatus(composite, 90, 70);

  return (
    <Flex
      flexDirection="column"
      gap={8}
      onClick={onClick}
      style={{
        background: "var(--dt-colors-surface-default)",
        borderRadius: 12,
        padding: 20,
        minWidth: 220,
        flex: 1,
        cursor: onClick ? "pointer" : "default",
        border: "1px solid var(--dt-colors-border-neutral-default)",
      }}
    >
      <Flex justifyContent="space-between" alignItems="center">
        <Heading level={4}>{name}</Heading>
        <HealthBadge status={status} />
      </Flex>
      <Text style={{ fontSize: 12, opacity: 0.6 }}>{code}</Text>
      <Flex gap={16} style={{ marginTop: 8 }}>
        <Flex flexDirection="column" alignItems="center">
          <Text style={{ fontSize: 20, fontWeight: 600 }}>{composite.toFixed(0)}</Text>
          <Text style={{ fontSize: 11, opacity: 0.6 }}>Composite</Text>
        </Flex>
        <Flex flexDirection="column" alignItems="center">
          <Text style={{ fontSize: 14 }}>{epicHealth.toFixed(0)}</Text>
          <Text style={{ fontSize: 11, opacity: 0.6 }}>Epic</Text>
        </Flex>
        <Flex flexDirection="column" alignItems="center">
          <Text style={{ fontSize: 14 }}>{networkHealth.toFixed(0)}</Text>
          <Text style={{ fontSize: 11, opacity: 0.6 }}>Network</Text>
        </Flex>
        <Flex flexDirection="column" alignItems="center">
          <Text style={{ fontSize: 14 }}>{integrationHealth.toFixed(0)}</Text>
          <Text style={{ fontSize: 11, opacity: 0.6 }}>Integration</Text>
        </Flex>
      </Flex>
      {activeProblems > 0 && (
        <Text style={{ color: "var(--dt-colors-charts-status-critical)", fontSize: 12, marginTop: 4 }}>
          {activeProblems} active problem{activeProblems > 1 ? "s" : ""}
        </Text>
      )}
    </Flex>
  );
};
