// Vertical bar chart wrapper над Recharts.
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

export interface BarChartProps<T extends Record<string, unknown>> {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  color?: string;
  height?: number;
  unit?: string;
  isLoading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  formatValue?: (v: number | string) => string;
}

export function BarChart<T extends Record<string, unknown>>({
  data,
  xKey,
  yKey,
  color = CHART_COLORS.primary,
  height = 240,
  unit,
  isLoading,
  error,
  emptyMessage,
  formatValue,
}: BarChartProps<T>) {
  return (
    <ChartShell
      isLoading={isLoading}
      hasData={data.length > 0}
      error={error}
      emptyMessage={emptyMessage}
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ReBarChart data={data} margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis dataKey={xKey as string} tick={AXIS_TICK_STYLE} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} />
          <YAxis tick={AXIS_TICK_STYLE} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} />
          <Tooltip content={<ChartTooltip formatValue={formatValue} unit={unit} />} cursor={{ fill: "rgba(15,118,110,0.06)" }} />
          <Bar dataKey={yKey as string} fill={color} radius={[4, 4, 0, 0]} />
        </ReBarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
