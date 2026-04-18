import React from "react";
import { AppHeader, Flex } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { Link, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { path: "/", label: "Overview" },
  { path: "/epic", label: "Epic Health" },
  { path: "/network", label: "Network" },
  { path: "/integration", label: "Integration" },
  { path: "/sites", label: "Sites" },
  { path: "/explore", label: "Explore" },
];

export const Header = () => {
  const location = useLocation();
  return (
    <AppHeader>
      <AppHeader.ActionItems>
        <Flex gap={4} alignItems="center">
          <Text style={{ fontSize: 16, fontWeight: 700, marginRight: 24 }}>
            🏥 Healthcare Monitor
          </Text>
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
        </Flex>
      </AppHeader.ActionItems>
    </AppHeader>
  );
};
