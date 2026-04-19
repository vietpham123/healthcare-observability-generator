import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { Tooltip } from "@dynatrace/strato-components/overlays";
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
  /** What this health indicator measures and what causes status changes. */
  description?: string;
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

function formatNum(n: number): string {
  if (isNaN(n)) return "—";
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

/**
 * Compact health indicator for section headers.
 * Runs a DQL query (cached/deduped by useDql) and shows a colored dot + label.
 * Auto-refreshes every 30 seconds for near-real-time health status.
 * Hovering shows a tooltip with threshold criteria and what drives the status.
 */
const HEALTH_REFRESH_MS = 30_000;

export const SectionHealth = ({ query, field, green, amber, invert, description }: SectionHealthProps) => {
  const { data, isLoading } = useDql({ query }, { refetchInterval: HEALTH_REFRESH_MS });

  if (isLoading) return <ProgressCircle size="small" />;

  const raw = data?.records?.[0]?.[field];
  const value = typeof raw === "number" ? raw : Number(raw);
  const status = computeStatus(value, green, amber, invert);

  const tooltipContent = (
    <div style={{ maxWidth: 300, lineHeight: 1.6, fontSize: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Health Status: {STATUS_LABELS[status]}</div>
      {description && <div style={{ opacity: 0.85, marginBottom: 6 }}>{description}</div>}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.15)", paddingTop: 6, marginTop: 2 }}>
        <div style={{ marginBottom: 2 }}>
          <span style={{ color: "#2ab06f" }}>● Healthy</span>: {invert ? `≤ ${formatNum(green)}` : `≥ ${formatNum(green)}`}
        </div>
        <div style={{ marginBottom: 2 }}>
          <span style={{ color: "#f5a623" }}>● Warning</span>: {invert ? `${formatNum(green)} – ${formatNum(amber)}` : `${formatNum(amber)} – ${formatNum(green)}`}
        </div>
        <div style={{ marginBottom: 2 }}>
          <span style={{ color: "#dc3545" }}>● Critical</span>: {invert ? `> ${formatNum(amber)}` : `< ${formatNum(amber)}`}
        </div>
      </div>
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.15)", paddingTop: 6, marginTop: 6, fontWeight: 600 }}>
        Current value: {formatNum(value)}
      </div>
    </div>
  );

  return (
    <Tooltip text={tooltipContent} placement="bottom">
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          marginLeft: 12,
          cursor: "help",
        }}
      >
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
      </div>
    </Tooltip>
  );
};
