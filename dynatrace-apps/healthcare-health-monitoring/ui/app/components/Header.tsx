import React from "react";
import { Link } from "react-router-dom";
import { AppHeader } from "@dynatrace/strato-components-preview/layouts";
import { TimeframeSelector } from "@dynatrace/strato-components/filters";
import type { Timeframe } from "@dynatrace/strato-components/core";

interface HeaderProps {
  timeframe: Timeframe;
  onTimeframeChange: (tf: Timeframe) => void;
}

export const Header = ({ timeframe, onTimeframeChange }: HeaderProps) => {
  return (
    <AppHeader>
      <AppHeader.NavItems>
        <AppHeader.AppNavLink as={Link} to="/" />
        <AppHeader.NavItem as={Link} to="/epic">
          Epic Health
        </AppHeader.NavItem>
        <AppHeader.NavItem as={Link} to="/network">
          Network Health
        </AppHeader.NavItem>
        <AppHeader.NavItem as={Link} to="/integrations">
          Integrations
        </AppHeader.NavItem>
        <AppHeader.NavItem as={Link} to="/sites">
          Site View
        </AppHeader.NavItem>
        <AppHeader.NavItem as={Link} to="/explore">
          Explore
        </AppHeader.NavItem>
      </AppHeader.NavItems>
      <AppHeader.ActionItems>
        <TimeframeSelector
          value={timeframe}
          onChange={(value) => value && onTimeframeChange(value)}
        />
      </AppHeader.ActionItems>
    </AppHeader>
  );
};
