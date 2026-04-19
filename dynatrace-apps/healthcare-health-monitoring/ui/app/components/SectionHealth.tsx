import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { useDql } from "@dynatrace-sdk/react-hooks";

type HealthStatus = "healthy" | "warning" | "critical" | "unknown";

const STATUS_COLORS: Record<HealthStatus, string> = {
  healthy: "#2ab06f",
  warning: "#f5a623",
  critical: "#dc3545",
  unknown: "var(--dt-colors-text-secondary-default)",
};

const STATUS_LABELS: Record<HealthStatus, string> = {
  healthy: "Healthy",
  warning: "Warning",
  critical: "Critical",
  unknown: "—",
};

interface SectionHealthProps {
  query: string;
  field: string;
  green: number;
  amber: number;
  /** When true, lower values are better (CPU %, error rate). */
  invert?: boolean;
}

function computeStatus(value: number, green: number, amber: number, invert?: boolean): HealthStatus {
  if (isNaN(value)) return "unknown";
  if (invert) {
    if (value <= green) return "healthy";
    if (value <= amber) return "warning";
    return "critical";
  }
  if (value >= green) return "healthy";
  if (value >= amber) return "warning";
  return "critical";
}

/**
 * Compact health indicator for section headers.
 * Runs a DQL query (cached/deduped by useDql) and shows a colored dot + label.
 */
export const SectionHealth = ({ query, field, green, amber, invert }: SectionHealthProps) => {
  const { data, isLoading } = useDql({ query });

  if (isLoading) return <ProgressCircle size="small" />;

  const raw = data?.records?.[0]?.[field];
  const value = typeof raw === "number" ? raw : Number(raw);
  const status = computeStatus(value, green, amber, invert);

  return (
    <Flex alignItems="center" gap={6} style={{ marginLeft: 12 }}>
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: STATUS_COLORS[status],
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      <span style={{ fontSize: 12, color: STATUS_COLORS[status], fontWeight: 500 }}>
        {STATUS_LABELS[status]}
      </span>
    </Flex>
  );
};
