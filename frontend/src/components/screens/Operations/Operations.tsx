import type { CSSProperties } from "react";
import { useMemo, useState } from "react";
import { backend } from "@/api/backend";
import { ExportMenu } from "@/components/exports/ExportMenu";
import { ViewShell } from "@/components/views/ViewShell";
import { colIndex, useView } from "@/components/views/useView";
import { filtersToDto, useAppStore } from "@/store/appStore";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

type SortBy =
  | "total_duration_ms"
  | "avg_duration_ms"
  | "max_duration_ms"
  | "calls"
  | "sql_duration_ms"
  | "lock_events"
  | "exception_events";

export function OperationsScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const setScreen = useAppStore((s) => s.setScreen);
  const setSelectedOperation = useAppStore((s) => s.setSelectedOperation);
  const [sortBy, setSortBy] = useState<SortBy>("total_duration_ms");
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewTopBusinessOperations(archiveId, filtersToDto(filters), sortBy, 100)
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId, filters, sortBy],
  );

  const idx = useMemo(() => colIndex(data?.columns), [data?.columns]);
  const rows = data?.rows ?? [];

  const totalDuration = useMemo(() => {
    if (!rows.length) return 0;
    const i = idx["total_duration_ms"];
    return rows.reduce((s, r) => s + (Number(r[i]) || 0), 0);
  }, [rows, idx]);

  const openAnatomy = (operation: string) => {
    setSelectedOperation(operation);
    setScreen("anatomy");
  };

  return (
    <ViewShell
      breadcrumbs={["Анализ", "Бизнес-операции"]}
      title={<>Бизнес-операции</>}
      sub="Топ операций по `Context` — что фактически выполнялось в платформе"
      right={
        <>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
            style={selectStyle}
          >
            <option value="total_duration_ms">Σ время</option>
            <option value="avg_duration_ms">avg время</option>
            <option value="max_duration_ms">max время</option>
            <option value="calls">кол-во вызовов</option>
            <option value="sql_duration_ms">SQL-время</option>
            <option value="lock_events">блокировок</option>
            <option value="exception_events">исключений</option>
          </select>
          <ExportMenu
            defaultName="top_business_operations"
            columns={data?.columns ?? []}
            rows={rows}
          />
        </>
      }
    >
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.panel_head}>
          <div className={vshellStyles.panel_title}>
            {loading ? "Загрузка…" : `${rows.length} операций`}
          </div>
          {data && (
            <div className={vshellStyles.panel_sub}>
              выполнено за {(data.executed_ms ?? 0).toFixed(0)} мс
            </div>
          )}
        </div>

        {!archiveId && <div className={vshellStyles.empty}>Загрузите архив</div>}
        {archiveId && loading && <div className={vshellStyles.loading}>Загрузка…</div>}
        {archiveId && error && <div className={vshellStyles.error}>{error}</div>}
        {archiveId && !loading && !error && rows.length > 0 && (
          <div className={vshellStyles.table_wrap}>
            <table className={vshellStyles.table}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Операция</th>
                  <th>Вызовов</th>
                  <th>Σ ms</th>
                  <th>avg ms</th>
                  <th>max ms</th>
                  <th>SQL ms</th>
                  <th>Locks</th>
                  <th>EXCP</th>
                  <th>Сессий</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => {
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
        {archiveId && !loading && !error && rows.length === 0 && (
          <div className={vshellStyles.empty}>
            В архиве нет событий с заполненным `Context` —
            либо logcfg.xml не пишет Context, либо filters его исключают
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

const selectStyle: CSSProperties = {
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
