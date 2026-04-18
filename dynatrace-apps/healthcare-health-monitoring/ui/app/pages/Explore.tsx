import React, { useState } from "react";
import { Flex, Surface, TitleBar } from "@dynatrace/strato-components/layouts";
import { Heading, Text } from "@dynatrace/strato-components/typography";
import { ProgressCircle } from "@dynatrace/strato-components/content";
import { useDql } from "@dynatrace-sdk/react-hooks";
import { queries } from "../queries";

type PresetKey = "allEpic" | "allNetwork" | "problems";

const PRESETS: Record<PresetKey, { label: string; query: string }> = {
  allEpic: { label: "Epic Events", query: queries.allEpicEvents },
  allNetwork: { label: "Network Events", query: queries.allNetworkEvents },
  problems: { label: "Active Problems", query: queries.activeProblemsList },
};

export const Explore = () => {
  const [active, setActive] = useState<PresetKey>("allEpic");
  const { data, isLoading } = useDql({ query: PRESETS[active].query });
  const records = data?.records ?? [];

  return (
    <Flex flexDirection="column" gap={16} padding={16}>
      <Heading level={3}>Explore Data</Heading>

      <Flex gap={8}>
        {(Object.keys(PRESETS) as PresetKey[]).map((key) => (
          <button
            key={key}
            onClick={() => setActive(key)}
            style={{
              padding: "8px 18px",
              borderRadius: 8,
              border: active === key ? "2px solid var(--dt-colors-charts-categorical-color-01)" : "1px solid var(--dt-colors-border-neutral-default)",
              background: active === key ? "var(--dt-colors-surface-default)" : "transparent",
              fontWeight: active === key ? 600 : 400,
              fontSize: 13,
              cursor: "pointer",
              color: "var(--dt-colors-text-primary-default)",
            }}
          >
            {PRESETS[key].label}
          </button>
        ))}
      </Flex>

      <Surface style={{ padding: 16, borderRadius: 12 }}>
        <TitleBar>
          <TitleBar.Title>{PRESETS[active].label}</TitleBar.Title>
          <TitleBar.Subtitle>{records.length} records</TitleBar.Subtitle>
        </TitleBar>

        {isLoading ? (
          <Flex justifyContent="center" style={{ padding: 40 }}><ProgressCircle /></Flex>
        ) : records.length === 0 ? (
          <Text style={{ padding: 20, opacity: 0.5 }}>No records found</Text>
        ) : (
          <div style={{ maxHeight: 600, overflow: "auto", fontSize: 12 }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {Object.keys(records[0]).map((key) => (
                    <th key={key} style={TH}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((r: any, i: number) => (
                  <tr key={i}>
                    {Object.keys(records[0]).map((key) => (
                      <td key={key} style={TD}>
                        {r[key] instanceof Date || (typeof r[key] === "string" && r[key].match(/^\d{4}-\d{2}-\d{2}T/))
                          ? new Date(r[key]).toLocaleString()
                          : String(r[key] ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Surface>
    </Flex>
  );
};

const TH: React.CSSProperties = { padding: "6px 8px", textAlign: "left", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", fontWeight: 600, whiteSpace: "nowrap" };
const TD: React.CSSProperties = { padding: "4px 8px", borderBottom: "1px solid var(--dt-colors-border-neutral-default)", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" };
