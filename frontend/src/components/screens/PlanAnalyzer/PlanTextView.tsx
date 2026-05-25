/**
 * Sprint 7 Phase D — отображение текстового execution plan (формат 1С planSQLText).
 *
 * SHOWPLAN_TEXT output от SQL Server выглядит как дерево операторов:
 *   |--Clustered Index Seek(OBJECT:([db].[dbo].[_Reference15]))
 *   |     SEEK:([_Reference15].[_IDRRef] = (?))
 *   |     Estimated Rows = 1
 *
 * В отличие от XML format (Phase B), text не парсится html-query-plan,
 * не имеет visualization, и PerformanceStudio CLI на нём не работает.
 * Это «lite» view — `<pre>` блок с monospace + AI explanation поверх.
 *
 * UI: header с meta (источник, длительность), пустой/empty state, body с текстом.
 */

import { useState } from "react";
import styles from "./PlanTextView.module.css";

interface Props {
  planText: string;
  /** Опционально: контекст события из ТЖ для header'а (sql_text, ts, duration). */
  meta?: {
    ts?: string | null;
    duration_us?: number | null;
    context?: string | null;
  };
}

export function PlanTextView({ planText, meta }: Props) {
  // Sprint 7 post-Phase F — collapse toggle. План занимает много места
  // (max-height: 600px), а юзеру он нужен не всегда — иногда хочется только
  // прочитать AI-объяснение и SQL. Default expanded — это основной контент.
  const [collapsed, setCollapsed] = useState(false);

  if (!planText.trim()) {
    return (
      <div className={styles.empty}>План пуст — нечего показать.</div>
    );
  }
  return (
    <div className={styles.container}>
      <div
        className={styles.header}
        onClick={() => setCollapsed((v) => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setCollapsed((v) => !v); } }}
        aria-expanded={!collapsed}
      >
        <div className={styles.title}>План запроса (текстовый формат 1С)</div>
        {meta && (
          <div className={styles.meta}>
            {meta.ts && <span className={styles.metaItem}>{formatTs(meta.ts)}</span>}
            {meta.duration_us != null && (
              <span className={styles.metaItem}>
                {formatDuration(meta.duration_us)}
              </span>
            )}
            {meta.context && (
              <span className={styles.metaContext} title={meta.context}>
                {meta.context}
              </span>
            )}
          </div>
        )}
      </div>
      {!collapsed && (
        <>
          <div className={styles.hint}>
            Это план в формате SHOWPLAN_TEXT — визуализация (SSMS-style дерево
            с операторами) недоступна, потому что 1С пишет планы как текст, не XML.
            Анализ через PerformanceStudio тоже не работает для текстового формата —
            используйте AI-объяснение поверх.
          </div>
          <pre className={styles.body}>{planText}</pre>
        </>
      )}
    </div>
  );
}

function formatTs(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function formatDuration(us: number): string {
  const ms = us / 1000;
  if (ms < 1) return `${us} мкс`;
  if (ms < 1000) return `${ms.toFixed(0)} мс`;
  return `${(ms / 1000).toFixed(2)} с`;
}
