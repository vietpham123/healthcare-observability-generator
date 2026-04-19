import React from "react";
import { AppHeader, Flex } from "@dynatrace/strato-components/layouts";
import { TimeframeSelector } from "@dynatrace/strato-components/filters";
import { Button } from "@dynatrace/strato-components/buttons";
import { Tooltip } from "@dynatrace/strato-components/overlays";
import { RefreshIcon } from "@dynatrace/strato-icons";
import type { Timeframe } from "@dynatrace/strato-components/core";
import { Link, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { path: "/", label: "Overview" },
  { path: "/epic", label: "Epic Health" },
  { path: "/network", label: "Network" },
  { path: "/integration", label: "Integration" },
  { path: "/security", label: "Security" },
  { path: "/mychart", label: "MyChart" },
  { path: "/sites", label: "Sites" },
  { path: "/explore", label: "Explore" },
];

interface HeaderProps {
  timeframe?: Timeframe;
  onTimeframeChange?: (tf: Timeframe | null) => void;
  onRefresh?: () => void;
}

export const Header = ({ timeframe, onTimeframeChange, onRefresh }: HeaderProps) => {
  const location = useLocation();
  return (
    <AppHeader>
      <AppHeader.ActionItems>
        <Flex gap={4} alignItems="center" style={{ width: "100%" }}>
          {NAV_ITEMS.map((item) => {
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  padding: "6px 14px",
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: active ? 600 : 400,
                  background: active ? "var(--dt-colors-surface-default)" : "transparent",
                  color: active ? "var(--dt-colors-text-primary-default)" : "var(--dt-colors-text-secondary-default)",
                  textDecoration: "none",
                  transition: "background 0.15s",
                }}
              >
                {item.label}
              </Link>
            );
          })}
          <Flex gap={8} alignItems="center" style={{ marginLeft: "auto" }}>
            <TimeframeSelector value={timeframe} onChange={onTimeframeChange} />
            <Tooltip text="Refresh all queries with the current timeframe">
              <Button variant="accent" onClick={onRefresh}>
                <Button.Prefix><RefreshIcon /></Button.Prefix>
              </Button>
            </Tooltip>
          </Flex>
        </Flex>
      </AppHeader.ActionItems>
    </AppHeader>
  );
};
