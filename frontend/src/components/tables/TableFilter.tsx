import type { CSSProperties } from "react";
import { Icon } from "@/components/icons/Icon";

interface Props {
  value: string;
  onChange: (v: string) => void;
  total: number;
  visible: number;
  placeholder?: string;
}

/** Input для substring-фильтра таблицы.
 *  Размещается в panel_head справа после счётчика строк.
 *  Показывает "X / Y" если фильтр активен (X = visible, Y = total). */
export function TableFilter({ value, onChange, total, visible, placeholder = "Фильтр…" }: Props) {
  const filtered = value.trim().length > 0;
  return (
    <div style={wrap}>
      {filtered && (
        <span style={counterStyle}>
          {visible.toLocaleString("ru-RU")} / {total.toLocaleString("ru-RU")}
        </span>
      )}
      <div style={inputWrap}>
        <Icon name="Search" size={11} color="var(--o-text-3)" />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          style={inputStyle}
        />
        {filtered && (
          <button
            type="button"
            onClick={() => onChange("")}
            style={clearStyle}
            title="Очистить фильтр"
            aria-label="Очистить фильтр"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}

const wrap: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  marginLeft: "auto",
};

const counterStyle: CSSProperties = {
  fontSize: 10.5,
  fontFamily: "var(--o-font-mono)",
  color: "var(--o-text-3)",
};

const inputWrap: CSSProperties = {
  position: "relative",
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  padding: "0 6px 0 8px",
  height: 24,
  border: "1px solid var(--o-border-2)",
  borderRadius: 4,
  background: "var(--o-panel)",
};

const inputStyle: CSSProperties = {
  width: 180,
  border: "none",
  outline: "none",
  background: "transparent",
  fontSize: 11.5,
  color: "var(--o-text-1)",
  fontFamily: "var(--o-font-mono)",
};

const clearStyle: CSSProperties = {
  width: 16,
  height: 16,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  border: "none",
  background: "transparent",
  color: "var(--o-text-3)",
  fontSize: 14,
  lineHeight: 1,
  cursor: "pointer",
  padding: 0,
};
