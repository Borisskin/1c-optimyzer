import { Fragment, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { backend } from "@/api/backend";
import { ExportMenu } from "@/components/exports/ExportMenu";
import { ViewShell } from "@/components/views/ViewShell";
import { colIndex, useView } from "@/components/views/useView";
import { useTableState } from "@/components/tables/useTableState";
import { TableFilter } from "@/components/tables/TableFilter";
import { LimitSelector } from "@/components/tables/LimitSelector";
import { filtersToDto, useAppStore } from "@/store/appStore";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

export function SlowQueriesScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const [limit, setLimit] = useState(100);
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewSlowQueries(archiveId, filtersToDto(filters), "total_duration", limit)
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId, filters, limit],
  );

  const idx = useMemo(() => colIndex(data?.columns), [data?.columns]);

  const table = useTableState({
    rows: data?.rows ?? [],
    columns: data?.columns ?? [],
    defaultSortKey: "total_duration_ms",
    defaultSortDir: "desc",
  });

  // Sprint 5 hotfix #2 (расширение): expand-by-click для длинного запроса
  // вместо hover-tooltip. Hover не позволял ни скопировать, ни нормально
  // прочитать SQL длиной 1+ КБ. По клику на строку — раскрывается inline-
  // блок с полным selectable-текстом. Тот же паттерн что в Anatomy/Top SQL.
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const toggleRow = (ri: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(ri)) next.delete(ri);
      else next.add(ri);
      return next;
    });
  };

  return (
    <ViewShell
      breadcrumbs={["Анализ", "Медленные запросы"]}
      title={<>Медленные запросы</>}
      sub="Топ агрегированных SQL запросов по суммарной длительности"
      right={
        <ExportMenu
          defaultName="slow_queries"
          columns={data?.columns ?? []}
          rows={table.rows}
        />
      }
    >
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.panel_head}>
          <LimitSelector
            value={limit}
            onChange={setLimit}
            loaded={data?.rows?.length ?? 0}
            total={data?.total_rows ?? null}
            unitLabel="запросов"
          />
          {data && (
            <div className={vshellStyles.panel_sub}>
              за {(data.executed_ms ?? 0).toFixed(0)} мс
            </div>
          )}
          {data && data.rows && data.rows.length > 0 && (
            <TableFilter
              value={table.filter}
              onChange={table.setFilter}
              total={table.totalRows}
              visible={table.visibleRows}
              placeholder="Поиск по тексту запроса…"
            />
          )}
        </div>

        {!archiveId && <div className={vshellStyles.empty}>Загрузите архив, чтобы увидеть медленные запросы</div>}
        {archiveId && loading && <div className={vshellStyles.loading}>Загрузка…</div>}
        {archiveId && error && <div className={vshellStyles.error}>{error}</div>}
        {archiveId && !loading && !error && data && data.rows && data.rows.length > 0 && (
          <div className={vshellStyles.table_wrap}>
            <table className={vshellStyles.table}>
              <thead>
                <tr>
                  <th>#</th>
                  <th {...table.headerProps("query")}>Запрос (нормализованный)</th>
                  <th {...table.headerProps("calls")}>Calls</th>
                  <th {...table.headerProps("total_duration_ms")}>Σ ms</th>
                  <th {...table.headerProps("avg_duration_ms")}>avg ms</th>
                  <th {...table.headerProps("max_duration_ms")}>max ms</th>
                  <th {...table.headerProps("total_rows_read")}>Σ rows</th>
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, ri) => {
                  const queryFull = String(row[idx["query"]] ?? "");
                  const isExpandable = queryFull.length > 80;
                  const isExpanded = expanded.has(ri);
                  return (
                    <Fragment key={ri}>
                      <tr
                        onClick={isExpandable ? () => toggleRow(ri) : undefined}
                        style={{ cursor: isExpandable ? "pointer" : "default" }}
                        title={isExpandable ? (isExpanded ? "Клик — свернуть" : "Клик — раскрыть полный запрос") : undefined}
                      >
                        <td className={vshellStyles.mono}>{ri + 1}</td>
                        <td>
                          {isExpandable ? queryFull.slice(0, 80) + "…" : queryFull}
                        </td>
                        <td className={vshellStyles.mono}>{fmt(row[idx["calls"]])}</td>
                        <td className={vshellStyles.mono}>{fmtMs(row[idx["total_duration_ms"]])}</td>
                        <td className={vshellStyles.mono}>{fmtMs(row[idx["avg_duration_ms"]])}</td>
                        <td className={vshellStyles.mono}>{fmtMs(row[idx["max_duration_ms"]])}</td>
                        <td className={vshellStyles.mono}>{fmt(row[idx["total_rows_read"]])}</td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} style={expandedCellStyle}>
                            <pre style={expandedPreStyle}>{queryFull}</pre>
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
        {archiveId && !loading && !error && data && data.row_count === 0 && (
          <div className={vshellStyles.empty}>Нет DBMSSQL-запросов в архиве</div>
        )}
      </div>
    </ViewShell>
  );
}

function fmt(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "number") return v.toLocaleString("ru-RU");
  return String(v);
}

function fmtMs(v: unknown): string {
  if (v == null || typeof v !== "number") return "—";
  if (v >= 1000) return (v / 1000).toFixed(2) + " с";
  return v.toFixed(1);
}

const expandedCellStyle: CSSProperties = {
  background: "var(--o-subtle)",
  padding: 0,
};

const expandedPreStyle: CSSProperties = {
  margin: 0,
  padding: "10px 12px",
  fontFamily: "var(--o-font-mono)",
  fontSize: 12,
  lineHeight: 1.45,
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
  color: "var(--o-text-1)",
  userSelect: "text",
  cursor: "text",
};
