// Multi-select фильтр по enum-колонке, размещается в th таблицы.
// Кликается отдельно от sort-area: stopPropagation в кнопке-воронке и popover
// не дёргают sort заголовка.

import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { Icon } from "@/components/icons/Icon";

interface Props {
  /** Заголовок popover ("Тип события"). */
  label: string;
  /** Все возможные значения колонки (упорядоченные). */
  options: string[];
  /** Текущий выбор. Пустой Set = «все значения». */
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}

export function ColumnFilterPopover({ label, options, selected, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const active = selected.size > 0;

  const toggle = (v: string) => {
    const next = new Set(selected);
    if (next.has(v)) next.delete(v);
    else next.add(v);
    onChange(next);
  };

  const reset = () => onChange(new Set());

  const summary = useMemo(() => {
    if (!active) return "Фильтр";
    const arr = [...selected];
    return `Фильтр: ${arr.join(", ")}`;
  }, [active, selected]);

  return (
    <span ref={ref} style={wrapStyle} onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        onKeyDown={(e) => {
          // Не давать th-роли button перехватить Enter/Space для sort.
          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
        }}
        title={summary}
        aria-label={`Фильтр ${label}`}
        style={btnStyle(active)}
      >
        <Icon name="Filter" size={11} color={active ? "var(--o-accent)" : "var(--o-text-3)"} />
      </button>
      {open && (
        <div style={popStyle} role="dialog" aria-label={label}>
          <div style={popHeader}>
            <span style={popTitle}>{label}</span>
            {active && (
              <button type="button" onClick={reset} style={resetStyle} title="Сбросить фильтр">
                Сбросить
              </button>
            )}
          </div>
          {options.length === 0 ? (
            <div style={emptyStyle}>Нет значений</div>
          ) : (
            <div style={listStyle}>
              {options.map((opt) => (
                <label key={opt} style={rowStyle}>
                  <input
                    type="checkbox"
                    checked={selected.has(opt)}
                    onChange={() => toggle(opt)}
                    style={checkboxStyle}
                  />
                  <span style={valueStyle}>{opt}</span>
                </label>
              ))}
            </div>
          )}
          <div style={popFooter}>
            <span style={hintStyle}>
              {active ? `${selected.size} из ${options.length}` : `все ${options.length}`}
            </span>
          </div>
        </div>
      )}
    </span>
  );
}

const wrapStyle: CSSProperties = {
  position: "relative",
  display: "inline-flex",
  alignItems: "center",
  marginLeft: 4,
};

function btnStyle(active: boolean): CSSProperties {
  return {
    width: 18,
    height: 18,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    border: "none",
    background: active ? "var(--o-subtle)" : "transparent",
    borderRadius: 3,
    cursor: "pointer",
    padding: 0,
  };
}

const popStyle: CSSProperties = {
  position: "absolute",
  top: "calc(100% + 4px)",
  left: 0,
  minWidth: 180,
  background: "var(--o-panel)",
  border: "1px solid var(--o-border)",
  borderRadius: 4,
  boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
  zIndex: 50,
  overflow: "hidden",
};

const popHeader: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "8px 10px 6px",
  borderBottom: "1px solid var(--o-border-2)",
};

const popTitle: CSSProperties = {
  fontSize: 10.5,
  letterSpacing: "0.05em",
  textTransform: "uppercase",
  color: "var(--o-text-3)",
  fontWeight: 600,
};

const resetStyle: CSSProperties = {
  border: "none",
  background: "transparent",
  color: "var(--o-accent)",
  fontSize: 11,
  cursor: "pointer",
  padding: 0,
};

const listStyle: CSSProperties = {
  maxHeight: 240,
  overflowY: "auto",
  padding: "4px 0",
};

const rowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  padding: "5px 10px",
  cursor: "pointer",
  fontSize: 11.5,
  color: "var(--o-text-1)",
};

const checkboxStyle: CSSProperties = {
  margin: 0,
  cursor: "pointer",
};

const valueStyle: CSSProperties = {
  fontFamily: "var(--o-font-mono)",
};

const popFooter: CSSProperties = {
  padding: "6px 10px",
  borderTop: "1px solid var(--o-border-2)",
  fontSize: 10.5,
  color: "var(--o-text-3)",
};

const hintStyle: CSSProperties = {
  fontFamily: "var(--o-font-mono)",
};

const emptyStyle: CSSProperties = {
  padding: "10px 10px",
  fontSize: 11,
  color: "var(--o-text-3)",
};
