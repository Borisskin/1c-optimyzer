// Scatter plot wrapper. Используется для duration vs ts distribution.
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart as ReScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AXIS_TICK_STYLE, CHART_COLORS } from "./chartTheme";
import { ChartShell } from "./ChartShell";
import { ChartTooltip } from "./ChartTooltip";

export interface ScatterChartProps<T extends Record<string, unknown>> {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  color?: string;
  height?: number;
  unit?: string;
  isLoading?: boolean;
  error?: string | null;
  emptyMessage?: string;
}

export function ScatterChart<T extends Record<string, unknown>>({
  data,
  xKey,
  yKey,
  color = CHART_COLORS.primary,
  height = 260,
  unit,
  isLoading,
  error,
  emptyMessage,
}: ScatterChartProps<T>) {
  return (
    <ChartShell
      isLoading={isLoading}
      hasData={data.length > 0}
      error={error}
      emptyMessage={emptyMessage}
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ReScatterChart margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey={xKey as string} type="category" tick={AXIS_TICK_STYLE} axisLine={{ stroke: CHART_COLORS.grid }} />
          <YAxis dataKey={yKey as string} tick={AXIS_TICK_STYLE} axisLine={{ stroke: CHART_COLORS.grid }} />
          <Tooltip content={<ChartTooltip unit={unit} />} />
          <Scatter data={data} fill={color} />
        </ReScatterChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
