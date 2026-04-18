import React from "react";
import { Flex } from "@dynatrace/strato-components/layouts";
import { Text } from "@dynatrace/strato-components/typography";
import { computeHealthStatus, statusColor } from "./HealthBadge";

interface SiteMapData {
  code: string;
  name: string;
  label: string;
  x: number;
  y: number;
  events: number;
  loginRate: number;
  users: number;
}

interface CampusMapProps {
  sites: SiteMapData[];
  onSiteClick?: (code: string) => void;
}

export const CampusMap = ({ sites, onSiteClick }: CampusMapProps) => {
  return (
    <div style={{ position: "relative", width: "100%", height: 320, background: "var(--dt-colors-surface-default)", borderRadius: 12, overflow: "hidden" }}>
      {/* Kansas state outline hint */}
      <svg viewBox="0 0 600 320" style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}>
        {/* Kansas approx outline */}
        <path d="M 80 60 L 520 60 L 520 260 L 80 260 Z" fill="none" stroke="var(--dt-colors-border-neutral-default)" strokeWidth="1" strokeDasharray="6 3" opacity="0.3" />
        {/* Connection lines between sites */}
        {sites.length >= 4 && (
          <>
            <line x1={sites[0].x} y1={sites[0].y} x2={sites[1].x} y2={sites[1].y} stroke="var(--dt-colors-border-neutral-default)" strokeWidth="1" opacity="0.2" strokeDasharray="4 2" />
            <line x1={sites[0].x} y1={sites[0].y} x2={sites[2].x} y2={sites[2].y} stroke="var(--dt-colors-border-neutral-default)" strokeWidth="1" opacity="0.2" strokeDasharray="4 2" />
            <line x1={sites[0].x} y1={sites[0].y} x2={sites[3].x} y2={sites[3].y} stroke="var(--dt-colors-border-neutral-default)" strokeWidth="1" opacity="0.2" strokeDasharray="4 2" />
          </>
        )}
        {/* Site nodes */}
        {sites.map((site) => {
          const status = computeHealthStatus(site.loginRate, 90, 70);
          const color = statusColor(status);
          const radius = Math.max(20, Math.min(40, site.events / 10));
          return (
            <g
              key={site.code}
              onClick={() => onSiteClick?.(site.code)}
              style={{ cursor: onSiteClick ? "pointer" : "default" }}
            >
              {/* Outer pulse ring */}
              <circle cx={site.x} cy={site.y} r={radius + 8} fill={color} opacity="0.1">
                <animate attributeName="r" from={radius + 4} to={radius + 14} dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.15" to="0" dur="2s" repeatCount="indefinite" />
              </circle>
              {/* Main circle */}
              <circle cx={site.x} cy={site.y} r={radius} fill={color} opacity="0.85" />
              {/* Inner bright ring */}
              <circle cx={site.x} cy={site.y} r={radius - 4} fill="none" stroke="#fff" strokeWidth="1.5" opacity="0.4" />
              {/* Events count */}
              <text x={site.x} y={site.y - 2} textAnchor="middle" fill="#fff" fontSize="14" fontWeight="700">
                {site.events}
              </text>
              <text x={site.x} y={site.y + 12} textAnchor="middle" fill="#fff" fontSize="8" opacity="0.8">
                events
              </text>
              {/* Label below */}
              <text x={site.x} y={site.y + radius + 18} textAnchor="middle" fill="var(--dt-colors-text-primary-default)" fontSize="12" fontWeight="600">
                {site.label}
              </text>
              <text x={site.x} y={site.y + radius + 32} textAnchor="middle" fill="var(--dt-colors-text-secondary-default)" fontSize="10">
                {site.loginRate.toFixed(0)}% login · {site.users} users
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
