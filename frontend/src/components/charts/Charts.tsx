// Простые SVG-based charts (Spark, MiniBars, Donut, LineChart, Heatmap).
// Без сторонних chart-библиотек — портировано из design/opt/shared.jsx.

import type { ReactNode } from "react";

const TEAL = "#0F766E";

export function Spark({
  data,
  w = 120,
  h = 28,
  color = TEAL,
  area = true,
  strokeW = 1.4,
}: {
  data: number[];
  w?: number;
  h?: number;
  color?: string;
  area?: boolean;
  strokeW?: number;
}) {
  if (data.length === 0) return <svg width={w} height={h} />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1 || 1)) * (w - 2) + 1;
    const y = h - 2 - ((v - min) / range) * (h - 4);
    return [x, y] as const;
  });
  const path = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const areaPath = path + ` L${(w - 1).toFixed(1)} ${h - 1} L1 ${h - 1} Z`;
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      {area && <path d={areaPath} fill={color} opacity={0.08} />}
      <path d={path} fill="none" stroke={color} strokeWidth={strokeW} />
    </svg>
  );
}

export function MiniBars({
  data,
  w = 120,
  h = 28,
  color = TEAL,
}: {
  data: number[];
  w?: number;
  h?: number;
  color?: string;
}) {
  const max = Math.max(...data) || 1;
  const bw = (w - (data.length - 1)) / data.length;
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      {data.map((v, i) => {
        const bh = (v / max) * (h - 2);
        return (
          <rect
            key={i}
            x={i * (bw + 1)}
            y={h - bh}
            width={bw}
            height={bh}
            fill={color}
            opacity={0.85}
          />
        );
      })}
    </svg>
  );
}

export function Donut({
  pct = 75,
  size = 44,
  stroke = 5,
  color = TEAL,
  track = "var(--o-border)",
}: {
  pct?: number;
  size?: number;
  stroke?: number;
  color?: string;
  track?: string;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size}>
      <circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none" />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        stroke={color}
        strokeWidth={stroke}
        fill="none"
        strokeDasharray={`${(pct / 100) * c} ${c}`}
        strokeDashoffset={c * 0.25}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
    </svg>
  );
}

export interface LinePoint {
  t: number;
  v: number;
}

export interface LineSeries {
  data: LinePoint[];
  name?: string;
  color?: string;
}

export function LineChart({
  series,
  w = 600,
  h = 180,
  yLabel,
  color = TEAL,
  baseline,
  target,
}: {
  series: LineSeries[];
  w?: number;
  h?: number;
  yLabel?: ReactNode;
  color?: string;
  baseline?: number;
  target?: number;
}) {
  const all = series.flatMap((s) => s.data.map((d) => d.v));
  const min = Math.min(...all, baseline ?? Infinity, target ?? Infinity);
  const max = Math.max(...all, baseline ?? -Infinity, target ?? -Infinity);
  const range = max - min || 1;
  const px = 38;
  const py = 14;
  const pb = 20;
  const W = w - px - 8;
  const H = h - py - pb;
  const xAt = (i: number, n: number) => px + (i / (n - 1 || 1)) * W;
  const yAt = (v: number) => py + H - ((v - min) / range) * H;
  const grid = [0, 0.25, 0.5, 0.75, 1].map((t) => min + t * range);
  return (
    <svg width={w} height={h}>
      {grid.map((g, i) => (
        <g key={i}>
          <line x1={px} x2={px + W} y1={yAt(g)} y2={yAt(g)} stroke="var(--o-hover)" />
          <text
            x={px - 6}
            y={yAt(g) + 3}
            fontSize="10"
            textAnchor="end"
            fill="var(--o-text-3)"
            fontFamily="var(--o-font-mono)"
          >
            {g.toFixed(2)}
          </text>
        </g>
      ))}
      {target != null && (
        <line
          x1={px}
          x2={px + W}
          y1={yAt(target)}
          y2={yAt(target)}
          stroke="var(--o-ok)"
          strokeDasharray="3 3"
        />
      )}
      {baseline != null && (
        <line
          x1={px}
          x2={px + W}
          y1={yAt(baseline)}
          y2={yAt(baseline)}
          stroke="var(--o-text-3)"
          strokeDasharray="2 4"
        />
      )}
      {series.map((s, si) => {
        const path = s.data
          .map((d, i) => (i ? "L" : "M") + xAt(i, s.data.length).toFixed(1) + " " + yAt(d.v).toFixed(1))
          .join(" ");
        return <path key={si} d={path} fill="none" stroke={s.color || color} strokeWidth="1.5" />;
      })}
    </svg>
  );
}

export function Heatmap({
  data,
  w = 720,
  h = 160,
}: {
  data: number[][];
  w?: number;
  h?: number;
}) {
  const days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
  const cw = (w - 32) / 24;
  const ch = (h - 18) / 7;
  const col = (v: number) => {
    if (v < 0.33) return "#F0FDF4";
    if (v < 0.55) return "#DCFCE7";
    if (v < 0.7) return "#FEF3C7";
    if (v < 0.85) return "#FECACA";
    return "#FCA5A5";
  };
  return (
    <svg width={w} height={h}>
      {days.map((d, i) => (
        <text
          key={d}
          x={4}
          y={18 + i * ch + ch / 2 + 4}
          fontSize="10"
          fill="var(--o-text-4)"
          fontFamily="var(--o-font-mono)"
        >
          {d}
        </text>
      ))}
      {Array.from({ length: 24 }).map((_, h2) =>
        h2 % 3 === 0 ? (
          <text
            key={h2}
            x={32 + h2 * cw + 2}
            y={12}
            fontSize="10"
            fill="var(--o-text-3)"
            fontFamily="var(--o-font-mono)"
          >
            {String(h2).padStart(2, "0")}
          </text>
        ) : null,
      )}
      {data.map((row, ri) =>
        row.map((v, ci) => (
          <rect
            key={`${ri}-${ci}`}
            x={32 + ci * cw + 1}
            y={18 + ri * ch + 1}
            width={cw - 2}
            height={ch - 2}
            fill={col(v)}
          />
        )),
      )}
    </svg>
  );
}
