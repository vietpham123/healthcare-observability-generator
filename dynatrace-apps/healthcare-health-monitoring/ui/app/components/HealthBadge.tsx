import React from "react";

type HealthStatus = "healthy" | "warning" | "critical" | "unknown";

const STATUS_COLORS: Record<HealthStatus, string> = {
  healthy: "#2ab06f",
  warning: "#f5a623",
  critical: "#dc3545",
  unknown: "#8c8c8c",
};

const STATUS_LABELS: Record<HealthStatus, string> = {
  healthy: "Healthy",
  warning: "Warning",
  critical: "Critical",
  unknown: "Unknown",
};

interface HealthBadgeProps {
  status: HealthStatus;
  size?: number;
}

export const HealthBadge = ({ status, size = 12 }: HealthBadgeProps) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
    <span
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: STATUS_COLORS[status],
        display: "inline-block",
      }}
    />
    <span style={{ fontSize: 13 }}>{STATUS_LABELS[status]}</span>
  </span>
);

export function computeHealthStatus(value: number, greenThreshold: number, amberThreshold: number): HealthStatus {
  if (value >= greenThreshold) return "healthy";
  if (value >= amberThreshold) return "warning";
  return "critical";
}
