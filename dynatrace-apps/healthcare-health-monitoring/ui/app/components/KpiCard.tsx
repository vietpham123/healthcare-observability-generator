import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { useDql } from "@dynatrace-sdk/react-hooks";

interface KpiCardProps {
  query: string;
  label: string;
  field: string;
  thresholds?: { green: number; amber: number };
  format?: "number" | "percent" | "bytes";
  icon?: string;
}

function formatValue(value: unknown, format?: string): string {
  if (value == null) return "—";
  const num = typeof value === "number" ? value : Number(value);
  if (isNaN(num)) return String(value);
  if (format === "percent") return `${num.toFixed(1)}%`;
  if (format === "bytes") {
    if (num > 1e9) return `${(num / 1e9).toFixed(1)} GB`;
    if (num > 1e6) return `${(num / 1e6).toFixed(1)} MB`;
    if (num > 1e3) return `${(num / 1e3).toFixed(1)} KB`;
    return `${num} B`;
  }
  return num.toLocaleString();
}

function healthColor(value: unknown, thresholds?: { green: number; amber: number }): string {
  if (!thresholds) return "#fff";
  const num = typeof value === "number" ? value : Number(value);
  if (isNaN(num)) return "#fff";
  if (num >= thresholds.green) return "#2ab06f";
  if (num >= thresholds.amber) return "#f5a623";
  return "#dc3545";
}

export const KpiCard = ({ query, label, field, thresholds, format, icon }: KpiCardProps) => {
  const { data, isLoading } = useDql({ query });
  const value = data?.records?.[0]?.[field] ?? 0;

  if (isLoading)
    return (
      <Flex alignItems="center" justifyContent="center" style={{ minWidth: 160, minHeight: 90 }}>
        <ProgressCircle size="small" />
      </Flex>
    );

  const color = healthColor(value, thresholds);

  return (
    <Flex
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      style={{
        background: "var(--dt-colors-surface-default)",
        borderRadius: 12,
        padding: "16px 20px",
        minWidth: 160,
        flex: 1,
        borderLeft: `4px solid ${color}`,
      }}
    >
      <Text style={{ fontSize: 11, opacity: 0.5, textTransform: "uppercase", letterSpacing: 1 }}>
        {icon ? `${icon} ` : ""}{label}
      </Text>
      <Text style={{ fontSize: 36, fontWeight: 700, color, marginTop: 4 }}>
        {formatValue(value, format)}
      </Text>
    </Flex>
  );
};
