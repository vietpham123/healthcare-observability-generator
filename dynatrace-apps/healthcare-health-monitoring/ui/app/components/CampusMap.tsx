import React, { useEffect, useRef, useMemo } from "react";
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
  devices?: number;
}

interface FlowData {
  from: string;
  to: string;
  volume: number;
  label?: string;
}

interface CampusMapProps {
  sites: SiteMapData[];
  flows?: FlowData[];
  onSiteClick?: (code: string) => void;
}

// Kansas state outline (simplified)
const KS_OUTLINE = "M 62 52 L 640 52 L 640 60 L 648 60 L 648 72 L 640 72 L 640 370 L 62 370 Z";

// County grid for subtle texture
const COUNTY_LINES = [
  "M 62 132 L 640 132", "M 62 212 L 640 212", "M 62 292 L 640 292",
  "M 158 52 L 158 370", "M 254 52 L 254 370", "M 350 52 L 350 370",
  "M 446 52 L 446 370", "M 542 52 L 542 370",
];

// Geographic positions in SVG viewBox(0 0 700 420)
const SITE_GEO: Record<string, { gx: number; gy: number }> = {
  "kcrmc-main": { gx: 608, gy: 115 },
  "tpk-clinic": { gx: 525, gy: 105 },
  "lwr-clinic": { gx: 565, gy: 120 },
  "wch-clinic": { gx: 430, gy: 270 },
};

// Background reference cities
const REF_CITIES = [
  { name: "Dodge City", x: 210, y: 255 },
  { name: "Salina", x: 350, y: 150 },
  { name: "Manhattan", x: 468, y: 98 },
  { name: "Emporia", x: 490, y: 195 },
  { name: "Hays", x: 278, y: 132 },
  { name: "Garden City", x: 158, y: 230 },
  { name: "Hutchinson", x: 370, y: 225 },
  { name: "Pittsburg", x: 610, y: 310 },
  { name: "Liberal", x: 165, y: 340 },
  { name: "Colby", x: 145, y: 75 },
];

// Build a curved bezier path between two points
function curvedPath(x1: number, y1: number, x2: number, y2: number): string {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  const offset = Math.min(len * 0.18, 45);
  const mx = (x1 + x2) / 2 + (-dy / len) * offset;
  const my = (y1 + y2) / 2 + (dx / len) * offset;
  return `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
}

// Evaluate a quadratic bezier at t
function bezierAt(
  x1: number, y1: number,
  cx: number, cy: number,
  x2: number, y2: number,
  t: number,
) {
  const mt = 1 - t;
  return {
    x: mt * mt * x1 + 2 * mt * t * cx + t * t * x2,
    y: mt * mt * y1 + 2 * mt * t * cy + t * t * y2,
  };
}

export const CampusMap = ({ sites, flows = [], onSiteClick }: CampusMapProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Merge geographic positions
  const geoSites = useMemo(
    () => sites.map((s) => ({ ...s, ...(SITE_GEO[s.code] ?? { gx: s.x, gy: s.y }) })),
    [sites],
  );

  // Default hub-and-spoke flows if not provided
  const activeFlows = useMemo(() => {
    if (flows.length > 0) return flows;
    const hub = geoSites.find((s) => s.code === "kcrmc-main");
    if (!hub) return [];
    return geoSites
      .filter((s) => s.code !== "kcrmc-main")
      .map((s) => ({
        from: "kcrmc-main",
        to: s.code,
        volume: Math.round((s.events + hub.events) / 2),
        label: `${s.events} ev`,
      }));
  }, [flows, geoSites]);

  const maxVol = Math.max(1, ...activeFlows.map((f) => f.volume));

  // Canvas particle animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || activeFlows.length === 0 || geoSites.length < 2) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const sx = rect.width / 700;
    const sy = rect.height / 420;
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    ctx.scale(2, 2);

    interface Particle { fi: number; t: number; speed: number; sz: number; }
    const particles: Particle[] = [];
    activeFlows.forEach((flow, fi) => {
      const n = Math.max(3, Math.round((flow.volume / maxVol) * 8));
      for (let i = 0; i < n; i++) {
        particles.push({
          fi,
          t: Math.random(),
          speed: 0.0015 + Math.random() * 0.003,
          sz: 1.2 + (flow.volume / maxVol) * 2.5,
        });
      }
    });

    let raf: number;
    const draw = () => {
      ctx.clearRect(0, 0, rect.width, rect.height);
      for (const p of particles) {
        const fl = activeFlows[p.fi];
        const a = geoSites.find((s) => s.code === fl.from);
        const b = geoSites.find((s) => s.code === fl.to);
        if (!a || !b) continue;
        const x1 = a.gx * sx, y1 = a.gy * sy;
        const x2 = b.gx * sx, y2 = b.gy * sy;
        const dx = x2 - x1, dy = y2 - y1;
        const len = Math.sqrt(dx * dx + dy * dy);
        const off = Math.min(len * 0.18, 45 * sx);
        const cx = (x1 + x2) / 2 + (-dy / len) * off;
        const cy = (y1 + y2) / 2 + (dx / len) * off;
        const pt = bezierAt(x1, y1, cx, cy, x2, y2, p.t);
        // Glow
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, p.sz * 3.5, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(91,143,249,0.12)";
        ctx.fill();
        // Core
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, p.sz, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(120,170,255,0.9)";
        ctx.fill();
        p.t += p.speed;
        if (p.t > 1) p.t = 0;
      }
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [activeFlows, geoSites, maxVol]);

  return (
    <div style={{
      position: "relative", width: "100%", height: 420,
      background: "linear-gradient(135deg, #080c18 0%, #0f1729 50%, #0a1020 100%)",
      borderRadius: 12, overflow: "hidden",
    }}>
      <svg viewBox="0 0 700 420" style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}>
        <defs>
          <filter id="fglow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feComposite in="SourceGraphic" in2="b" operator="over" />
          </filter>
          <filter id="sglow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="10" result="b" />
            <feComposite in="SourceGraphic" in2="b" operator="over" />
          </filter>
          <radialGradient id="rg-healthy" cx="35%" cy="35%">
            <stop offset="0%" stopColor="#6ee7a0" /><stop offset="100%" stopColor="#2ab06f" />
          </radialGradient>
          <radialGradient id="rg-warning" cx="35%" cy="35%">
            <stop offset="0%" stopColor="#fcd06e" /><stop offset="100%" stopColor="#f5a623" />
          </radialGradient>
          <radialGradient id="rg-critical" cx="35%" cy="35%">
            <stop offset="0%" stopColor="#f87171" /><stop offset="100%" stopColor="#dc3545" />
          </radialGradient>
        </defs>

        {/* State outline */}
        <path d={KS_OUTLINE} fill="rgba(25,50,85,0.18)" stroke="rgba(100,160,230,0.22)" strokeWidth="1.5" />
        {/* County grid */}
        {COUNTY_LINES.map((d, i) => <path key={i} d={d} fill="none" stroke="rgba(100,160,230,0.05)" strokeWidth="0.5" />)}

        {/* State label */}
        <text x="200" y="200" fill="rgba(100,150,210,0.08)" fontSize="72" fontWeight="800" fontFamily="system-ui" letterSpacing="16">KANSAS</text>

        {/* Reference cities */}
        {REF_CITIES.map((c) => (
          <g key={c.name}>
            <circle cx={c.x} cy={c.y} r="1.5" fill="rgba(130,170,220,0.3)" />
            <text x={c.x + 5} y={c.y + 3} fill="rgba(130,170,220,0.2)" fontSize="7.5" fontFamily="system-ui">{c.name}</text>
          </g>
        ))}

        {/* Highway hints */}
        <path d="M 62 112 L 648 112" fill="none" stroke="rgba(130,170,220,0.06)" strokeWidth="2.5" />
        <text x="80" y="108" fill="rgba(130,170,220,0.12)" fontSize="7" fontFamily="monospace">I-70</text>
        <path d="M 608 52 Q 500 160 430 370" fill="none" stroke="rgba(130,170,220,0.06)" strokeWidth="2.5" />
        <text x="500" y="180" fill="rgba(130,170,220,0.12)" fontSize="7" fontFamily="monospace">I-35</text>

        {/* Flow paths */}
        {activeFlows.map((flow, i) => {
          const a = geoSites.find((s) => s.code === flow.from);
          const b = geoSites.find((s) => s.code === flow.to);
          if (!a || !b) return null;
          const w = 1.5 + (flow.volume / maxVol) * 4;
          const op = 0.15 + (flow.volume / maxVol) * 0.35;
          const d = curvedPath(a.gx, a.gy, b.gx, b.gy);
          // Midpoint for label
          const dx = b.gx - a.gx, dy = b.gy - a.gy;
          const len = Math.sqrt(dx * dx + dy * dy);
          const off = Math.min(len * 0.18, 45);
          const lx = (a.gx + b.gx) / 2 + (-dy / len) * off;
          const ly = (a.gy + b.gy) / 2 + (dx / len) * off;
          return (
            <g key={i}>
              <path d={d} fill="none" stroke="rgba(91,143,249,0.1)" strokeWidth={w + 6} filter="url(#fglow)" />
              <path d={d} fill="none" stroke={`rgba(91,143,249,${op})`} strokeWidth={w} strokeLinecap="round" />
              <path d={d} fill="none" stroke="rgba(120,170,255,0.5)" strokeWidth={Math.max(1, w - 1)} strokeDasharray="4 14" strokeLinecap="round">
                <animate attributeName="stroke-dashoffset" from="0" to="-18" dur="1.2s" repeatCount="indefinite" />
              </path>
              {flow.label && (
                <g>
                  <rect x={lx - 22} y={ly - 7} width="44" height="14" rx="3" fill="rgba(8,12,24,0.85)" stroke="rgba(91,143,249,0.25)" strokeWidth="0.5" />
                  <text x={lx} y={ly + 3} textAnchor="middle" fill="rgba(160,200,255,0.8)" fontSize="7.5" fontFamily="monospace">{flow.label}</text>
                </g>
              )}
            </g>
          );
        })}

        {/* Site nodes */}
        {geoSites.map((site) => {
          const hs = computeHealthStatus(site.loginRate, 90, 70);
          const col = statusColor(hs);
          const main = site.code === "kcrmc-main";
          const r = main ? 24 : 17;
          return (
            <g key={site.code} onClick={() => onSiteClick?.(site.code)} style={{ cursor: onSiteClick ? "pointer" : "default" }}>
              {/* Double pulse rings */}
              <circle cx={site.gx} cy={site.gy} r={r} fill="none" stroke={col} opacity="0">
                <animate attributeName="r" from={r + 2} to={r + 22} dur="3s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.5" to="0" dur="3s" repeatCount="indefinite" />
              </circle>
              <circle cx={site.gx} cy={site.gy} r={r} fill="none" stroke={col} opacity="0">
                <animate attributeName="r" from={r + 2} to={r + 22} dur="3s" begin="1.5s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.3" to="0" dur="3s" begin="1.5s" repeatCount="indefinite" />
              </circle>
              {/* Glow */}
              <circle cx={site.gx} cy={site.gy} r={r + 8} fill={col} opacity="0.1" filter="url(#sglow)" />
              {/* Main disc */}
              <circle cx={site.gx} cy={site.gy} r={r} fill={`url(#rg-${hs})`} opacity="0.92" />
              <circle cx={site.gx} cy={site.gy} r={r - 3} fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
              {/* Center number */}
              <text x={site.gx} y={site.gy + 1} textAnchor="middle" dominantBaseline="middle" fill="#fff" fontSize={main ? "12" : "10"} fontWeight="700" fontFamily="monospace">
                {site.devices ?? site.events}
              </text>
              {/* Label card */}
              <rect x={site.gx - (main ? 62 : 48)} y={site.gy + r + 6} width={main ? 124 : 96} height={main ? 42 : 36} rx="5" fill="rgba(8,12,24,0.88)" stroke={`rgba(${hs === "healthy" ? "42,176,111" : hs === "warning" ? "245,166,35" : "220,53,69"},0.25)`} strokeWidth="0.5" />
              <text x={site.gx} y={site.gy + r + 20} textAnchor="middle" fill="#e2e8f0" fontSize={main ? "11" : "9.5"} fontWeight="600">{site.label}</text>
              <text x={site.gx} y={site.gy + r + (main ? 36 : 32)} textAnchor="middle" fill="rgba(160,200,255,0.55)" fontSize="8" fontFamily="monospace">
                {site.loginRate.toFixed(0)}% login · {site.users}u · {site.events}ev
              </text>
            </g>
          );
        })}

        {/* Legend */}
        <g transform="translate(70, 338)">
          <rect x="0" y="0" width="205" height="26" rx="5" fill="rgba(8,12,24,0.8)" stroke="rgba(91,143,249,0.15)" strokeWidth="0.5" />
          <circle cx="16" cy="13" r="4" fill="#2ab06f" />
          <text x="26" y="16" fill="rgba(160,200,255,0.6)" fontSize="8">Healthy</text>
          <circle cx="72" cy="13" r="4" fill="#f5a623" />
          <text x="82" y="16" fill="rgba(160,200,255,0.6)" fontSize="8">Warning</text>
          <circle cx="128" cy="13" r="4" fill="#dc3545" />
          <text x="138" y="16" fill="rgba(160,200,255,0.6)" fontSize="8">Critical</text>
          <line x1="168" y1="5" x2="168" y2="21" stroke="rgba(91,143,249,0.2)" strokeWidth="0.5" />
          <line x1="174" y1="13" x2="188" y2="13" stroke="rgba(120,170,255,0.5)" strokeWidth="1.5" strokeDasharray="3 4">
            <animate attributeName="stroke-dashoffset" from="0" to="-7" dur="1s" repeatCount="indefinite" />
          </line>
          <text x="193" y="16" fill="rgba(160,200,255,0.6)" fontSize="7">Flow</text>
        </g>
      </svg>

      {/* Canvas particle overlay */}
      <canvas ref={canvasRef} style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }} />
    </div>
  );
};
