// Schema picker: показывает таблицы и колонки текущего архива.
// Клик по колонке → вставка её имени в editor через onInsert callback.

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import type { TableSchema } from "@/api/backend";
import { t, format } from "@/i18n/ru";
import styles from "./SQLConsole.module.css";

interface Props {
  schema: TableSchema;
  onInsert: (text: string) => void;
}

export function SchemaPanel({ schema, onInsert }: Props) {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const tables = Object.keys(schema);
  const totalColumns = tables.reduce((acc, t) => acc + schema[t].length, 0);
  const buttonLabel = tables.length === 0
    ? t.sql.schema.label
    : `${t.sql.schema.label} · ${format(t.sql.schema.columnsCount, { count: String(totalColumns) })}`;

  return (
    <div className={styles.saved_menu} ref={dropdownRef}>
      <button
        className={styles.template_btn}
        onClick={() => setOpen((v) => !v)}
        title={t.sql.schema.hint}
        disabled={tables.length === 0}
      >
        <Icon name="Database" size={11} color="var(--o-text-3)" />
        {buttonLabel}
        <Icon name="ChevronDown" size={10} color="var(--o-text-3)" />
      </button>

      {open && (
        <div
          className={styles.saved_dropdown}
          style={{ minWidth: 320, maxHeight: 440, bottom: 32, right: "auto", left: 0 }}
        >
          {tables.length === 0 ? (
            <div className={styles.saved_empty}>{t.sql.schema.empty}</div>
          ) : (
            <>
              <div className={styles.schema_hint}>{t.sql.schema.hint}</div>
              {tables.map((table) => (
                <div key={table}>
                  <div className={styles.schema_table_name}>{table}</div>
                  {schema[table].map((col) => (
                    <button
                      key={col.name}
                      type="button"
                      className={styles.schema_col_btn}
                      onClick={() => {
                        onInsert(col.name);
                        setOpen(false);
                      }}
                      title={`${col.name} : ${col.type}`}
                    >
                      <span className={styles.schema_col_name}>{col.name}</span>
                      <span className={styles.schema_col_type}>{col.type}</span>
                    </button>
                  ))}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
