import type { CSSProperties } from "react";
import { Fragment, useMemo, useState } from "react";
import { backend } from "@/api/backend";
import { ExportMenu } from "@/components/exports/ExportMenu";
import { ViewShell } from "@/components/views/ViewShell";
import { colIndex, useView } from "@/components/views/useView";
import { useTableState } from "@/components/tables/useTableState";
import { TableFilter } from "@/components/tables/TableFilter";
import { filtersToDto, useAppStore } from "@/store/appStore";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

export function ErrorsFeedScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const [typeFilter, setTypeFilter] = useState<"all" | "EXCP" | "TDEADLOCK" | "TLOCK">("all");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewErrorsFeed(archiveId, filtersToDto(filters))
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId, filters],
  );

  // 1. type filter (dropdown) — сужает до конкретного event_type
  const typeFilteredRows = useMemo(() => {
    if (!data?.rows) return [] as unknown[][];
    if (typeFilter === "all") return data.rows;
    const idx = colIndex(data.columns);
    return data.rows.filter((r) => String(r[idx["event_type"]]) === typeFilter);
  }, [data, typeFilter]);

  const idx = useMemo(() => colIndex(data?.columns), [data?.columns]);

  // 2. useTableState — substring filter + sort внутри type-отфильтрованных rows
  const table = useTableState({
    rows: typeFilteredRows,
    columns: data?.columns ?? [],
    defaultSortKey: "ts",
    defaultSortDir: "desc",
  });

  return (
    <ViewShell
      breadcrumbs={["Анализ", "Ошибки и исключения"]}
      title={<>Ошибки и исключения</>}
      sub="EXCP / TDEADLOCK / TLOCK — последние сначала"
      right={
        <>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as typeof typeFilter)}
            style={selectStyle}
          >
            <option value="all">Все типы</option>
            <option value="EXCP">EXCP</option>
            <option value="TDEADLOCK">TDEADLOCK</option>
            <option value="TLOCK">TLOCK</option>
          </select>
          <ExportMenu
            defaultName="errors_feed"
            columns={data?.columns ?? []}
            rows={table.rows}
          />
        </>
      }
    >
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.panel_head}>
          <div className={vshellStyles.panel_title}>{typeFilteredRows.length} событий</div>
          {data && (
            <div className={vshellStyles.panel_sub}>
              выполнено за {(data.executed_ms ?? 0).toFixed(0)} мс
            </div>
          )}
          {typeFilteredRows.length > 0 && (
            <TableFilter
              value={table.filter}
              onChange={table.setFilter}
              total={table.totalRows}
              visible={table.visibleRows}
            />
          )}
        </div>
        {!archiveId && <div className={vshellStyles.empty}>Загрузите архив</div>}
        {archiveId && loading && <div className={vshellStyles.loading}>Загрузка…</div>}
        {archiveId && error && <div className={vshellStyles.error}>{error}</div>}
        {archiveId && !loading && !error && table.rows.length > 0 && (
          <div className={vshellStyles.table_wrap}>
            <table className={vshellStyles.table}>
              <thead>
                <tr>
                  <th {...table.headerProps("ts")}>Время</th>
                  <th {...table.headerProps("event_type")}>Тип</th>
                  <th {...table.headerProps("process_role")}>Роль</th>
                  <th {...table.headerProps("process_pid")}>PID</th>
                  <th {...table.headerProps("context")}>Контекст</th>
                  <th {...table.headerProps("duration_ms")}>ms</th>
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, ri) => {
                  const tone = badgeTone(String(row[idx["event_type"]] ?? ""));
                  const context = String(row[idx["context"]] ?? "");
                  const isExpanded = expanded.has(ri);
                  const toggle = () => {
                    setExpanded((prev) => {
                      const next = new Set(prev);
                      if (next.has(ri)) next.delete(ri);
                      else next.add(ri);
                      return next;
                    });
                  };
                  return (
                    <Fragment key={ri}>
                      <tr
                        className={`${vshellStyles.clickable}`}
                        onClick={toggle}
                      >
                        <td className={vshellStyles.mono} style={nowrapCell}>
                          {formatTs(row[idx["ts"]])}
                        </td>
                        <td style={nowrapCell}>
                          <span style={badgeStyle(tone)}>{String(row[idx["event_type"]] ?? "")}</span>
                        </td>
                        <td style={nowrapCell}>{String(row[idx["process_role"]] ?? "—")}</td>
                        <td className={vshellStyles.mono} style={nowrapCell}>
                          {String(row[idx["process_pid"]] ?? "—")}
                        </td>
                        <td style={contextCellStyle}>
                          <span style={contextTextStyle(isExpanded)}>{context || "—"}</span>
                        </td>
                        <td className={vshellStyles.mono} style={nowrapCell}>
                          {fmtMs(row[idx["duration_ms"]])}
                        </td>
                      </tr>
                      {isExpanded && context && (
                        <tr className={vshellStyles.expandRow}>
                          <td colSpan={6} style={expandedCellStyle}>
                            <pre style={expandedPreStyle}>{context}</pre>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {archiveId && !loading && !error && typeFilteredRows.length === 0 && (
          <div className={vshellStyles.empty}>Нет ошибок и исключений</div>
        )}
        {archiveId && !loading && !error && typeFilteredRows.length > 0 && table.rows.length === 0 && (
          <div className={vshellStyles.empty}>
            Фильтр «{table.filter}» не дал совпадений
          </div>
        )}
      </div>
    </ViewShell>
  );
}

const selectStyle: CSSProperties = {
  height: 28,
  padding: "0 8px",
  fontSize: 11.5,
  border: "1px solid var(--o-border-2)",
  borderRadius: 4,
  background: "var(--o-panel)",
  color: "var(--o-text-1)",
};

function badgeTone(type: string): "err" | "warn" | "mute" {
  if (type === "EXCP" || type === "TDEADLOCK") return "err";
  if (type === "TLOCK") return "warn";
  return "mute";
}

function badgeStyle(tone: "err" | "warn" | "mute"): CSSProperties {
  const bg = tone === "err" ? "rgba(220,38,38,0.1)" : tone === "warn" ? "rgba(245,158,11,0.1)" : "var(--o-subtle)";
  const fg = tone === "err" ? "#DC2626" : tone === "warn" ? "#B45309" : "var(--o-text-3)";
  return {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 3,
    fontSize: 10.5,
    fontFamily: "var(--o-font-mono)",
    background: bg,
    color: fg,
  };
}

function formatTs(v: unknown): string {
  if (v == null) return "—";
  const s = String(v);
  return s.length >= 19 ? s.slice(0, 19).replace("T", " ") : s;
}

function fmtMs(v: unknown): string {
  if (v == null || typeof v !== "number") return "—";
  if (v >= 1000) return (v / 1000).toFixed(2) + " с";
  return v.toFixed(1);
}

// Колонка контекста — единственная без nowrap; забирает остаток ширины
// после того, как короткие колонки (ts/type/role/pid/ms) заняли свой
// natural width.
const contextCellStyle: CSSProperties = {
  maxWidth: 0,
  width: "100%",
  overflow: "hidden",
};

const nowrapCell: CSSProperties = {
  whiteSpace: "nowrap",
};

function contextTextStyle(expanded: boolean): CSSProperties {
  if (expanded) {
    return {
      display: "block",
      whiteSpace: "normal",
      wordBreak: "break-word",
      color: "var(--o-text-1)",
    };
  }
  return {
    display: "block",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    color: "var(--o-text-2)",
  };
}

const expandedCellStyle: CSSProperties = {
  background: "var(--o-codebox-bg)",
  borderBottom: "1px solid var(--o-border-2)",
  padding: "12px 14px",
};

const expandedPreStyle: CSSProperties = {
  margin: 0,
  fontFamily: "var(--o-font-mono)",
  fontSize: 11.5,
  lineHeight: 1.55,
  color: "var(--o-text-1)",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
};
