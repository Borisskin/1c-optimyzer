// Sprint 5 hotfix: 3-state segmented control для фильтрации событий
// по наличию контекста. Размещается рядом с EventTypeFilter в panel_head
// (например на странице "События ТЖ").
//
// Состояния:
//   - 'any'     — без фильтра (по умолчанию)
//   - 'with'    — только события у которых есть Context
//   - 'without' — только события без Context
//
// Отдельно от EventTypeFilter — там multi-select по типу события, а здесь
// бинарная фильтрация по содержимому одной колонки.

import type { CSSProperties } from "react";

export type ContextPresenceFilter = "any" | "with" | "without";

interface Props {
  value: ContextPresenceFilter;
  onChange: (next: ContextPresenceFilter) => void;
  label?: string;
}

const OPTIONS: { value: ContextPresenceFilter; label: string; title: string }[] = [
  { value: "any", label: "все", title: "Показать все события" },
  { value: "with", label: "есть", title: "Только события с заполненным контекстом" },
  { value: "without", label: "нет", title: "Только события без контекста (NULL)" },
];

export function ContextFilter({ value, onChange, label = "Контекст" }: Props) {
  return (
    <div style={wrap} role="group" aria-label={label}>
      <span style={labelStyle}>{label}:</span>
      {OPTIONS.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            style={segStyle(active)}
            title={opt.title}
            aria-pressed={active}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

const wrap: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  height: 24,
  padding: "0 8px",
  border: "1px solid var(--o-border-2)",
  borderRadius: 4,
  background: "var(--o-panel)",
  fontFamily: "var(--o-font-mono)",
  fontSize: 11.5,
};

const labelStyle: CSSProperties = {
  color: "var(--o-text-3)",
  marginRight: 4,
};

function segStyle(active: boolean): CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    height: 18,
    padding: "0 8px",
    border: `1px solid ${active ? "var(--o-accent)" : "transparent"}`,
    borderRadius: 3,
    background: active ? "var(--o-subtle)" : "transparent",
    color: active ? "var(--o-text-1)" : "var(--o-text-3)",
    fontFamily: "inherit",
    fontSize: 11.5,
    fontWeight: active ? 600 : 400,
    cursor: "pointer",
  };
}
