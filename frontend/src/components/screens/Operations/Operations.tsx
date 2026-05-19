import type { CSSProperties } from "react";
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

export function OperationsScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const setScreen = useAppStore((s) => s.setScreen);
  const setSelectedOperation = useAppStore((s) => s.setSelectedOperation);
  // Backend всегда возвращает топ-500 по total_duration_ms. Клиентская
  // sort/filter работает внутри этих 500. Это даёт хороший repr данных
  // для производственных архивов с сотнями операций. Server-side sort
  // selector убран — sort везде через клик по заголовку колонки.
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewTopBusinessOperations(archiveId, filtersToDto(filters), "total_duration_ms", 500)
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

  const totalDuration = useMemo(() => {
    if (!table.rows.length) return 0;
    const i = idx["total_duration_ms"];
    return table.rows.reduce((s, r) => s + (Number(r[i]) || 0), 0);
  }, [table.rows, idx]);

  const openAnatomy = (operation: string) => {
    setSelectedOperation(operation);
    setScreen("anatomy");
  };

  return (
    <ViewShell
      breadcrumbs={["Анализ", "Бизнес-операции"]}
      title={<>Бизнес-операции</>}
      sub="Топ операций по `Context` — клик по заголовку колонки = сортировка"
      right={
        <ExportMenu
          defaultName="top_business_operations"
          columns={data?.columns ?? []}
          rows={table.rows}
        />
      }
    >
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.panel_head}>
          <div className={vshellStyles.panel_title}>
            {loading ? "Загрузка…" : `${data?.row_count ?? 0} операций`}
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

        {!archiveId && <div className={vshellStyles.empty}>Загрузите архив</div>}
        {archiveId && loading && <div className={vshellStyles.loading}>Загрузка…</div>}
        {archiveId && error && <div className={vshellStyles.error}>{error}</div>}
        {archiveId && !loading && !error && table.rows.length > 0 && (
          <div className={vshellStyles.table_wrap}>
            <table className={vshellStyles.table}>
              <thead>
                <tr>
                  <th>#</th>
                  <th {...table.headerProps("operation")}>Операция</th>
                  <th {...table.headerProps("calls")}>Вызовов</th>
                  <th {...table.headerProps("total_duration_ms")}>Σ ms</th>
                  <th {...table.headerProps("avg_duration_ms")}>avg ms</th>
                  <th {...table.headerProps("max_duration_ms")}>max ms</th>
                  <th {...table.headerProps("sql_duration_ms")}>SQL ms</th>
                  <th {...table.headerProps("lock_events")}>Locks</th>
                  <th {...table.headerProps("exception_events")}>EXCP</th>
                  <th {...table.headerProps("unique_sessions")}>Сессий</th>
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, ri) => {
                  const op = String(row[idx["operation"]] ?? "");
                  const dur = Number(row[idx["total_duration_ms"]]) || 0;
                  const tone = pickTone(dur, totalDuration);
                  return (
                    <tr
                      key={ri}
                      className={vshellStyles.clickable}
                      onClick={() => openAnatomy(op)}
                      title="Кликни — открыть детали операции"
                    >
                      <td className={vshellStyles.mono}>{ri + 1}</td>
                      <td>
                        <span style={opStyle}>{op}</span>
                        {tone !== "none" && <span style={dotStyle(tone)} />}
                      </td>
                      <td className={vshellStyles.mono}>{fmt(row[idx["calls"]])}</td>
                      <td className={vshellStyles.mono} style={tone === "hot" ? heavyStyle : undefined}>
                        {fmtMs(row[idx["total_duration_ms"]])}
                      </td>
                      <td className={vshellStyles.mono}>{fmtMs(row[idx["avg_duration_ms"]])}</td>
                      <td className={vshellStyles.mono}>{fmtMs(row[idx["max_duration_ms"]])}</td>
                      <td className={vshellStyles.mono}>{fmtMs(row[idx["sql_duration_ms"]])}</td>
                      <td className={vshellStyles.mono} style={lockStyle(Number(row[idx["lock_events"]]))}>
                        {fmt(row[idx["lock_events"]])}
                      </td>
                      <td className={vshellStyles.mono} style={excpStyle(Number(row[idx["exception_events"]]))}>
                        {fmt(row[idx["exception_events"]])}
                      </td>
                      <td className={vshellStyles.mono}>{fmt(row[idx["unique_sessions"]])}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {archiveId && !loading && !error && data && (data.row_count ?? 0) === 0 && (
          <div className={vshellStyles.empty}>
            В архиве нет событий с заполненным `Context` —
            либо logcfg.xml не пишет Context, либо filters его исключают
          </div>
        )}
        {archiveId && !loading && !error && (data?.row_count ?? 0) > 0 && table.rows.length === 0 && (
          <div className={vshellStyles.empty}>
            Фильтр «{table.filter}» не дал совпадений ·{" "}
            <button type="button" onClick={() => table.setFilter("")} style={resetBtn}>
              сбросить
            </button>
          </div>
        )}
      </div>
    </ViewShell>
  );
}

type Tone = "hot" | "warm" | "none";

function pickTone(value: number, total: number): Tone {
  if (total <= 0) return "none";
  const pct = value / total;
  if (pct >= 0.3) return "hot";
  if (pct >= 0.1) return "warm";
  return "none";
}

function dotStyle(tone: Tone): CSSProperties {
  const colors: Record<Tone, string> = {
    hot: "#DC2626",
    warm: "#D97706",
    none: "transparent",
  };
  return {
    display: "inline-block",
    marginLeft: 6,
    width: 6,
    height: 6,
    borderRadius: 3,
    background: colors[tone],
    verticalAlign: "middle",
  };
}

const heavyStyle: CSSProperties = { color: "#DC2626", fontWeight: 600 };

function lockStyle(n: number): CSSProperties | undefined {
  if (!n) return undefined;
  return { color: "#B45309", fontWeight: 500 };
}

function excpStyle(n: number): CSSProperties | undefined {
  if (!n) return undefined;
  return { color: "#DC2626", fontWeight: 500 };
}

const opStyle: CSSProperties = {
  fontFamily: "var(--o-font-mono)",
  fontSize: 11.5,
};

const resetBtn: CSSProperties = {
  border: "none",
  background: "transparent",
  color: "var(--o-accent)",
  cursor: "pointer",
  textDecoration: "underline",
  padding: 0,
  fontSize: "inherit",
};

const _unusedSelectStyle: CSSProperties = {
  height: 28,
  padding: "0 8px",
  fontSize: 11.5,
  border: "1px solid var(--o-border-2)",
  borderRadius: 4,
  background: "var(--o-panel)",
  color: "var(--o-text-1)",
};

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
