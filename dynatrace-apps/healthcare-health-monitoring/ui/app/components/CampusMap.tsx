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

/* -- Equirectangular projection for Kansas -- */
const KS_WEST = -102.05;
const KS_EAST = -94.59;
const KS_NORTH = 40.003;
const KS_SOUTH = 36.993;

const VB_W = 700;
const VB_H = 420;
const PAD_X = 40;
const PAD_Y = 30;
const CW = VB_W - 2 * PAD_X;
const CH = VB_H - 2 * PAD_Y;

function lonToX(lon: number) {
  return ((lon - KS_WEST) / (KS_EAST - KS_WEST)) * CW + PAD_X;
}
function latToY(lat: number) {
  return ((KS_NORTH - lat) / (KS_NORTH - KS_SOUTH)) * CH + PAD_Y;
}
function geoToSvg(lat: number, lon: number) {
  return { gx: Math.round(lonToX(lon)), gy: Math.round(latToY(lat)) };
}

/* -- Site positions from real lat/lon -- */
// Hub at Lawrence, KS (Douglas County) — central-east Kansas along I-70
const SITE_GEO: Record<string, { gx: number; gy: number }> = {
  "kcrmc-main": geoToSvg(38.9717, -95.2353),   // Lawrence KS (Douglas County)
  "oak-clinic": geoToSvg(39.1333, -100.8528),   // Oakley KS
  "bel-clinic": geoToSvg(39.8258, -97.6322),    // Belleville KS
  "wel-clinic": geoToSvg(37.2650, -97.3714),    // Wellington KS
};

/* -- Reference cities from real lat/lon -- */
const REF_CITIES = [
  { name: "Wichita", ...geoToSvg(37.6872, -97.3301) },
  { name: "Topeka", ...geoToSvg(39.0489, -95.6780) },
  { name: "Dodge City", ...geoToSvg(37.7528, -100.0171) },
  { name: "Salina", ...geoToSvg(38.8403, -97.6114) },
  { name: "Manhattan", ...geoToSvg(39.1836, -96.5717) },
  { name: "Emporia", ...geoToSvg(38.4039, -96.1817) },
  { name: "Hays", ...geoToSvg(38.8791, -99.3268) },
  { name: "Garden City", ...geoToSvg(37.9717, -100.8727) },
  { name: "Hutchinson", ...geoToSvg(38.0608, -97.9298) },
  { name: "Pittsburg", ...geoToSvg(37.4109, -94.7049) },
  { name: "Liberal", ...geoToSvg(37.0439, -100.9209) },
  { name: "Colby", ...geoToSvg(39.3958, -101.0529) },
];

/* -- Kansas outline - simplified real boundary with NE Missouri River notch -- */
const ksOutline = (() => {
  const pts: [number, number][] = [
    [KS_SOUTH, KS_WEST],
    [KS_NORTH, KS_WEST],
    [KS_NORTH, -95.31],
    [39.90, -95.07],
    [39.76, -94.88],
    [39.60, -94.71],
    [39.20, -94.61],
    [KS_SOUTH, -94.61],
  ];
  return "M " + pts.map(([lat, lon]) => `${lonToX(lon).toFixed(1)} ${latToY(lat).toFixed(1)}`).join(" L ") + " Z";
})();

/* -- Highways (real routes) -- */
const I70 = (() => {
  const pts: [number, number][] = [
    [39.05, KS_WEST], [39.07, -99.33], [38.84, -97.61],
    [39.05, -96.57], [39.05, -95.68], [39.10, -94.63],
  ];
  return "M " + pts.map(([lat, lon]) => `${lonToX(lon).toFixed(1)} ${latToY(lat).toFixed(1)}`).join(" L ");
})();

const I35 = (() => {
  const pts: [number, number][] = [
    [39.10, -94.63], [38.96, -95.68], [38.40, -96.18],
    [37.69, -97.33], [37.27, -97.37], [KS_SOUTH, -97.40],
  ];
  return "M " + pts.map(([lat, lon]) => `${lonToX(lon).toFixed(1)} ${latToY(lat).toFixed(1)}`).join(" L ");
})();

/* -- County grid -- */
const COUNTY_H = [39.5, 39.0, 38.5, 38.0, 37.5].map(latToY);
const COUNTY_V = [-101, -100, -99, -98, -97, -96, -95].map(lonToX);

export const CampusMap = ({ sites, flows = [], onSiteClick }: CampusMapProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const geoSites = useMemo(() => {
    const mapped = sites.map((s) => ({ ...s, ...(SITE_GEO[s.code] ?? { gx: s.x, gy: s.y }) }));
    // Ensure hub is always present so flow lines always have an origin
    if (!mapped.find((s) => s.code === "kcrmc-main") && SITE_GEO["kcrmc-main"]) {
      mapped.push({
        code: "kcrmc-main", name: "Lawrence Regional Medical Center", label: "Lawrence Main Campus",
        x: 0, y: 0, events: 0, loginRate: 100, users: 0,
        ...SITE_GEO["kcrmc-main"],
      });
    }
    return mapped;
  }, [sites]);

  // Only show real netflow data — no fake/synthetic flows
  const activeFlows = useMemo(() => flows, [flows]);

  const maxVol = Math.max(1, ...activeFlows.map((f) => f.volume));

  // Canvas particle animation - straight lines
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || activeFlows.length === 0 || geoSites.length < 2) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    // Match SVG's preserveAspectRatio="xMidYMid meet" — uniform scale + centering
    const uniformScale = Math.min(rect.width / VB_W, rect.height / VB_H);
    const offsetX = (rect.width - VB_W * uniformScale) / 2;
    const offsetY = (rect.height - VB_H * uniformScale) / 2;
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    ctx.scale(2, 2);

    interface P { fi: number; t: number; speed: number; sz: number; }
    const ps: P[] = [];
    activeFlows.forEach((flow, fi) => {
      const n = Math.max(3, Math.round((flow.volume / maxVol) * 8));
      for (let i = 0; i < n; i++)
        ps.push({ fi, t: Math.random(), speed: 0.002 + Math.random() * 0.003, sz: 1.2 + (flow.volume / maxVol) * 2.5 });
    });

    let raf: number;
    const draw = () => {
      ctx.clearRect(0, 0, rect.width, rect.height);
      for (const p of ps) {
        const fl = activeFlows[p.fi];
        const a = geoSites.find((s) => s.code === fl.from);
        const b = geoSites.find((s) => s.code === fl.to);
        if (!a || !b) continue;
        const x1 = a.gx * uniformScale + offsetX, y1 = a.gy * uniformScale + offsetY;
        const x2 = b.gx * uniformScale + offsetX, y2 = b.gy * uniformScale + offsetY;
        const px = x1 + (x2 - x1) * p.t;
        const py = y1 + (y2 - y1) * p.t;
        ctx.beginPath();
        ctx.arc(px, py, p.sz * 3.5, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(91,143,249,0.12)";
        ctx.fill();
        ctx.beginPath();
        ctx.arc(px, py, p.sz, 0, Math.PI * 2);
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
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}>
        <defs>
          <filter id="fglow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feComposite in="SourceGraphic" in2="b" operator="over" />
          </filter>
          <filter id="sglow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="12" result="b" />
            <feComposite in="SourceGraphic" in2="b" operator="over" />
          </filter>
        </defs>

        {/* Kansas outline */}
        <path d={ksOutline} fill="rgba(25,50,85,0.18)" stroke="rgba(100,160,230,0.22)" strokeWidth="1.5" />

        {/* County grid */}
        {COUNTY_H.map((y, i) => (
          <line key={`h${i}`} x1={PAD_X} y1={y} x2={VB_W - PAD_X} y2={y} stroke="rgba(100,160,230,0.05)" strokeWidth="0.5" />
        ))}
        {COUNTY_V.map((x, i) => (
          <line key={`v${i}`} x1={x} y1={PAD_Y} x2={x} y2={VB_H - PAD_Y} stroke="rgba(100,160,230,0.05)" strokeWidth="0.5" />
        ))}

        {/* Background label */}
        <text x={VB_W / 2} y={VB_H / 2 + 10} textAnchor="middle" fill="rgba(100,150,210,0.06)" fontSize="72" fontWeight="800" fontFamily="system-ui" letterSpacing="16">KANSAS</text>

        {/* Highways */}
        <path d={I70} fill="none" stroke="rgba(130,170,220,0.08)" strokeWidth="2.5" />
        <text x={lonToX(-101.3)} y={latToY(39.25)} fill="rgba(130,170,220,0.15)" fontSize="7" fontFamily="monospace">I-70</text>
        <path d={I35} fill="none" stroke="rgba(130,170,220,0.08)" strokeWidth="2.5" />
        <text x={lonToX(-96.5)} y={latToY(38.0)} fill="rgba(130,170,220,0.15)" fontSize="7" fontFamily="monospace">I-35</text>

        {/* Reference cities */}
        {REF_CITIES.map((c) => (
          <g key={c.name}>
            <circle cx={c.gx} cy={c.gy} r="1.5" fill="rgba(130,170,220,0.3)" />
            <text x={c.gx + 5} y={c.gy + 3} fill="rgba(130,170,220,0.2)" fontSize="7.5" fontFamily="system-ui">{c.name}</text>
          </g>
        ))}

        {/* Flow paths - straight lines */}
        {activeFlows.map((flow, i) => {
          const a = geoSites.find((s) => s.code === flow.from);
          const b = geoSites.find((s) => s.code === flow.to);
          if (!a || !b) return null;
          const w = 1.5 + (flow.volume / maxVol) * 4;
          const op = 0.15 + (flow.volume / maxVol) * 0.35;
          const lx = (a.gx + b.gx) / 2;
          const ly = (a.gy + b.gy) / 2;
          return (
            <g key={i}>
              <line x1={a.gx} y1={a.gy} x2={b.gx} y2={b.gy}
                stroke="rgba(91,143,249,0.1)" strokeWidth={w + 6} filter="url(#fglow)" />
              <line x1={a.gx} y1={a.gy} x2={b.gx} y2={b.gy}
                stroke={`rgba(91,143,249,${op})`} strokeWidth={w} strokeLinecap="round" />
              <line x1={a.gx} y1={a.gy} x2={b.gx} y2={b.gy}
                stroke="rgba(120,170,255,0.5)" strokeWidth={Math.max(1, w - 1)}
                strokeDasharray="4 14" strokeLinecap="round">
                <animate attributeName="stroke-dashoffset" from="0" to="-18" dur="1.2s" repeatCount="indefinite" />
              </line>
              {flow.label && (
                <g>
                  <rect x={lx - 32} y={ly - 9} width="64" height="17" rx="3"
                    fill="rgba(8,12,24,0.9)" stroke="rgba(91,143,249,0.25)" strokeWidth="0.5" />
                  <text x={lx} y={ly + 4} textAnchor="middle"
                    fill="rgba(160,200,255,0.85)" fontSize="8" fontFamily="monospace">{flow.label}</text>
                </g>
              )}
            </g>
          );
        })}

        {/* Site nodes - Hospital icons */}
        {geoSites.map((site) => {
          const hs = computeHealthStatus(site.loginRate, 90, 70);
          const col = statusColor(hs);
          const isMain = site.code === "kcrmc-main";
          const scale = isMain ? 1.8 : 1.3;

          return (
            <g key={site.code} onClick={() => onSiteClick?.(site.code)} style={{ cursor: onSiteClick ? "pointer" : "default" }}>
              {/* Pulse rings */}
              <circle cx={site.gx} cy={site.gy} r="20" fill="none" stroke={col} opacity="0">
                <animate attributeName="r" from="16" to="38" dur="3s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.45" to="0" dur="3s" repeatCount="indefinite" />
              </circle>
              <circle cx={site.gx} cy={site.gy} r="20" fill="none" stroke={col} opacity="0">
                <animate attributeName="r" from="16" to="38" dur="3s" begin="1.5s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.25" to="0" dur="3s" begin="1.5s" repeatCount="indefinite" />
              </circle>

              {/* Glow backdrop */}
              <circle cx={site.gx} cy={site.gy} r={18 * scale} fill={col} opacity="0.08" filter="url(#sglow)" />

              {/* Hospital building icon */}
              <g transform={`translate(${site.gx}, ${site.gy}) scale(${scale})`}>
                <rect x="-12" y="-8" width="24" height="20" rx="2" fill="rgba(20,30,50,0.9)" stroke={col} strokeWidth="1.2" />
                <rect x="-12" y="-8" width="24" height="3" rx="1" fill={col} opacity="0.7" />
                <rect x="-1.5" y="-4" width="3" height="10" rx="0.5" fill="#fff" opacity="0.9" />
                <rect x="-5" y="-0.5" width="10" height="3" rx="0.5" fill="#fff" opacity="0.9" />
                <rect x="-2.5" y="6" width="5" height="6" rx="1" fill={col} opacity="0.5" />
                <rect x="-9" y="0" width="3" height="3" rx="0.5" fill="rgba(120,170,255,0.4)" />
                <rect x="6" y="0" width="3" height="3" rx="0.5" fill="rgba(120,170,255,0.4)" />
                <rect x="-9" y="5" width="3" height="3" rx="0.5" fill="rgba(120,170,255,0.3)" />
                <rect x="6" y="5" width="3" height="3" rx="0.5" fill="rgba(120,170,255,0.3)" />
              </g>

              {/* Status indicator dot */}
              <circle cx={site.gx + 14 * scale} cy={site.gy - 10 * scale} r="5" fill={col} stroke="rgba(8,12,24,0.9)" strokeWidth="1.5" />

              {/* Label card */}
              <rect
                x={site.gx - (isMain ? 66 : 52)}
                y={site.gy + 16 * scale + 4}
                width={isMain ? 132 : 104}
                height={isMain ? 44 : 38}
                rx="5"
                fill="rgba(8,12,24,0.9)"
                stroke={`rgba(${hs === "healthy" ? "42,176,111" : hs === "warning" ? "245,166,35" : "220,53,69"},0.3)`}
                strokeWidth="0.5"
              />
              <text
                x={site.gx}
                y={site.gy + 16 * scale + 18}
                textAnchor="middle"
                fill="#e2e8f0"
                fontSize={isMain ? "11" : "9.5"}
                fontWeight="600"
              >
                {site.label}
              </text>
              <text
                x={site.gx}
                y={site.gy + 16 * scale + (isMain ? 34 : 32)}
                textAnchor="middle"
                fill="rgba(160,200,255,0.55)"
                fontSize="8"
                fontFamily="monospace"
              >
                {site.loginRate.toFixed(0)}% {'\u00B7'} {site.users}u {'\u00B7'} {site.events}ev
              </text>
            </g>
          );
        })}

        {/* Legend */}
        <g transform={`translate(${PAD_X + 30}, ${VB_H - PAD_Y - 32})`}>
          <rect x="0" y="0" width="230" height="26" rx="5" fill="rgba(8,12,24,0.8)" stroke="rgba(91,143,249,0.15)" strokeWidth="0.5" />
          <g transform="translate(14, 13) scale(0.45)">
            <rect x="-12" y="-8" width="24" height="20" rx="2" fill="rgba(20,30,50,0.9)" stroke="#2ab06f" strokeWidth="1.5" />
            <rect x="-1.5" y="-4" width="3" height="10" rx="0.5" fill="#fff" />
            <rect x="-5" y="-0.5" width="10" height="3" rx="0.5" fill="#fff" />
          </g>
          <text x="28" y="16" fill="rgba(160,200,255,0.6)" fontSize="8">Hospital</text>
          <circle cx="76" cy="13" r="4" fill="#2ab06f" /><text x="84" y="16" fill="rgba(160,200,255,0.6)" fontSize="8">Healthy</text>
          <circle cx="122" cy="13" r="4" fill="#f5a623" /><text x="130" y="16" fill="rgba(160,200,255,0.6)" fontSize="8">Warning</text>
          <circle cx="170" cy="13" r="4" fill="#dc3545" /><text x="178" y="16" fill="rgba(160,200,255,0.6)" fontSize="8">Critical</text>
          <line x1="208" y1="5" x2="208" y2="21" stroke="rgba(91,143,249,0.2)" strokeWidth="0.5" />
          <line x1="212" y1="13" x2="224" y2="13" stroke="rgba(120,170,255,0.5)" strokeWidth="1.5" strokeDasharray="3 4">
            <animate attributeName="stroke-dashoffset" from="0" to="-7" dur="1s" repeatCount="indefinite" />
          </line>
        </g>
      </svg>

      {/* Canvas particle overlay */}
      <canvas ref={canvasRef} style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }} />
    </div>
  );
};
