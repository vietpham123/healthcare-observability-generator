import React from "react";
import { FilterBar } from "@dynatrace/strato-components/filters";
import { Select, SelectOption } from "@dynatrace/strato-components/forms";
import { ALL_SITES } from "../queries";

interface SiteFilterProps {
  value: string | null;
  onChange: (siteCode: string | null) => void;
}

export const SiteFilter = ({ value, onChange }: SiteFilterProps) => (
  <FilterBar onFilterChange={() => {}}>
    <FilterBar.Item name="site" label="Site">
      <Select name="site" value={value} onChange={(val) => {
        const v = val == null ? null : String(val);
        onChange(v === "" ? null : v);
      }}>
        <SelectOption value="">All Sites</SelectOption>
        {ALL_SITES.map((s) => (
          <SelectOption key={s.code} value={s.code}>{s.name}</SelectOption>
        ))}
      </Select>
    </FilterBar.Item>
  </FilterBar>
);
