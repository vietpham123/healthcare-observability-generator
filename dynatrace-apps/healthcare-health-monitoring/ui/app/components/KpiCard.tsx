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
  if (!thresholds) return "inherit";
  const num = typeof value === "number" ? value : Number(value);
  if (isNaN(num)) return "inherit";
  if (num >= thresholds.green) return "var(--dt-colors-charts-categorical-color-01)";
  if (num >= thresholds.amber) return "var(--dt-colors-charts-status-warning)";
  return "var(--dt-colors-charts-status-critical)";
}

export const KpiCard = ({ query, label, field, thresholds, format }: KpiCardProps) => {
  const { data, isLoading } = useDql({ query });
  const value = data?.records?.[0]?.[field] ?? 0;

  if (isLoading) return <ProgressCircle size="small" />;

  return (
    <Flex
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      style={{
        background: "var(--dt-colors-surface-default)",
        borderRadius: 8,
        padding: 16,
        minWidth: 160,
        flex: 1,
      }}
    >
      <Text style={{ fontSize: 32, fontWeight: 700, color: healthColor(value, thresholds) }}>
        {formatValue(value, format)}
      </Text>
      <Text style={{ fontSize: 13, opacity: 0.7 }}>{label}</Text>
    </Flex>
  );
};
