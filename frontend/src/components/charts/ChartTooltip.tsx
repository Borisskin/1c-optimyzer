// Кастомный tooltip с design-system стилем.
// Recharts 3.x не экспортирует стабильный props type для custom content —
// принимаем "any-shaped" payload, нам нужны label + payload[]; формат
// устаканенный с Recharts 2.x.

import { CHART_COLORS, CHART_FONT } from "./chartTheme";

interface CTProps {
  active?: boolean;
  label?: string | number;
  payload?: Array<{
    name?: string | number;
    value?: string | number;
    color?: string;
    dataKey?: string;
  }>;
  formatValue?: (value: number | string) => string;
  unit?: string;
}

export function ChartTooltip({ active, label, payload, formatValue, unit }: CTProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div
      style={{
        background: CHART_COLORS.panel,
        border: `1px solid ${CHART_COLORS.grid}`,
        borderRadius: 4,
        padding: "8px 10px",
        fontSize: 11.5,
        boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
      }}
    >
      {label != null && (
        <div
          style={{
            color: CHART_COLORS.text1,
            fontFamily: CHART_FONT.mono,
            marginBottom: 4,
            fontWeight: 500,
          }}
        >
          {String(label)}
        </div>
      )}
      {payload.map((p, i) => {
        const raw = p.value;
        const formatted = raw != null ? (formatValue ? formatValue(raw) : String(raw)) : "—";
        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              color: CHART_COLORS.text2,
              fontFamily: CHART_FONT.mono,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: 2,
                background: p.color ?? CHART_COLORS.primary,
                flex: "0 0 8px",
              }}
            />
            <span style={{ color: CHART_COLORS.text2 }}>{p.name ?? "value"}</span>
            <span style={{ marginLeft: "auto", color: CHART_COLORS.text1, fontWeight: 500 }}>
              {formatted}
              {unit ? ` ${unit}` : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}
