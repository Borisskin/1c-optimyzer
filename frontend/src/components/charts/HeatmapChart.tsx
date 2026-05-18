// Custom 7x24 SVG heatmap (Recharts не имеет встроенного heatmap).
// Используется в Activity view: ось X = час суток, ось Y = день недели,
// intensity = выбранная метрика (count / duration / errors).

import { useMemo } from "react";
import { ChartShell } from "./ChartShell";
import { CHART_COLORS, CHART_FONT } from "./chartTheme";

export interface HeatmapCell {
  x: number; // 0..23
  y: number; // 0..6 (Monday=0)
  value: number;
}

export interface HeatmapChartProps {
  data: HeatmapCell[];
  height?: number;
  xLabels?: string[];
  yLabels?: string[];
  isLoading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  onCellClick?: (cell: HeatmapCell) => void;
  formatValue?: (v: number) => string;
}

const DEFAULT_X_LABELS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
const DEFAULT_Y_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export function HeatmapChart({
  data,
  height = 260,
  xLabels = DEFAULT_X_LABELS,
  yLabels = DEFAULT_Y_LABELS,
  isLoading,
  error,
  emptyMessage,
  onCellClick,
  formatValue,
}: HeatmapChartProps) {
  const maxValue = useMemo(() => {
    let m = 0;
    for (const c of data) if (c.value > m) m = c.value;
    return m;
  }, [data]);

  const grid = useMemo(() => {
    const map = new Map<string, HeatmapCell>();
    for (const c of data) map.set(`${c.x}:${c.y}`, c);
    return map;
  }, [data]);

  const cols = xLabels.length;
  const rows = yLabels.length;

  // Inline SVG sizing — будет scaled через ResponsiveContainer parent CSS.
  // Берём cell aspect ratio ~ квадрат, ширина зависит от height.
  const padding = { left: 32, top: 16, right: 8, bottom: 24 };
  const cellH = Math.max(14, (height - padding.top - padding.bottom) / rows);
  // Width вычисляется по cellH (square cells), но даём min 18px для читаемости.
  const cellW = Math.max(18, cellH);
  const svgW = padding.left + cellW * cols + padding.right;
  const svgH = padding.top + cellH * rows + padding.bottom;

  function colorFor(value: number): string {
    if (maxValue === 0) return CHART_COLORS.grid;
    const t = value / maxValue;
    // Интерполяция между панелью и primary teal.
    // Simple HSL approximation: light teal -> dark teal.
    const r = Math.round(255 - (255 - 15) * t);
    const g = Math.round(255 - (255 - 118) * t);
    const b = Math.round(255 - (255 - 110) * t);
    return `rgb(${r},${g},${b})`;
  }

  return (
    <ChartShell
      isLoading={isLoading}
      hasData={data.length > 0}
      error={error}
      emptyMessage={emptyMessage}
      height={height}
    >
      <svg width="100%" height="100%" viewBox={`0 0 ${svgW} ${svgH}`} preserveAspectRatio="xMidYMid meet">
        {/* y-axis labels */}
        {yLabels.map((label, yi) => (
          <text
            key={`y${yi}`}
            x={padding.left - 6}
            y={padding.top + cellH * yi + cellH / 2 + 4}
            textAnchor="end"
            fontFamily={CHART_FONT.axis}
            fontSize={10.5}
            fill={CHART_COLORS.text2}
          >
            {label}
          </text>
        ))}
        {/* x-axis labels (каждый второй для читаемости при тонких клетках) */}
        {xLabels.map((label, xi) =>
          xi % 2 === 0 ? (
            <text
              key={`x${xi}`}
              x={padding.left + cellW * xi + cellW / 2}
              y={svgH - padding.bottom + 14}
              textAnchor="middle"
              fontFamily={CHART_FONT.mono}
              fontSize={10}
              fill={CHART_COLORS.text2}
            >
              {label}
            </text>
          ) : null,
        )}
        {/* cells */}
        {Array.from({ length: rows * cols }, (_, idx) => {
          const x = idx % cols;
          const y = Math.floor(idx / cols);
          const cell = grid.get(`${x}:${y}`) ?? { x, y, value: 0 };
          const fill = colorFor(cell.value);
          return (
            <rect
              key={`c${x}-${y}`}
              x={padding.left + cellW * x + 1}
              y={padding.top + cellH * y + 1}
              width={cellW - 2}
              height={cellH - 2}
              fill={fill}
              stroke={CHART_COLORS.grid}
              strokeWidth={0.5}
              rx={2}
              ry={2}
              cursor={onCellClick ? "pointer" : undefined}
              onClick={onCellClick ? () => onCellClick(cell) : undefined}
            >
              <title>{`${yLabels[y]} ${xLabels[x]}:00 · ${
                formatValue ? formatValue(cell.value) : cell.value.toLocaleString("ru-RU")
              }`}</title>
            </rect>
          );
        })}
      </svg>
    </ChartShell>
  );
}
