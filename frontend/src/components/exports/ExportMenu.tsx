// Compact "Экспорт" dropdown с тремя форматами. Получает columns + rows из
// родителя — компонент не знает откуда они: view RPC, comparison diff,
// SQL editor result.

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { useAppStore } from "@/store/appStore";
import { exportRows, type ExportColumn, type ExportFormat } from "./export";

interface Props {
  defaultName: string;
  columns: ExportColumn[];
  rows: unknown[][];
  disabled?: boolean;
}

const FORMATS: { key: ExportFormat; label: string }[] = [
  { key: "csv", label: "CSV (запятые)" },
  { key: "tsv", label: "TSV (табуляция)" },
  { key: "json", label: "JSON" },
];

export function ExportMenu({ defaultName, columns, rows, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const pushToast = useAppStore((s) => s.pushToast);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const isEmpty = rows.length === 0 || columns.length === 0;
  const isDisabled = disabled || isEmpty;

  const handle = async (format: ExportFormat) => {
    setOpen(false);
    try {
      const { saved, path } = await exportRows(defaultName, format, columns, rows);
      if (saved && path) {
        pushToast(`Сохранено: ${path}`, "ok");
      }
    } catch (e) {
      pushToast(`Ошибка экспорта: ${String(e)}`, "err");
    }
  };

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-block" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={isDisabled}
        title={isEmpty ? "Нет данных для экспорта" : "Экспорт"}
        style={btnStyle(isDisabled)}
      >
        <Icon name="Download" size={11} />
        Экспорт
        <Icon name="ChevronDown" size={10} />
      </button>
      {open && (
        <div style={menuStyle}>
          {FORMATS.map((f) => (
            <button key={f.key} onClick={() => handle(f.key)} style={itemStyle}>
              {f.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function btnStyle(disabled: boolean): React.CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    height: 28,
    padding: "0 8px",
    fontSize: 11,
    border: "1px solid var(--o-border-2)",
    borderRadius: "var(--o-radius-sm, 4px)",
    color: disabled ? "var(--o-text-3)" : "var(--o-text-2)",
    background: "var(--o-panel)",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.55 : 1,
  };
}

const menuStyle: React.CSSProperties = {
  position: "absolute",
  top: "100%",
  right: 0,
  marginTop: 4,
  minWidth: 160,
  background: "var(--o-panel)",
  border: "1px solid var(--o-border)",
  borderRadius: 4,
  boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
  zIndex: 50,
  overflow: "hidden",
};

const itemStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "8px 12px",
  textAlign: "left",
  fontSize: 11.5,
  background: "transparent",
  border: "none",
  cursor: "pointer",
  color: "var(--o-text-2)",
};
