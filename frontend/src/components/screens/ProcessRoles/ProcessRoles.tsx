import { useMemo } from "react";
import { backend } from "@/api/backend";
import { DonutChart } from "@/components/charts";
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

export function ProcessRolesScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const setFilters = useAppStore((s) => s.setFilters);
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewProcessRoles(archiveId, filtersToDto(filters))
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId, filters],
  );

  const { donutData, tableRows } = useMemo(() => {
    if (!data?.rows)
      return { donutData: [] as { label: string; value: number }[], tableRows: [] as unknown[][] };
    const idx = colIndex(data.columns);
    const donut = data.rows.map((r) => ({
      label: String(r[idx["process_role"]] ?? "—"),
      value: Number(r[idx["events_count"]] ?? 0),
    }));
    return { donutData: donut, tableRows: data.rows };
  }, [data]);

  const table = useTableState({
    rows: tableRows,
    columns: data?.columns ?? [],
    defaultSortKey: "events_count",
    defaultSortDir: "desc",
  });

  return (
    <ViewShell
      breadcrumbs={["Анализ", "Роли процессов"]}
      title={<>Роли процессов</>}
      sub="Распределение событий по rphost / rmngr / ragent / 1cv8 ..."
      right={
        <ExportMenu
          defaultName="process_roles"
          columns={data?.columns ?? []}
          rows={data?.rows ?? []}
        />
      }
    >
      <div style={{ display: "grid", gridTemplateColumns: "minmax(300px, 1fr) 2fr", gap: 16 }}>
        <div className={vshellStyles.panel}>
          <div className={vshellStyles.panel_title} style={{ marginBottom: 8 }}>
            События по ролям
          </div>
          {!archiveId && <div className={vshellStyles.empty}>Загрузите архив</div>}
          {archiveId && error && <div className={vshellStyles.error}>{error}</div>}
          {archiveId && !error && (
            <DonutChart
              data={donutData}
              isLoading={loading}
              height={260}
              onSliceClick={(slice) =>
                setFilters({ process_role: slice.label, source_view: "process-roles" })
              }
            />
          )}
        </div>

        <div className={vshellStyles.panel}>
          <div className={vshellStyles.panel_head}>
            <div className={vshellStyles.panel_title}>Детали</div>
            {tableRows.length > 0 && (
              <TableFilter
                value={table.filter}
                onChange={table.setFilter}
                total={table.totalRows}
                visible={table.visibleRows}
              />
            )}
          </div>
          {archiveId && !error && table.rows.length > 0 && (
            <div className={vshellStyles.table_wrap}>
              <table className={vshellStyles.table}>
                <thead>
                  <tr>
                    <th {...table.headerProps("process_role")}>Роль</th>
                    <th {...table.headerProps("events_count")}>События</th>
                    <th {...table.headerProps("total_duration_ms")}>Σ ms</th>
                    <th {...table.headerProps("avg_duration_ms")}>avg ms</th>
                    <th {...table.headerProps("unique_processes")}>Процессы</th>
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((row, ri) => {
                    const idx = colIndex(data?.columns);
                    return (
                      <tr key={ri}>
                        <td>{String(row[idx["process_role"]] ?? "—")}</td>
                        <td className={vshellStyles.mono}>{fmt(row[idx["events_count"]])}</td>
                        <td className={vshellStyles.mono}>{fmtMs(row[idx["total_duration_ms"]])}</td>
                        <td className={vshellStyles.mono}>{fmtMs(row[idx["avg_duration_ms"]])}</td>
                        <td className={vshellStyles.mono}>{fmt(row[idx["unique_processes"]])}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
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
