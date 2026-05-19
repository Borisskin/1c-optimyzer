import type { CSSProperties } from "react";
import { useCallback, useEffect, useState } from "react";
import { backend, type ExplainerCacheEntry, type ExplainerStatus } from "@/api/backend";
import { ViewShell } from "@/components/views/ViewShell";
import { useTableState } from "@/components/tables/useTableState";
import { TableFilter } from "@/components/tables/TableFilter";
import { setDevMode } from "@/hooks/useDevMode";
import vshellStyles from "@/components/views/ViewShell.module.css";

/**
 * Developer-only screen. Доступен только при `localStorage["optimyzer:dev"] = "1"`
 * (toggle через Ctrl+Shift+D). Юзер обычно не видит этот экран.
 *
 * Управление:
 *  - Статус AI explainer engine
 *  - Содержимое cache (rows из data/explainer_cache.db)
 *  - Очистка кеша целиком / по архиву / точечно
 */
export function DevToolsScreen() {
  const [status, setStatus] = useState<ExplainerStatus | null>(null);
  const [entries, setEntries] = useState<ExplainerCacheEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, list] = await Promise.all([
        backend.explainerStatus(),
        backend.explainerCacheList(500),
      ]);
      setStatus(s);
      setEntries(list.entries ?? []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const columns = [
    { name: "archive_id" },
    { name: "anatomy_kind" },
    { name: "target_id" },
    { name: "rule_id" },
    { name: "model" },
    { name: "tokens_in" },
    { name: "tokens_out" },
    { name: "ai_text_len" },
    { name: "created_at" },
  ];
  const tableRows = entries.map((e) => [
    e.archive_id.slice(0, 8) + "…",
    e.anatomy_kind,
    e.target_id.length > 50 ? e.target_id.slice(0, 50) + "…" : e.target_id,
    e.rule_id ?? "—",
    e.model,
    e.tokens_in,
    e.tokens_out,
    e.ai_text_len,
    e.created_at.replace("T", " ").slice(0, 19),
  ]);
  const table = useTableState({
    rows: tableRows,
    columns,
    defaultSortKey: "created_at",
    defaultSortDir: "desc",
  });

  const handleClearAll = async () => {
    if (!window.confirm(`Очистить ВЕСЬ кеш AI? Удалится ${status?.cache_entries ?? "?"} entries. Следующие открытия anatomy вызовут API заново.`))
      return;
    setBusy("clear-all");
    try {
      await backend.explainerCacheClearAll();
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const handleReloadRules = async () => {
    setBusy("reload-rules");
    try {
      const res = await backend.explainerReloadRules();
      await refresh();
      window.alert(`Перечитано правил: ${res.rules_count}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const handleDeleteEntry = async (cache_key: string) => {
    setBusy(`delete-${cache_key}`);
    try {
      await backend.explainerCacheDeleteEntry(cache_key);
      setEntries((prev) => prev.filter((e) => e.cache_key !== cache_key));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <ViewShell
      breadcrumbs={["DevTools"]}
      title={<>DevTools</>}
      sub="Имплементационные детали — кеш AI, статус engine, ручное управление"
      right={
        <>
          <button type="button" style={btn} onClick={refresh} disabled={loading}>
            ↻ Refresh
          </button>
          <button
            type="button"
            style={btnDanger}
            onClick={() => setDevMode(false)}
            title="Скрыть DevTools screen (Ctrl+Shift+D — вернуть)"
          >
            Скрыть DevTools
          </button>
        </>
      }
    >
      {error && <div className={vshellStyles.error}>{error}</div>}

      {/* Status panel */}
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.panel_head}>
          <div className={vshellStyles.panel_title}>Explainer engine status</div>
        </div>
        <div style={statusGrid}>
          <StatusItem label="AI enabled" value={status?.ai_enabled ? "yes" : "no"} tone={status?.ai_enabled ? "ok" : "warn"} />
          <StatusItem label="Model" value={status?.model ?? "—"} />
          <StatusItem label="Rules loaded" value={String(status?.rules_count ?? "—")} />
          <StatusItem label="Cache entries" value={String(status?.cache_entries ?? "—")} />
        </div>
        <div style={actionsRow}>
          <button
            type="button"
            style={btn}
            onClick={handleReloadRules}
            disabled={busy === "reload-rules"}
            title="Перечитать backend/explainers/*.md (для разработки правил без рестарта)"
          >
            {busy === "reload-rules" ? "…" : "Reload rules"}
          </button>
          <button
            type="button"
            style={btnDanger}
            onClick={handleClearAll}
            disabled={busy === "clear-all" || (status?.cache_entries ?? 0) === 0}
          >
            {busy === "clear-all" ? "…" : "Очистить весь кеш"}
          </button>
        </div>
      </div>

      {/* Cache entries */}
      <div className={vshellStyles.panel} style={{ marginTop: 12 }}>
        <div className={vshellStyles.panel_head}>
          <div className={vshellStyles.panel_title}>
            Cache entries ({entries.length})
          </div>
          {entries.length > 0 && (
            <TableFilter
              value={table.filter}
              onChange={table.setFilter}
              total={table.totalRows}
              visible={table.visibleRows}
            />
          )}
        </div>
        {entries.length === 0 ? (
          <div className={vshellStyles.empty}>Кеш пуст</div>
        ) : (
          <div className={vshellStyles.table_wrap}>
            <table className={vshellStyles.table}>
              <thead>
                <tr>
                  <th {...table.headerProps("archive_id")}>archive</th>
                  <th {...table.headerProps("anatomy_kind")}>kind</th>
                  <th {...table.headerProps("target_id")}>target</th>
                  <th {...table.headerProps("rule_id")}>rule</th>
                  <th {...table.headerProps("model")}>model</th>
                  <th {...table.headerProps("tokens_in")}>tok in</th>
                  <th {...table.headerProps("tokens_out")}>tok out</th>
                  <th {...table.headerProps("ai_text_len")}>text len</th>
                  <th {...table.headerProps("created_at")}>created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, ri) => {
                  const entry = entries.find(
                    (e) =>
                      e.archive_id.startsWith(String(row[0]).replace("…", "")) &&
                      e.anatomy_kind === row[1],
                  );
                  return (
                    <tr key={ri}>
                      {row.map((cell, ci) => (
                        <td key={ci} className={vshellStyles.mono}>
                          {String(cell)}
                        </td>
                      ))}
                      <td>
                        {entry && (
                          <button
                            type="button"
                            style={btnDel}
                            disabled={busy === `delete-${entry.cache_key}`}
                            onClick={() => handleDeleteEntry(entry.cache_key)}
                            title="Удалить эту entry — следующее открытие вызовет API заново"
                          >
                            ×
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Hint */}
      <div style={hintStyle}>
        Сочетания клавиш:
        <ul style={{ margin: "4px 0 0 20px", padding: 0 }}>
          <li><kbd>Ctrl+Shift+D</kbd> — toggle DevTools screen</li>
          <li>localStorage <code>optimyzer:dev = "1"</code> — программная активация</li>
        </ul>
      </div>
    </ViewShell>
  );
}

function StatusItem({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "ok" | "warn";
}) {
  const color = tone === "ok" ? "var(--o-ok)" : tone === "warn" ? "#B45309" : "var(--o-text-1)";
  return (
    <div style={statusItem}>
      <div style={statusLabel}>{label}</div>
      <div style={{ ...statusValue, color }}>{value}</div>
    </div>
  );
}

const btn: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  height: 28,
  padding: "0 10px",
  fontSize: 11,
  border: "1px solid var(--o-border-2)",
  borderRadius: 4,
  color: "var(--o-text-2)",
  background: "var(--o-panel)",
  cursor: "pointer",
};

const btnDanger: CSSProperties = {
  ...btn,
  marginLeft: 8,
  borderColor: "#DC2626",
  color: "#DC2626",
};

const btnDel: CSSProperties = {
  width: 20,
  height: 20,
  padding: 0,
  border: "1px solid var(--o-border-2)",
  borderRadius: 3,
  background: "transparent",
  color: "var(--o-text-3)",
  fontSize: 12,
  cursor: "pointer",
};

const statusGrid: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
  gap: 12,
  padding: 16,
};

const statusItem: CSSProperties = {
  background: "var(--o-bg)",
  border: "1px solid var(--o-border-2)",
  borderRadius: 4,
  padding: "8px 12px",
};

const statusLabel: CSSProperties = {
  fontSize: 10.5,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "var(--o-text-3)",
  fontFamily: "var(--o-font-mono)",
  marginBottom: 4,
};

const statusValue: CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  fontFamily: "var(--o-font-mono)",
};

const actionsRow: CSSProperties = {
  padding: "0 16px 16px",
  display: "flex",
  alignItems: "center",
  gap: 8,
};

const hintStyle: CSSProperties = {
  marginTop: 12,
  padding: 12,
  fontSize: 11,
  color: "var(--o-text-3)",
  fontFamily: "var(--o-font-mono)",
  background: "var(--o-subtle)",
  borderRadius: 4,
};
