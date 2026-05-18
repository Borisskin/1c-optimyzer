// Time-series line chart wrapper.
import {
  CartesianGrid,
  Line,
  LineChart as ReLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AXIS_TICK_STYLE, CATEGORICAL_PALETTE, CHART_COLORS } from "./chartTheme";
import { ChartShell } from "./ChartShell";
import { ChartTooltip } from "./ChartTooltip";

export interface LineSeries {
  key: string;
  label?: string;
  color?: string;
}

export interface LineChartProps<T extends Record<string, unknown>> {
  data: T[];
  xKey: keyof T & string;
  series: LineSeries[];
  height?: number;
  unit?: string;
  isLoading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  formatValue?: (v: number | string) => string;
}

export function LineChart<T extends Record<string, unknown>>({
  data,
  xKey,
  series,
  height = 240,
  unit,
  isLoading,
  error,
  emptyMessage,
  formatValue,
}: LineChartProps<T>) {
  return (
    <ChartShell
      isLoading={isLoading}
      hasData={data.length > 0}
      error={error}
      emptyMessage={emptyMessage}
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ReLineChart data={data} margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis dataKey={xKey as string} tick={AXIS_TICK_STYLE} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} />
          <YAxis tick={AXIS_TICK_STYLE} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} />
          <Tooltip content={<ChartTooltip formatValue={formatValue} unit={unit} />} />
          {series.map((s, i) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label ?? s.key}
              stroke={s.color ?? CATEGORICAL_PALETTE[i % CATEGORICAL_PALETTE.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </ReLineChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
