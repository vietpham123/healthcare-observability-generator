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

const KS_OUTLINE = "M 62 52 L 640 52 L 640 60 L 648 60 L 648 72 L 640 72 L 640 370 L 62 370 Z";

const COUNTY_LINES = [
  "M 62 132 L 640 132", "M 62 212 L 640 212", "M 62 292 L 640 292",
  "M 158 52 L 158 370", "M 254 52 L 254 370", "M 350 52 L 350 370",
  "M 446 52 L 446 370", "M 542 52 L 542 370",
];

// Kansas sites spread geographically: KC east, Oakley far west, Belleville north, Wellington south
const SITE_GEO: Record<string, { gx: number; gy: number }> = {
  "kcrmc-main": { gx: 610, gy: 112 },
  "oak-clinic": { gx: 155, gy: 108 },
  "bel-clinic": { gx: 410, gy: 72 },
  "wel-clinic": { gx: 390, gy: 310 },
};

const REF_CITIES = [
  { name: "Dodge City", x: 210, y: 255 },
  { name: "Salina", x: 350, y: 150 },
  { name: "Manhattan", x: 430, y: 98 },
  { name: "Emporia", x: 490, y: 210 },
  { name: "Hays", x: 278, y: 132 },
  { name: "Garden City", x: 158, y: 230 },
  { name: "Hutchinson", x: 370, y: 225 },
  { name: "Pittsburg", x: 610, y: 310 },
  { name: "Liberal", x: 165, y: 340 },
  { name: "Colby", x: 145, y: 75 },
];

// Hospital cross icon path centered at (0,0), size ~1 unit
// A classic medical cross (plus sign with rounded ends)
const HOSPITAL_CROSS = "M -4 -10 L 4 -10 L 4 -4 L 10 -4 L 10 4 L 4 4 L 4 10 L -4 10 L -4 4 L -10 4 L -10 -4 L -4 -4 Z";

function curvedPath(x1: number, y1: number, x2: number, y2: number): string {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  const offset = Math.min(len * 0.1, 22);
  // Perpendicular offset
  let px = -dy / len, py = dx / len;
  // Always bow toward vertical center of state (~y=210) so curves stay interior
  const midY = (y1 + y2) / 2;
  if ((midY + py * offset) < 210 && py < 0) { px = -px; py = -py; }
  if ((midY + py * offset) > 210 && py > 0 && midY > 210) { px = -px; py = -py; }
  let mx = (x1 + x2) / 2 + px * offset;
  let my = (y1 + y2) / 2 + py * offset;
  // Clamp control point inside the state outline
  mx = Math.max(75, Math.min(635, mx));
  my = Math.max(60, Math.min(360, my));
  return `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
}

function bezierAt(x1: number, y1: number, cx: number, cy: number, x2: number, y2: number, t: number) {
  const mt = 1 - t;
  return {
    x: mt * mt * x1 + 2 * mt * t * cx + t * t * x2,
    y: mt * mt * y1 + 2 * mt * t * cy + t * t * y2,
  };
}

export const CampusMap = ({ sites, flows = [], onSiteClick }: CampusMapProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const geoSites = useMemo(
    () => sites.map((s) => ({ ...s, ...(SITE_GEO[s.code] ?? { gx: s.x, gy: s.y }) })),
    [sites],
  );

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
    const sx = rect.width / 700, sy = rect.height / 420;
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    ctx.scale(2, 2);

    interface P { fi: number; t: number; speed: number; sz: number; }
    const ps: P[] = [];
    activeFlows.forEach((flow, fi) => {
      const n = Math.max(3, Math.round((flow.volume / maxVol) * 8));
      for (let i = 0; i < n; i++) ps.push({ fi, t: Math.random(), speed: 0.0015 + Math.random() * 0.003, sz: 1.2 + (flow.volume / maxVol) * 2.5 });
    });

    let raf: number;
    const draw = () => {
      ctx.clearRect(0, 0, rect.width, rect.height);
      for (const p of ps) {
        const fl = activeFlows[p.fi];
        const a = geoSites.find((s) => s.code === fl.from);
        const b = geoSites.find((s) => s.code === fl.to);
        if (!a || !b) continue;
        const x1 = a.gx * sx, y1 = a.gy * sy, x2 = b.gx * sx, y2 = b.gy * sy;
        const dx = x2 - x1, dy = y2 - y1, len = Math.sqrt(dx * dx + dy * dy);
        const off = Math.min(len * 0.1, 22 * sx);
        let px = -dy / len, py = dx / len;
        const midYc = (y1 + y2) / 2;
        const center = 210 * sy;
        if ((midYc + py * off) < center && py < 0) { px = -px; py = -py; }
        if ((midYc + py * off) > center && py > 0 && midYc > center) { px = -px; py = -py; }
        let cx = (x1 + x2) / 2 + px * off, cy = (y1 + y2) / 2 + py * off;
        cx = Math.max(75 * sx, Math.min(635 * sx, cx));
        cy = Math.max(60 * sy, Math.min(360 * sy, cy));
        const pt = bezierAt(x1, y1, cx, cy, x2, y2, p.t);
        ctx.beginPath(); ctx.arc(pt.x, pt.y, p.sz * 3.5, 0, Math.PI * 2); ctx.fillStyle = "rgba(91,143,249,0.12)"; ctx.fill();
        ctx.beginPath(); ctx.arc(pt.x, pt.y, p.sz, 0, Math.PI * 2); ctx.fillStyle = "rgba(120,170,255,0.9)"; ctx.fill();
        p.t += p.speed; if (p.t > 1) p.t = 0;
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
            <feGaussianBlur stdDeviation="3" result="b" /><feComposite in="SourceGraphic" in2="b" operator="over" />
          </filter>
          <filter id="sglow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="12" result="b" /><feComposite in="SourceGraphic" in2="b" operator="over" />
          </filter>
          {/* Hospital icon clip — white cross on colored bg */}
          <clipPath id="crossClip">
            <path d={HOSPITAL_CROSS} />
          </clipPath>
        </defs>

        {/* State outline + county grid */}
        <path d={KS_OUTLINE} fill="rgba(25,50,85,0.18)" stroke="rgba(100,160,230,0.22)" strokeWidth="1.5" />
        {COUNTY_LINES.map((d, i) => <path key={i} d={d} fill="none" stroke="rgba(100,160,230,0.05)" strokeWidth="0.5" />)}
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
        <path d="M 610 52 Q 500 160 380 370" fill="none" stroke="rgba(130,170,220,0.06)" strokeWidth="2.5" />
        <text x="485" y="185" fill="rgba(130,170,220,0.12)" fontSize="7" fontFamily="monospace">I-35</text>

        {/* Flow paths */}
        {activeFlows.map((flow, i) => {
          const a = geoSites.find((s) => s.code === flow.from);
          const b = geoSites.find((s) => s.code === flow.to);
          if (!a || !b) return null;
          const w = 1.5 + (flow.volume / maxVol) * 4;
          const op = 0.15 + (flow.volume / maxVol) * 0.35;
          const d = curvedPath(a.gx, a.gy, b.gx, b.gy);
          const dx = b.gx - a.gx, dy = b.gy - a.gy, len = Math.sqrt(dx * dx + dy * dy);
          const off = Math.min(len * 0.1, 22);
          let px = -dy / len, py = dx / len;
          const midY = (a.gy + b.gy) / 2;
          if ((midY + py * off) < 210 && py < 0) { px = -px; py = -py; }
          if ((midY + py * off) > 210 && py > 0 && midY > 210) { px = -px; py = -py; }
          let lx = (a.gx + b.gx) / 2 + px * off;
          let ly = (a.gy + b.gy) / 2 + py * off;
          lx = Math.max(75, Math.min(635, lx));
          ly = Math.max(60, Math.min(360, ly));
          return (
            <g key={i}>
              <path d={d} fill="none" stroke="rgba(91,143,249,0.1)" strokeWidth={w + 6} filter="url(#fglow)" />
              <path d={d} fill="none" stroke={`rgba(91,143,249,${op})`} strokeWidth={w} strokeLinecap="round" />
              <path d={d} fill="none" stroke="rgba(120,170,255,0.5)" strokeWidth={Math.max(1, w - 1)} strokeDasharray="4 14" strokeLinecap="round">
                <animate attributeName="stroke-dashoffset" from="0" to="-18" dur="1.2s" repeatCount="indefinite" />
              </path>
              {flow.label && (
                <g>
                  <rect x={lx - 30} y={ly - 8} width="60" height="15" rx="3" fill="rgba(8,12,24,0.88)" stroke="rgba(91,143,249,0.25)" strokeWidth="0.5" />
                  <text x={lx} y={ly + 3} textAnchor="middle" fill="rgba(160,200,255,0.8)" fontSize="7.5" fontFamily="monospace">{flow.label}</text>
                </g>
              )}
            </g>
          );
        })}

        {/* Site nodes — Hospital icons */}
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
                {/* Building body */}
                <rect x="-12" y="-8" width="24" height="20" rx="2" fill="rgba(20,30,50,0.9)" stroke={col} strokeWidth="1.2" />
                {/* Roof accent */}
                <rect x="-12" y="-8" width="24" height="3" rx="1" fill={col} opacity="0.7" />
                {/* Cross */}
                <rect x="-1.5" y="-4" width="3" height="10" rx="0.5" fill="#fff" opacity="0.9" />
                <rect x="-5" y="-0.5" width="10" height="3" rx="0.5" fill="#fff" opacity="0.9" />
                {/* Door */}
                <rect x="-2.5" y="6" width="5" height="6" rx="1" fill={col} opacity="0.5" />
                {/* Windows */}
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
                {site.loginRate.toFixed(0)}% · {site.users}u · {site.events}ev
              </text>
            </g>
          );
        })}

        {/* Legend */}
        <g transform="translate(70, 340)">
          <rect x="0" y="0" width="230" height="26" rx="5" fill="rgba(8,12,24,0.8)" stroke="rgba(91,143,249,0.15)" strokeWidth="0.5" />
          {/* Mini hospital icon */}
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
