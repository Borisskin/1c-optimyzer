// Dropdown-multi-select для выбора event_type в panel_head.
// Размещается на одном уровне с TableFilter, слева от поиска.

import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { Icon } from "@/components/icons/Icon";

interface Option {
  value: string;
  count: number;
}

interface Props {
  options: Option[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
  label?: string;
}

export function EventTypeFilter({ options, selected, onChange, label = "Тип" }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

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

  const triggerLabel = useMemo(() => {
    if (selected.size === 0) return "все";
    if (selected.size <= 2) return [...selected].join(", ");
    return `${selected.size} из ${options.length}`;
  }, [selected, options.length]);

  const toggle = (v: string) => {
    const next = new Set(selected);
    if (next.has(v)) next.delete(v);
    else next.add(v);
    onChange(next);
  };

  const reset = () => onChange(new Set());
  const selectAll = () => onChange(new Set(options.map((o) => o.value)));

  const active = selected.size > 0;

  return (
    <div ref={ref} style={wrap}>
      <button type="button" onClick={() => setOpen((v) => !v)} style={triggerStyle(active, open)}>
        <span style={triggerLabelStyle}>{label}:</span>
        <span style={triggerValueStyle}>{triggerLabel}</span>
        <Icon name="ChevronDown" size={11} color="var(--o-text-3)" />
      </button>
      {open && (
        <div style={popStyle} role="dialog" aria-label={label}>
          <div style={popHeader}>
            <button type="button" onClick={selectAll} style={linkBtnStyle} title="Выбрать все">
              Все
            </button>
            {active && (
              <button type="button" onClick={reset} style={linkBtnStyle} title="Сбросить фильтр">
                Сбросить
              </button>
            )}
          </div>
          {options.length === 0 ? (
            <div style={emptyStyle}>Нет значений</div>
          ) : (
            <div style={listStyle}>
              {options.map((opt) => (
                <label key={opt.value} style={rowStyle}>
                  <input
                    type="checkbox"
                    checked={selected.has(opt.value)}
                    onChange={() => toggle(opt.value)}
                    style={checkboxStyle}
                  />
                  <span style={valueStyle}>
                    {opt.value} <span style={countInlineStyle}>({opt.count.toLocaleString("ru-RU")})</span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const wrap: CSSProperties = {
  position: "relative",
  display: "inline-flex",
  alignItems: "center",
};

function triggerStyle(active: boolean, open: boolean): CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "0 8px",
    height: 24,
    border: `1px solid ${active || open ? "var(--o-border)" : "var(--o-border-2)"}`,
    borderRadius: 4,
    background: active ? "var(--o-subtle)" : "var(--o-panel)",
    color: "var(--o-text-1)",
    fontSize: 11.5,
    cursor: "pointer",
    fontFamily: "var(--o-font-mono)",
  };
}

const triggerLabelStyle: CSSProperties = {
  color: "var(--o-text-3)",
};

const triggerValueStyle: CSSProperties = {
  color: "var(--o-text-1)",
};

const popStyle: CSSProperties = {
  position: "absolute",
  top: "calc(100% + 4px)",
  right: 0,
  minWidth: 220,
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
  padding: "6px 10px",
  borderBottom: "1px solid var(--o-border-2)",
  gap: 12,
};

const linkBtnStyle: CSSProperties = {
  border: "none",
  background: "transparent",
  color: "var(--o-accent)",
  fontSize: 11,
  cursor: "pointer",
  padding: 0,
};

const listStyle: CSSProperties = {
  maxHeight: 280,
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
  flex: 1,
};

const countInlineStyle: CSSProperties = {
  color: "var(--o-text-3)",
  fontSize: 11,
};

const emptyStyle: CSSProperties = {
  padding: "10px 10px",
  fontSize: 11,
  color: "var(--o-text-3)",
};
