import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { ALL_SITES } from "../queries";

interface SiteFilterProps {
  value: string | null;
  onChange: (siteCode: string | null) => void;
}

const BTN: React.CSSProperties = {
  padding: "5px 14px",
  borderRadius: 6,
  fontSize: 12,
  cursor: "pointer",
  border: "1px solid var(--dt-colors-border-neutral-default)",
  background: "transparent",
  color: "var(--dt-colors-text-primary-default)",
  transition: "background 0.15s, border-color 0.15s",
};

const BTN_ACTIVE: React.CSSProperties = {
  ...BTN,
  background: "var(--dt-colors-surface-default)",
  border: "2px solid var(--dt-colors-charts-categorical-color-01)",
  fontWeight: 600,
};

export const SiteFilter = ({ value, onChange }: SiteFilterProps) => (
  <Flex gap={6} alignItems="center" flexWrap="wrap">
    <Text style={{ fontSize: 11, opacity: 0.5, marginRight: 4 }}>FILTER BY SITE</Text>
    <button style={value === null ? BTN_ACTIVE : BTN} onClick={() => onChange(null)}>All Sites</button>
    {ALL_SITES.map((s) => (
      <button key={s.code} style={value === s.code ? BTN_ACTIVE : BTN} onClick={() => onChange(s.code)}>
        {s.name}
      </button>
    ))}
  </Flex>
);
