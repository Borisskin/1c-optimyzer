import type { CSSProperties } from "react";
import { Fragment, useEffect, useMemo, useState } from "react";
import { backend, type OperationAnatomyResult } from "@/api/backend";
import { ViewShell } from "@/components/views/ViewShell";
import { ExplainerCard } from "@/components/explainer/ExplainerCard";
import { useTableState } from "@/components/tables/useTableState";
import { TableFilter } from "@/components/tables/TableFilter";
import { useStickyTableHead } from "@/components/views/useStickyTableHead";
import { useAppStore } from "@/store/appStore";
import { formatSql } from "@/utils/sqlFormat";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

export function AnatomyScreen({ archiveId }: Props) {
  const operation = useAppStore((s) => s.selectedOperation);
  const setScreen = useAppStore((s) => s.setScreen);
  const [data, setData] = useState<OperationAnatomyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!archiveId || !operation) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    backend
      .viewOperationAnatomy(archiveId, operation)
      .then((res) => {
        if (cancelled) return;
        if (!res.ok) {
          setError(res.error ?? "Ошибка загрузки");
          setData(null);
        } else {
          setData(res);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [archiveId, operation]);

  if (!archiveId) {
    return (
      <ViewShell
        breadcrumbs={[
          "Анализ",
          { label: "Бизнес-операции", onClick: () => setScreen("operations") },
          "Анатомия операции",
        ]}
        title={<>Анатомия операции</>}
      >
        <div className={vshellStyles.panel}>
          <div className={vshellStyles.empty}>Загрузите архив</div>
        </div>
      </ViewShell>
    );
  }

  if (!operation) {
    return (
      <ViewShell
        breadcrumbs={[
          "Анализ",
          { label: "Бизнес-операции", onClick: () => setScreen("operations") },
          "Анатомия операции",
        ]}
        title={<>Анатомия операции</>}
      >
        <div className={vshellStyles.panel}>
          <div className={vshellStyles.empty}>
            Откройте «Бизнес-операции» и кликните по строке, чтобы попасть сюда
            <div style={{ marginTop: 12 }}>
              <button
                style={btnStyle}
                onClick={() => setScreen("operations")}
                type="button"
              >
                Перейти к Бизнес-операциям
              </button>
            </div>
          </div>
        </div>
      </ViewShell>
    );
  }

  const s = data?.summary;
  const found = s?.found ?? false;

  return (
    <ViewShell
      breadcrumbs={[
        "Анализ",
        { label: "Бизнес-операции", onClick: () => setScreen("operations") },
        "Анатомия операции",
      ]}
      title={
        <span style={titleOp}>
          {operation}
        </span>
      }
      sub="Drill-down по операции — timeline, breakdown, top SQL, exceptions"
      right={
        <button
          type="button"
          style={btnStyle}
          onClick={() => setScreen("operations")}
        >
          ← Назад к списку
        </button>
      }
    >
      {loading && <div className={vshellStyles.loading}>Загрузка…</div>}
      {error && <div className={vshellStyles.error}>{error}</div>}

      {!loading && !error && data && !found && (
        <div className={vshellStyles.panel}>
          <div className={vshellStyles.empty}>
            Операция «{operation}» не найдена в архиве
          </div>
        </div>
      )}

      {!loading && !error && data && found && s && (
        <>
          <ExplainerCard
            archiveId={archiveId}
            anatomyKind="slow_op"
            targetId={operation}
            features={{
              operation,
              calls: s.total_events ?? 0,
              // Округление чтобы в template substitution не вылазило
              // "1.909757467634394 мс" — пользователю достаточно 1 знака.
              avg_duration_ms: round1(s.avg_duration_ms ?? 0),
              total_duration_ms: round1(s.total_duration_ms ?? 0),
              total_duration_s: ((s.total_duration_ms ?? 0) / 1000).toFixed(1),
              sql_duration_ms: round1(
                data.breakdown.find((b) => b.event_type === "DBMSSQL")?.total_duration_ms ?? 0,
              ),
              sql_share: (s.total_duration_ms ?? 0) > 0
                ? ((data.breakdown.find((b) => b.event_type === "DBMSSQL")?.total_duration_ms ?? 0) / (s.total_duration_ms ?? 1))
                : 0,
              sql_share_pct: Math.round(
                (s.total_duration_ms ?? 0) > 0
                  ? ((data.breakdown.find((b) => b.event_type === "DBMSSQL")?.total_duration_ms ?? 0) / (s.total_duration_ms ?? 1)) * 100
                  : 0,
              ),
              lock_events: s.lock_count ?? 0,
              lock_share: (s.total_events ?? 0) > 0 ? (s.lock_count ?? 0) / (s.total_events ?? 1) : 0,
            }}
            anatomyData={{
              operation,
              summary: s,
              breakdown: data.breakdown,
              top_sql_count: data.top_sql.row_count,
            }}
          />
          <div className={vshellStyles.panel} style={summaryPanel}>
            <div className={vshellStyles.panel_head}>
              <div className={vshellStyles.panel_title}>Сводка</div>
            </div>
            <div style={metricsGrid}>
              <Metric label="Событий" value={fmt(s.total_events)} />
              {/* Σ длительность = сумма durations всех событий БЕЗ EXCPCNTX
                  и Context (они cumulative и дают double-count). Это
                  "CPU/work time" — может быть больше wall-clock из-за
                  параллельных сессий. По часам = реальный календарный
                  промежуток (last_seen - first_seen). */}
              <Metric label="Σ длительность" value={fmtMs(s.total_duration_ms)} />
              <Metric label="По часам" value={fmtWallClock(s.wall_clock_ms)} />
              <Metric label="avg" value={fmtMs(s.avg_duration_ms)} />
              <Metric label="max" value={fmtMs(s.max_duration_ms)} />
              <Metric label="Сессий" value={fmt(s.unique_sessions)} />
              <Metric label="Процессов" value={fmt(s.unique_processes)} />
              <Metric label="SQL" value={fmt(s.sql_count)} tone={(s.sql_count ?? 0) > 0 ? "info" : undefined} />
              <Metric label="Блокировок" value={fmt(s.lock_count)} tone={(s.lock_count ?? 0) > 0 ? "warn" : undefined} />
              <Metric label="Исключений" value={fmt(s.exception_count)} tone={(s.exception_count ?? 0) > 0 ? "err" : undefined} />
            </div>
            <div style={metaLine}>
              Роли: {s.process_roles || "—"} · с {fmtTs(s.first_seen)} по {fmtTs(s.last_seen)}
            </div>
          </div>

          <BreakdownTable
            breakdown={data.breakdown}
            totalDurationMs={s.total_duration_ms ?? 0}
          />

          {data.top_sql.row_count > 0 && (
            <div className={vshellStyles.panel} style={{ marginTop: 12 }}>
              <SubTableRender
                st={data.top_sql}
                truncateCol="query"
                title="Top SQL внутри операции"
                defaultSortKey="total_duration_ms"
              />
            </div>
          )}

          {data.related_exceptions.row_count > 0 && (
            <div className={vshellStyles.panel} style={{ marginTop: 12 }}>
              <SubTableRender
                st={data.related_exceptions}
                title="Связанные исключения"
                defaultSortKey="ts"
              />
            </div>
          )}

          {data.timeline.row_count > 0 && (
            <div className={vshellStyles.panel} style={{ marginTop: 12 }}>
              <SubTableRender
                st={data.timeline}
                title={`Timeline (${data.timeline.row_count} последних событий)`}
                defaultSortKey="ts"
              />
            </div>
          )}
        </>
      )}
    </ViewShell>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "info" | "warn" | "err";
}) {
  return (
    <div style={metricCard}>
      <div style={metricLabel}>{label}</div>
      <div style={metricValue(tone)}>{value}</div>
    </div>
  );
}

function SubTableRender({
  st,
  truncateCol,
  title,
  defaultSortKey,
}: {
  st: { columns: { name: string }[]; rows: unknown[][] };
  truncateCol?: string;
  title?: string;
  defaultSortKey?: string;
}) {
  const table = useTableState({
    rows: st.rows,
    columns: st.columns,
    defaultSortKey,
    defaultSortDir: "desc",
  });
  const truncIdx = truncateCol ? st.columns.findIndex((c) => c.name === truncateCol) : -1;
  // Sprint 5 hotfix: expandable rows вместо hover tooltip.
  // Hover не позволял ни скопировать, ни нормально прочитать длинный SQL.
  // Теперь клик по строке (если truncated) раскрывает inline-блок с
  // полным текстом — selectable и copyable.
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const toggleRow = (ri: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(ri)) next.delete(ri);
      else next.add(ri);
      return next;
    });
  };

  const { panelHeadRef, panelStyle } = useStickyTableHead<HTMLDivElement>();

  return (
    <div style={panelStyle}>
      <div ref={panelHeadRef} className={vshellStyles.panel_head}>
        {title && <div className={vshellStyles.panel_title}>{title}</div>}
        {st.rows.length > 0 && (
          <TableFilter
            value={table.filter}
            onChange={table.setFilter}
            total={table.totalRows}
            visible={table.visibleRows}
          />
        )}
      </div>
      <div className={vshellStyles.table_wrap}>
        <table className={vshellStyles.table}>
          <thead>
            <tr>
              {st.columns.map((c) => (
                <th key={c.name} {...table.headerProps(c.name)}>{c.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => {
              const rawTrunc = truncIdx >= 0 ? formatCell(row[truncIdx]) : "";
              const isExpandable = truncIdx >= 0 && rawTrunc.length > 100;
              const isExpanded = expanded.has(ri);
              return (
                <Fragment key={ri}>
                  <tr
                    onClick={isExpandable ? () => toggleRow(ri) : undefined}
                    style={{ cursor: isExpandable ? "pointer" : "default" }}
                  >
                    {row.map((cell, ci) => {
                      const raw = formatCell(cell);
                      const isTruncCell = ci === truncIdx;
                      const display =
                        isTruncCell && raw.length > 100
                          ? raw.slice(0, 100) + "…"
                          : raw;
                      return (
                        <td key={ci} className={vshellStyles.mono}>
                          {isExpandable && isTruncCell && (
                            <span style={expandToggleStyle} aria-hidden>
                              {isExpanded ? "▼" : "▶"}{" "}
                            </span>
                          )}
                          {display}
                        </td>
                      );
                    })}
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={st.columns.length} style={expandedCellStyle}>
                        <pre style={expandedPreStyle}>
                          {truncateCol === "query" ? formatSql(rawTrunc) : rawTrunc}
                        </pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const expandToggleStyle: CSSProperties = {
  color: "var(--o-text-3)",
  fontSize: 10,
  userSelect: "none",
};

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

function BreakdownTable({
  breakdown,
  totalDurationMs,
}: {
  breakdown: { event_type: string; events: number; total_duration_ms: number; avg_duration_ms: number }[];
  totalDurationMs: number;
}) {
  // Преобразуем breakdown[] в "табличный" формат с явной колонкой % для сортировки.
  const columns = useMemo(
    () => [
      { name: "event_type" },
      { name: "events" },
      { name: "total_duration_ms" },
      { name: "avg_duration_ms" },
      { name: "pct" },
    ],
    [],
  );
  const rows = useMemo(
    () =>
      breakdown.map((b) => {
        const pct = totalDurationMs > 0 ? (b.total_duration_ms / totalDurationMs) * 100 : 0;
        return [b.event_type, b.events, b.total_duration_ms, b.avg_duration_ms, pct];
      }),
    [breakdown, totalDurationMs],
  );
  const table = useTableState({ rows, columns, defaultSortKey: "total_duration_ms", defaultSortDir: "desc" });
  const { panelHeadRef, panelStyle } = useStickyTableHead<HTMLDivElement>();

  return (
    <div className={vshellStyles.panel} style={{ marginTop: 12, ...panelStyle }}>
      <div ref={panelHeadRef} className={vshellStyles.panel_head}>
        <div className={vshellStyles.panel_title}>Распределение по типам событий</div>
        {breakdown.length > 0 && (
          <TableFilter
            value={table.filter}
            onChange={table.setFilter}
            total={table.totalRows}
            visible={table.visibleRows}
          />
        )}
      </div>
      <table className={vshellStyles.table}>
        <thead>
          <tr>
            <th {...table.headerProps("event_type")}>Тип</th>
            <th {...table.headerProps("events")}>Событий</th>
            <th {...table.headerProps("total_duration_ms")}>Σ ms</th>
            <th {...table.headerProps("avg_duration_ms")}>avg ms</th>
            <th {...table.headerProps("pct")}>% от Σ</th>
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, ri) => (
            <tr key={ri}>
              <td className={vshellStyles.mono}>{String(row[0])}</td>
              <td className={vshellStyles.mono}>{fmt(Number(row[1]))}</td>
              <td className={vshellStyles.mono}>{fmtMs(Number(row[2]))}</td>
              <td className={vshellStyles.mono}>{fmtMs(Number(row[3]))}</td>
              <td className={vshellStyles.mono}>{Number(row[4]).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "string") return v;
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString("ru-RU") : v.toFixed(2);
  return String(v);
}

function round1(v: number): number {
  return Math.round(v * 10) / 10;
}

function fmt(v: number | undefined | null): string {
  if (v == null) return "—";
  return v.toLocaleString("ru-RU");
}

function fmtMs(v: number | undefined | null): string {
  if (v == null) return "—";
  if (v >= 1000) return (v / 1000).toFixed(2) + " с";
  return v.toFixed(1) + " мс";
}

// Отдельный formatter для wall-clock — у него range от секунд до часов,
// поэтому делаем "5ч 7м" / "12м 30с" / "45с" вместо "18407 с".
function fmtWallClock(v: number | undefined | null): string {
  if (v == null || v <= 0) return "—";
  const total = Math.floor(v / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}ч ${m}м`;
  if (m > 0) return `${m}м ${s}с`;
  return `${s}с`;
}

function fmtTs(v: string | null | undefined): string {
  if (!v) return "—";
  return v.length >= 19 ? v.slice(0, 19).replace("T", " ") : v;
}

const btnStyle: CSSProperties = {
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

const titleOp: CSSProperties = {
  fontFamily: "var(--o-font-mono)",
  fontSize: 14,
  fontWeight: 600,
};

const summaryPanel: CSSProperties = {
  padding: 0,
};

const metricsGrid: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
  gap: 12,
  padding: 16,
};

const metricCard: CSSProperties = {
  background: "var(--o-bg)",
  border: "1px solid var(--o-border-2)",
  borderRadius: 4,
  padding: "8px 12px",
};

const metricLabel: CSSProperties = {
  fontSize: 10.5,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "var(--o-text-3)",
  fontFamily: "var(--o-font-mono)",
  marginBottom: 4,
};

const metaLine: CSSProperties = {
  padding: "0 16px 12px",
  fontSize: 11,
  fontFamily: "var(--o-font-mono)",
  color: "var(--o-text-3)",
};

function metricValue(tone?: "info" | "warn" | "err"): CSSProperties {
  const color = tone === "err" ? "#DC2626" : tone === "warn" ? "#B45309" : tone === "info" ? "var(--o-accent)" : "var(--o-text-1)";
  return {
    fontSize: 18,
    fontWeight: 600,
    color,
    fontFamily: "var(--o-font-mono)",
    fontVariantNumeric: "tabular-nums",
  };
}
