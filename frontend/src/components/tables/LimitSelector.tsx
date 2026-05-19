// LimitSelector — dropdown «Показать N» + индикация «N из M» для view с
// limit (slow_queries / errors_feed / top_business_operations). Размещается
// в panel_head слева, рядом со счётчиком строк.

import type { CSSProperties } from "react";

export const DEFAULT_LIMIT_OPTIONS = [100, 500, 2000, 10000] as const;

interface Props {
  value: number;
  onChange: (n: number) => void;
  /** Сколько фактически загружено (= rows.length после backend LIMIT). */
  loaded: number;
  /** Сколько всего могло бы быть (= COUNT с теми же WHERE). null если backend
   *  не вернул total_rows. */
  total: number | null;
  options?: readonly number[];
  /** Что считать единицей: "событий", "запросов", "операций" — для подписи. */
  unitLabel?: string;
}

export function LimitSelector({
  value,
  onChange,
  loaded,
  total,
  options = DEFAULT_LIMIT_OPTIONS,
  unitLabel,
}: Props) {
  const truncated = total != null && loaded < total;

  return (
    <div style={wrap}>
      <span style={labelStyle}>Показать:</span>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={selectStyle}
        title="Лимит загружаемых строк"
      >
        {options.map((n) => (
          <option key={n} value={n}>
            {n.toLocaleString("ru-RU")}
          </option>
        ))}
      </select>
      <span style={summaryStyle(truncated)}>
        {total != null ? (
          <>
            {loaded.toLocaleString("ru-RU")} из {total.toLocaleString("ru-RU")}
            {unitLabel ? ` ${unitLabel}` : ""}
          </>
        ) : (
          <>{loaded.toLocaleString("ru-RU")}{unitLabel ? ` ${unitLabel}` : ""}</>
        )}
      </span>
    </div>
  );
}

const wrap: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
};

const labelStyle: CSSProperties = {
  fontSize: 10.5,
  color: "var(--o-text-3)",
  letterSpacing: "0.05em",
  textTransform: "uppercase",
};

const selectStyle: CSSProperties = {
  height: 22,
  padding: "0 4px",
  fontSize: 11,
  fontFamily: "var(--o-font-mono)",
  border: "1px solid var(--o-border-2)",
  borderRadius: 3,
  background: "var(--o-panel)",
  color: "var(--o-text-1)",
  cursor: "pointer",
};

function summaryStyle(truncated: boolean): CSSProperties {
  return {
    fontSize: 10.5,
    fontFamily: "var(--o-font-mono)",
    color: truncated ? "var(--o-warn, #B45309)" : "var(--o-text-3)",
  };
}
