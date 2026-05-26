// Multi-archive comparison screen (Sprint 2 Phase G, ADR-018).
// Killer-фича portfolio: side-by-side diff baseline vs compared archive.
// Phase G минимум — summary + slow queries diff. Errors/Duration/Roles diff
// можно добавить позднее тем же паттерном.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { Badge, Tabs } from "@/components/primitives/Primitives";
import {
  backend,
  type CompareSlowQueriesResult,
  type CompareSummaryResult,
  type RegressionComputeResult,
  type RegressionResultDto,
  type StoredArchive,
} from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { ViewShell } from "@/components/views/ViewShell";
import { useTableState } from "@/components/tables/useTableState";
import { TableFilter } from "@/components/tables/TableFilter";
import vshellStyles from "@/components/views/ViewShell.module.css";

type Slot = "a" | "b";
type Tab = "summary" | "slow_queries" | "regression";

export function ArchiveComparisonScreen() {
  const [archives, setArchives] = useState<StoredArchive[]>([]);
  const [slotA, setSlotA] = useState<string | null>(null);
  const [slotB, setSlotB] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("summary");
  const [summary, setSummary] = useState<CompareSummaryResult | null>(null);
  const [slowDiff, setSlowDiff] = useState<CompareSlowQueriesResult | null>(null);
  const [regression, setRegression] = useState<RegressionComputeResult | null>(null);
  const [regressionLoading, setRegressionLoading] = useState(false);
  const [regressionThreshold, setRegressionThreshold] = useState(2.0);
  const [regressionMinSamples, setRegressionMinSamples] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pushToast = useAppStore((s) => s.pushToast);

  const refreshArchives = useCallback(() => {
    backend
      .listStoredArchives()
      .then((r) => setArchives(r.archives.filter((a) => !a.is_orphan)))
      .catch((e) => pushToast(String(e), "err"));
  }, [pushToast]);

  useEffect(() => {
    refreshArchives();
  }, [refreshArchives]);

  const runCompare = useCallback(async () => {
    if (!slotA || !slotB) return;
    setLoading(true);
    setError(null);
    try {
      const [s, q] = await Promise.all([
        backend.compareSummary(slotA, slotB),
        backend.compareSlowQueries(slotA, slotB, 50),
      ]);
      setSummary(s);
      setSlowDiff(q);
      if (!s.ok) setError(s.error ?? "Ошибка");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [slotA, slotB]);

  const runRegression = useCallback(async () => {
    if (!slotA || !slotB) return;
    setRegressionLoading(true);
    try {
      const r = await backend.regressionCompute(
        slotA,
        slotB,
        regressionThreshold,
        regressionMinSamples,
        50,
      );
      setRegression(r);
    } catch (e) {
      setRegression({ ok: false, error: String(e) });
    } finally {
      setRegressionLoading(false);
    }
  }, [slotA, slotB, regressionThreshold, regressionMinSamples]);

  useEffect(() => {
    if (slotA && slotB && slotA !== slotB) {
      runCompare();
      runRegression();
    } else {
      setSummary(null);
      setSlowDiff(null);
      setRegression(null);
    }
  }, [slotA, slotB, runCompare, runRegression]);

  return (
    <ViewShell
      breadcrumbs={["Конфигурация", "Сравнение"]}
      title={
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          Сравнение архивов <Badge tone="teal">Killer</Badge>
        </span>
      }
      sub="Baseline vs Compared — найди регрессии после релиза"
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <ArchivePicker
          slot="a"
          label="Архив A — Baseline"
          archives={archives}
          value={slotA}
          onChange={setSlotA}
          oppositeValue={slotB}
        />
        <ArchivePicker
          slot="b"
          label="Архив B — Compared"
          archives={archives}
          value={slotB}
          onChange={setSlotB}
          oppositeValue={slotA}
        />
      </div>

      <div className={vshellStyles.panel}>
        <div className={vshellStyles.panel_head}>
          <Tabs
            value={tab}
            onChange={(v) => setTab(v as Tab)}
            dense
            tabs={[
              { id: "summary", label: "Сводка", icon: "Trend" },
              { id: "slow_queries", label: "Slow Queries", icon: "Database" },
              { id: "regression", label: "Регрессии операций", icon: "AlertTriangle" },
            ]}
          />
        </div>

        {!slotA || !slotB ? (
          <div className={vshellStyles.empty}>Выберите два разных архива выше</div>
        ) : loading ? (
          <div className={vshellStyles.loading}>Сравнение…</div>
        ) : error ? (
          <div className={vshellStyles.error}>{error}</div>
        ) : tab === "summary" ? (
          <SummaryTab summary={summary} />
        ) : tab === "slow_queries" ? (
          <SlowQueriesTab diff={slowDiff} />
        ) : (
          <RegressionTab
            result={regression}
            loading={regressionLoading}
            threshold={regressionThreshold}
            onThresholdChange={setRegressionThreshold}
            minSamples={regressionMinSamples}
            onMinSamplesChange={setRegressionMinSamples}
            onRefresh={runRegression}
          />
        )}
      </div>
    </ViewShell>
  );
}

function ArchivePicker({
  slot,
  label,
  archives,
  value,
  onChange,
  oppositeValue,
}: {
  slot: Slot;
  label: string;
  archives: StoredArchive[];
  value: string | null;
  onChange: (id: string | null) => void;
  oppositeValue: string | null;
}) {
  const current = archives.find((a) => a.archive_id === value);
  return (
    <div className={vshellStyles.panel}>
      <div className={vshellStyles.panel_title} style={{ marginBottom: 8 }}>
        {label}
      </div>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        style={{
          width: "100%",
          padding: "8px 10px",
          fontSize: 12,
          border: "1px solid var(--o-border-2)",
          borderRadius: 4,
          background: "var(--o-panel)",
          color: "var(--o-text-1)",
          marginBottom: 8,
        }}
      >
        <option value="">— Выберите архив —</option>
        {archives.map((a) => (
          <option
            key={a.archive_id}
            value={a.archive_id}
            disabled={a.archive_id === oppositeValue}
          >
            {pathTail(a.path)} · {fmt(a.events_count)} событий
          </option>
        ))}
      </select>
      {current && (
        <div
          style={{
            fontSize: 11,
            color: "var(--o-text-3)",
            fontFamily: "var(--o-font-mono)",
          }}
        >
          <div>{current.path}</div>
          <div>
            {fmt(current.events_count)} событий · {fmtBytes(current.size_bytes)} · загружен{" "}
            {short(current.loaded_at)}
          </div>
        </div>
      )}
      {slot === "a" && !current && (
        <div className={vshellStyles.panel_sub}>Подсказка: A = до релиза.</div>
      )}
      {slot === "b" && !current && (
        <div className={vshellStyles.panel_sub}>Подсказка: B = после релиза.</div>
      )}
    </div>
  );
}

function SummaryTab({ summary }: { summary: CompareSummaryResult | null }) {
  const columns = useMemo(
    () => [
      { name: "label" },
      { name: "a" },
      { name: "b" },
      { name: "delta" },
      { name: "delta_percent" },
      { name: "key" },
    ],
    [],
  );
  const tableRows = useMemo(() => {
    if (!summary?.metrics) return [];
    return summary.metrics.map((m) => [m.label, m.a, m.b, m.delta, m.delta_percent, m.key]);
  }, [summary]);
  const table = useTableState({ rows: tableRows, columns });

  if (!summary || !summary.metrics) return null;
  return (
    <div>
      {tableRows.length > 0 && (
        <div style={{ display: "flex", justifyContent: "flex-end", padding: "0 0 8px" }}>
          <TableFilter
            value={table.filter}
            onChange={table.setFilter}
            total={table.totalRows}
            visible={table.visibleRows}
          />
        </div>
      )}
      <div className={vshellStyles.table_wrap}>
        <table className={vshellStyles.table}>
          <thead>
            <tr>
              <th {...table.headerProps("label")}>Метрика</th>
              <th {...table.headerProps("a")}>Baseline</th>
              <th {...table.headerProps("b")}>Compared</th>
              <th {...table.headerProps("delta")}>Δ</th>
              <th {...table.headerProps("delta_percent")}>Δ%</th>
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => {
              const [label, a, b, delta, deltaPercent, key] = row as [
                string,
                number,
                number,
                number,
                number | null,
                string,
              ];
              const tone = deltaTone(deltaPercent, key);
              return (
                <tr key={ri}>
                  <td>{label}</td>
                  <td className={vshellStyles.mono}>{fmtNumber(a)}</td>
                  <td className={vshellStyles.mono}>{fmtNumber(b)}</td>
                  <td className={vshellStyles.mono}>{fmtNumber(delta)}</td>
                  <td className={vshellStyles.mono} style={{ color: tone }}>
                    {deltaPercent === null ? "—" : `${deltaPercent > 0 ? "+" : ""}${deltaPercent.toFixed(1)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SlowQueriesTab({ diff }: { diff: CompareSlowQueriesResult | null }) {
  if (!diff) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {diff.regressed && diff.regressed.length > 0 && (
        <Section
          title={
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Icon name="AlertTriangle" size={12} color="var(--o-err)" /> Регрессии (
              {diff.regressed.length})
            </span>
          }
          rows={diff.regressed}
        />
      )}
      {diff.improved && diff.improved.length > 0 && (
        <Section
          title={
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Icon name="Check" size={12} color="var(--o-ok)" /> Улучшения (
              {diff.improved.length})
            </span>
          }
          rows={diff.improved}
        />
      )}
      {diff.only_b && diff.only_b.length > 0 && (
        <OnlySection title={`Новые запросы в Compared (${diff.only_b.length})`} rows={diff.only_b} />
      )}
      {diff.only_a && diff.only_a.length > 0 && (
        <OnlySection title={`Исчезли в Compared (${diff.only_a.length})`} rows={diff.only_a} />
      )}
      {(!diff.regressed || diff.regressed.length === 0) &&
        (!diff.improved || diff.improved.length === 0) &&
        (!diff.only_a || diff.only_a.length === 0) &&
        (!diff.only_b || diff.only_b.length === 0) && (
          <div className={vshellStyles.empty}>Различий не найдено</div>
        )}
    </div>
  );
}

function Section({
  title,
  rows,
}: {
  title: React.ReactNode;
  rows: NonNullable<CompareSlowQueriesResult["regressed"]>;
}) {
  const columns = useMemo(
    () => [
      { name: "query" },
      { name: "a_avg_ms" },
      { name: "b_avg_ms" },
      { name: "delta_percent" },
      { name: "a_calls" },
      { name: "b_calls" },
      { name: "sql_text_hash" },
    ],
    [],
  );
  const tableRows = useMemo(
    () => rows.map((r) => [r.query ?? "—", r.a_avg_ms, r.b_avg_ms, r.delta_percent, r.a_calls, r.b_calls, r.sql_text_hash]),
    [rows],
  );
  const table = useTableState({ rows: tableRows, columns, defaultSortKey: "delta_percent", defaultSortDir: "desc" });
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
        <div className={vshellStyles.panel_title}>{title}</div>
        {tableRows.length > 0 && (
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
              <th {...table.headerProps("query")}>Запрос</th>
              <th {...table.headerProps("a_avg_ms")}>A avg, ms</th>
              <th {...table.headerProps("b_avg_ms")}>B avg, ms</th>
              <th {...table.headerProps("delta_percent")}>Δ%</th>
              <th {...table.headerProps("a_calls")}>Calls A→B</th>
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => {
              const [query, aAvg, bAvg, dPct, aCalls, bCalls, hash] = row as [
                string,
                number,
                number,
                number,
                number,
                number,
                string,
              ];
              return (
                <tr key={`${hash}-${ri}`}>
                  <td title={query}>{truncate(query, 60)}</td>
                  <td className={vshellStyles.mono}>{aAvg.toFixed(1)}</td>
                  <td className={vshellStyles.mono}>{bAvg.toFixed(1)}</td>
                  <td className={vshellStyles.mono} style={{ color: deltaTone(dPct) }}>
                    {dPct > 0 ? "+" : ""}
                    {dPct.toFixed(1)}%
                  </td>
                  <td className={vshellStyles.mono}>
                    {aCalls} → {bCalls}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OnlySection({
  title,
  rows,
}: {
  title: string;
  rows: NonNullable<CompareSlowQueriesResult["only_b"]>;
}) {
  const columns = useMemo(
    () => [
      { name: "query" },
      { name: "calls" },
      { name: "total_ms" },
      { name: "avg_ms" },
      { name: "sql_text_hash" },
    ],
    [],
  );
  const tableRows = useMemo(
    () => rows.map((r) => [r.query ?? "—", r.calls, r.total_ms, r.avg_ms, r.sql_text_hash]),
    [rows],
  );
  const table = useTableState({ rows: tableRows, columns, defaultSortKey: "total_ms", defaultSortDir: "desc" });
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
        <div className={vshellStyles.panel_title}>{title}</div>
        {tableRows.length > 0 && (
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
              <th {...table.headerProps("query")}>Запрос</th>
              <th {...table.headerProps("calls")}>Calls</th>
              <th {...table.headerProps("total_ms")}>Σ ms</th>
              <th {...table.headerProps("avg_ms")}>avg ms</th>
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => {
              const [query, calls, totalMs, avgMs, hash] = row as [
                string,
                number,
                number,
                number,
                string,
              ];
              return (
                <tr key={`${hash}-${ri}`}>
                  <td title={query}>{truncate(query, 60)}</td>
                  <td className={vshellStyles.mono}>{calls}</td>
                  <td className={vshellStyles.mono}>{totalMs.toFixed(0)}</td>
                  <td className={vshellStyles.mono}>{avgMs.toFixed(1)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function deltaTone(delta: number | null, metricKey?: string): string {
  if (delta === null) return "var(--o-text-3)";
  // По умолчанию рост = плохо (длительности/errors); для events_count трактуем neutral.
  if (metricKey === "events_count") return "var(--o-text-1)";
  if (delta >= 50) return "var(--o-err)";
  if (delta >= 20) return "var(--o-warn)";
  if (delta <= -30) return "var(--o-ok)";
  return "var(--o-text-2)";
}

function fmt(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toLocaleString("ru-RU");
}

function fmtNumber(v: number): string {
  if (!Number.isFinite(v)) return "—";
  if (Math.abs(v) >= 10000) return v.toLocaleString("ru-RU");
  return v.toFixed(2);
}

function fmtBytes(b: number): string {
  if (b < 1024) return `${b} Б`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} КБ`;
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} МБ`;
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} ГБ`;
}

function short(iso: string): string {
  if (iso.length >= 16) return iso.slice(0, 16).replace("T", " ");
  return iso;
}

function pathTail(p: string): string {
  const parts = p.split(/[\\/]/);
  return parts[parts.length - 1] || p;
}

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n) + "…";
}

// ============================================================================
// Sprint 11 Phase F — Regression UI
// ============================================================================

const CHANGE_TYPE_LABEL: Record<string, string> = {
  regression: "Регрессии",
  improvement: "Улучшения",
  new: "Новые",
  disappeared: "Исчезли",
  stable: "Стабильно",
};

const CONFIDENCE_LABEL: Record<string, string> = {
  high: "высокая",
  medium: "средняя",
  low: "низкая",
};

function RegressionTab({
  result,
  loading,
  threshold,
  onThresholdChange,
  minSamples,
  onMinSamplesChange,
  onRefresh,
}: {
  result: RegressionComputeResult | null;
  loading: boolean;
  threshold: number;
  onThresholdChange: (v: number) => void;
  minSamples: number;
  onMinSamplesChange: (v: number) => void;
  onRefresh: () => void;
}) {
  if (loading) {
    return <div className={vshellStyles.loading}>Анализ регрессий операций…</div>;
  }
  if (!result) return null;
  if (!result.ok) {
    return <div className={vshellStyles.error}>{result.error ?? "Ошибка"}</div>;
  }
  const s = result.summary;
  if (!s) return <div className={vshellStyles.empty}>Нет данных</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Контролы */}
      <div
        style={{
          display: "flex",
          gap: 16,
          alignItems: "center",
          padding: "8px 12px",
          background: "var(--o-panel)",
          border: "1px solid var(--o-border-2)",
          borderRadius: 4,
        }}
      >
        <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
          Порог регрессии:
          <input
            type="number"
            min={1.5}
            max={10}
            step={0.5}
            value={threshold}
            onChange={(e) => onThresholdChange(Math.max(1.5, parseFloat(e.target.value) || 2.0))}
            style={{
              width: 60,
              padding: "4px 6px",
              fontSize: 12,
              border: "1px solid var(--o-border-2)",
              borderRadius: 3,
              background: "var(--o-bg)",
              color: "var(--o-text-1)",
            }}
          />
          ×
        </label>
        <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
          Мин. кол-во вызовов:
          <input
            type="number"
            min={1}
            max={1000}
            value={minSamples}
            onChange={(e) => onMinSamplesChange(Math.max(1, parseInt(e.target.value) || 5))}
            style={{
              width: 60,
              padding: "4px 6px",
              fontSize: 12,
              border: "1px solid var(--o-border-2)",
              borderRadius: 3,
              background: "var(--o-bg)",
              color: "var(--o-text-1)",
            }}
          />
        </label>
        <button
          type="button"
          onClick={onRefresh}
          style={{
            padding: "4px 12px",
            fontSize: 12,
            border: "1px solid var(--o-border-2)",
            borderRadius: 3,
            background: "var(--o-accent)",
            color: "white",
            cursor: "pointer",
          }}
        >
          Применить
        </button>
      </div>

      {/* Summary */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 8,
        }}
      >
        <SummaryCard label="🔴 Регрессии" value={s.total_regressions} tone="err" />
        <SummaryCard label="🟢 Улучшения" value={s.total_improvements} tone="ok" />
        <SummaryCard label="🆕 Новые" value={s.total_new} tone="info" />
        <SummaryCard label="❌ Исчезли" value={s.total_disappeared} tone="muted" />
        <SummaryCard label="➖ Стабильно" value={s.total_stable} tone="muted" />
      </div>

      {/* Regressions table — top priority */}
      {result.regressions && result.regressions.length > 0 && (
        <RegressionSection
          title={
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Icon name="AlertTriangle" size={12} color="var(--o-err)" />
              Регрессии ({result.regressions.length})
            </span>
          }
          rows={result.regressions}
          changeType="regression"
        />
      )}

      {/* Improvements */}
      {result.improvements && result.improvements.length > 0 && (
        <RegressionSection
          title={
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Icon name="Check" size={12} color="var(--o-ok)" />
              Улучшения ({result.improvements.length})
            </span>
          }
          rows={result.improvements}
          changeType="improvement"
        />
      )}

      {/* New */}
      {result.new && result.new.length > 0 && (
        <RegressionSection
          title={`🆕 Новые операции (${result.new.length})`}
          rows={result.new}
          changeType="new"
        />
      )}

      {/* Disappeared */}
      {result.disappeared && result.disappeared.length > 0 && (
        <RegressionSection
          title={`❌ Исчезли (${result.disappeared.length})`}
          rows={result.disappeared}
          changeType="disappeared"
        />
      )}

      {result.regressions?.length === 0 &&
        result.improvements?.length === 0 &&
        result.new?.length === 0 &&
        result.disappeared?.length === 0 && (
          <div className={vshellStyles.empty}>
            Регрессий не найдено. Все операции работают в пределах порога ({threshold}×).
          </div>
        )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "err" | "ok" | "info" | "muted";
}) {
  const colors: Record<string, string> = {
    err: "var(--o-err)",
    ok: "var(--o-ok)",
    info: "var(--o-info, #4a9eff)",
    muted: "var(--o-text-3)",
  };
  return (
    <div
      style={{
        padding: "12px 16px",
        background: "var(--o-panel)",
        border: "1px solid var(--o-border-2)",
        borderRadius: 4,
      }}
    >
      <div style={{ fontSize: 11, color: "var(--o-text-3)" }}>{label}</div>
      <div
        style={{
          fontSize: 22,
          fontWeight: 600,
          color: colors[tone],
          marginTop: 4,
          fontFamily: "var(--o-font-mono)",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function RegressionSection({
  title,
  rows,
  changeType,
}: {
  title: React.ReactNode;
  rows: RegressionResultDto[];
  changeType: string;
}) {
  return (
    <div>
      <div className={vshellStyles.panel_title} style={{ marginBottom: 8 }}>
        {title}
      </div>
      <div className={vshellStyles.table_wrap}>
        <table className={vshellStyles.table}>
          <thead>
            <tr>
              <th>Операция</th>
              <th>p95 baseline → current, мс</th>
              <th>Δ</th>
              <th>Вызовов A→B</th>
              <th>Достоверность</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <RegressionRow key={`${r.operation_name}-${idx}`} r={r} changeType={changeType} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RegressionRow({
  r,
  changeType,
}: {
  r: RegressionResultDto;
  changeType: string;
}) {
  const baselineP95 = r.baseline_p95_ms;
  const currentP95 = r.current_p95_ms;
  let deltaCell: React.ReactNode = "—";
  let deltaColor = "var(--o-text-2)";
  if (r.p95_ratio !== null && r.p95_ratio !== undefined) {
    const pct = (r.p95_ratio - 1) * 100;
    deltaCell = `${pct > 0 ? "+" : ""}${pct.toFixed(0)}%`;
    if (changeType === "regression") deltaColor = "var(--o-err)";
    else if (changeType === "improvement") deltaColor = "var(--o-ok)";
  } else if (changeType === "regression") {
    deltaCell = "новый bottleneck";
    deltaColor = "var(--o-err)";
  }

  const baselineCell =
    baselineP95 !== null && baselineP95 !== undefined
      ? `${baselineP95.toFixed(0)} → `
      : "— → ";
  const currentCell =
    currentP95 !== null && currentP95 !== undefined ? currentP95.toFixed(0) : "—";

  return (
    <tr>
      <td title={r.context_signature ? `${r.operation_name}\n${r.context_signature}` : r.operation_name}>
        {truncate(r.operation_name, 60)}
      </td>
      <td className={vshellStyles.mono}>
        {baselineCell}
        {currentCell}
      </td>
      <td className={vshellStyles.mono} style={{ color: deltaColor }}>
        {deltaCell}
      </td>
      <td className={vshellStyles.mono}>
        {r.baseline_count ?? "—"} → {r.current_count ?? "—"}
      </td>
      <td style={{ fontSize: 11, color: confidenceColor(r.confidence) }}>
        {CONFIDENCE_LABEL[r.confidence]}
      </td>
    </tr>
  );
}

function confidenceColor(c: string): string {
  if (c === "high") return "var(--o-ok)";
  if (c === "medium") return "var(--o-text-2)";
  return "var(--o-text-3)";
}
