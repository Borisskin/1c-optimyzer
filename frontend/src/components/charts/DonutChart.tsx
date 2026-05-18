// Donut chart wrapper. Recharts PieChart с innerRadius > 0.
import {
  Cell,
  Legend,
  Pie,
  PieChart as RePieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { CATEGORICAL_PALETTE, CHART_COLORS, CHART_FONT } from "./chartTheme";
import { ChartShell } from "./ChartShell";

export interface DonutSlice {
  label: string;
  value: number;
  color?: string;
}

export interface DonutChartProps {
  data: DonutSlice[];
  height?: number;
  isLoading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  onSliceClick?: (slice: DonutSlice) => void;
}

export function DonutChart({
  data,
  height = 260,
  isLoading,
  error,
  emptyMessage,
  onSliceClick,
}: DonutChartProps) {
  return (
    <ChartShell
      isLoading={isLoading}
      hasData={data.length > 0}
      error={error}
      emptyMessage={emptyMessage}
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RePieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            innerRadius="55%"
            outerRadius="85%"
            paddingAngle={1}
            stroke={CHART_COLORS.panel}
            onClick={(d) => onSliceClick?.(d as unknown as DonutSlice)}
          >
            {data.map((slice, i) => (
              <Cell
                key={i}
                fill={slice.color ?? CATEGORICAL_PALETTE[i % CATEGORICAL_PALETTE.length]}
                cursor={onSliceClick ? "pointer" : undefined}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              fontFamily: CHART_FONT.mono,
              fontSize: 11.5,
              border: `1px solid ${CHART_COLORS.grid}`,
              borderRadius: 4,
              background: CHART_COLORS.panel,
            }}
            formatter={((value: unknown, name: unknown) => [
              typeof value === "number" ? value.toLocaleString("ru-RU") : String(value),
              String(name ?? ""),
            ]) as never}
          />
          <Legend
            wrapperStyle={{
              fontFamily: CHART_FONT.axis,
              fontSize: 11.5,
              color: CHART_COLORS.text2,
            }}
            iconType="circle"
            iconSize={8}
          />
        </RePieChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
