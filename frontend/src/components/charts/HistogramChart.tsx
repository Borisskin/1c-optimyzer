// Histogram = BarChart с явной шкалой bucket'ов. Отличие от BarChart:
// принимает массив {bucket_label, count}; опциональный logarithmic Y axis
// (для duration distribution).

import {
  Bar,
  CartesianGrid,
  BarChart as ReBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AXIS_TICK_STYLE, CHART_COLORS } from "./chartTheme";
import { ChartShell } from "./ChartShell";
import { ChartTooltip } from "./ChartTooltip";

export interface HistogramBucket {
  label: string;
  count: number;
  percent?: number;
}

export interface HistogramChartProps {
  data: HistogramBucket[];
  height?: number;
  logScale?: boolean;
  isLoading?: boolean;
  error?: string | null;
  emptyMessage?: string;
}

export function HistogramChart({
  data,
  height = 260,
  logScale = false,
  isLoading,
  error,
  emptyMessage,
}: HistogramChartProps) {
  return (
    <ChartShell
      isLoading={isLoading}
      hasData={data.length > 0}
      error={error}
      emptyMessage={emptyMessage}
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ReBarChart data={data} margin={{ top: 12, right: 16, bottom: 28, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis
            dataKey="label"
            tick={AXIS_TICK_STYLE}
            axisLine={{ stroke: CHART_COLORS.grid }}
            tickLine={false}
            angle={-20}
            textAnchor="end"
            height={48}
          />
          <YAxis
            tick={AXIS_TICK_STYLE}
            axisLine={{ stroke: CHART_COLORS.grid }}
            tickLine={false}
            scale={logScale ? "log" : "linear"}
            allowDataOverflow={logScale}
            domain={logScale ? [1, "dataMax"] : ["auto", "auto"]}
          />
          <Tooltip
            content={
              <ChartTooltip
                formatValue={(v) => (typeof v === "number" ? v.toLocaleString("ru-RU") : String(v))}
              />
            }
            cursor={{ fill: "rgba(15,118,110,0.06)" }}
          />
          <Bar dataKey="count" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
        </ReBarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
