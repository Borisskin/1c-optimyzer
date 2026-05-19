import { useMemo } from "react";
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

export function SlowQueriesScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewSlowQueries(archiveId, filtersToDto(filters), "total_duration", 100)
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId, filters],
  );

  const idx = useMemo(() => colIndex(data?.columns), [data?.columns]);

  const table = useTableState({
    rows: data?.rows ?? [],
    columns: data?.columns ?? [],
    defaultSortKey: "total_duration_ms",
    defaultSortDir: "desc",
  });

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
          <div className={vshellStyles.panel_title}>
            {loading ? "Загрузка…" : `${data?.row_count ?? 0} запросов`}
          </div>
          {data && (
            <div className={vshellStyles.panel_sub}>
              выполнено за {(data.executed_ms ?? 0).toFixed(0)} мс
            </div>
          )}
          {data && data.rows && data.rows.length > 0 && (
            <TableFilter
              value={table.filter}
              onChange={table.setFilter}
              total={table.totalRows}
              visible={table.visibleRows}
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
                {table.rows.map((row, ri) => (
                  <tr key={ri}>
                    <td className={vshellStyles.mono}>{ri + 1}</td>
                    <td title={String(row[idx["query"]] ?? "")}>
                      {truncate(String(row[idx["query"]] ?? ""), 80)}
                    </td>
                    <td className={vshellStyles.mono}>{fmt(row[idx["calls"]])}</td>
                    <td className={vshellStyles.mono}>{fmtMs(row[idx["total_duration_ms"]])}</td>
                    <td className={vshellStyles.mono}>{fmtMs(row[idx["avg_duration_ms"]])}</td>
                    <td className={vshellStyles.mono}>{fmtMs(row[idx["max_duration_ms"]])}</td>
                    <td className={vshellStyles.mono}>{fmt(row[idx["total_rows_read"]])}</td>
                  </tr>
                ))}
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

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n) + "…";
}
