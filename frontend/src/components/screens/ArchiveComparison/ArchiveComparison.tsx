// Multi-archive comparison screen (Sprint 2 Phase G, ADR-018).
// Killer-фича portfolio: side-by-side diff baseline vs compared archive.
// Phase G минимум — summary + slow queries diff. Errors/Duration/Roles diff
// можно добавить позднее тем же паттерном.

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { Badge, Tabs } from "@/components/primitives/Primitives";
import {
  backend,
  type CompareSlowQueriesResult,
  type CompareSummaryResult,
  type StoredArchive,
} from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { ViewShell } from "@/components/views/ViewShell";
import vshellStyles from "@/components/views/ViewShell.module.css";

type Slot = "a" | "b";
type Tab = "summary" | "slow_queries";

export function ArchiveComparisonScreen() {
  const [archives, setArchives] = useState<StoredArchive[]>([]);
  const [slotA, setSlotA] = useState<string | null>(null);
  const [slotB, setSlotB] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("summary");
  const [summary, setSummary] = useState<CompareSummaryResult | null>(null);
  const [slowDiff, setSlowDiff] = useState<CompareSlowQueriesResult | null>(null);
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

  useEffect(() => {
    if (slotA && slotB && slotA !== slotB) {
      runCompare();
    } else {
      setSummary(null);
      setSlowDiff(null);
    }
  }, [slotA, slotB, runCompare]);

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
        ) : (
          <SlowQueriesTab diff={slowDiff} />
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
  if (!summary || !summary.metrics) return null;
  return (
    <div className={vshellStyles.table_wrap}>
      <table className={vshellStyles.table}>
        <thead>
          <tr>
            <th>Метрика</th>
            <th>Baseline</th>
            <th>Compared</th>
            <th>Δ</th>
            <th>Δ%</th>
          </tr>
        </thead>
        <tbody>
          {summary.metrics.map((m) => {
            const tone = deltaTone(m.delta_percent, m.key);
            return (
              <tr key={m.key}>
                <td>{m.label}</td>
                <td className={vshellStyles.mono}>{fmtNumber(m.a)}</td>
                <td className={vshellStyles.mono}>{fmtNumber(m.b)}</td>
                <td className={vshellStyles.mono}>{fmtNumber(m.delta)}</td>
                <td className={vshellStyles.mono} style={{ color: tone }}>
                  {m.delta_percent === null ? "—" : `${m.delta_percent > 0 ? "+" : ""}${m.delta_percent.toFixed(1)}%`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
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
  return (
    <div>
      <div className={vshellStyles.panel_title} style={{ marginBottom: 8 }}>
        {title}
      </div>
      <div className={vshellStyles.table_wrap}>
        <table className={vshellStyles.table}>
          <thead>
            <tr>
              <th>Запрос</th>
              <th>A avg, ms</th>
              <th>B avg, ms</th>
              <th>Δ%</th>
              <th>Calls A→B</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.sql_text_hash}>
                <td title={r.query ?? ""}>{truncate(r.query ?? "—", 60)}</td>
                <td className={vshellStyles.mono}>{r.a_avg_ms.toFixed(1)}</td>
                <td className={vshellStyles.mono}>{r.b_avg_ms.toFixed(1)}</td>
                <td className={vshellStyles.mono} style={{ color: deltaTone(r.delta_percent) }}>
                  {r.delta_percent > 0 ? "+" : ""}
                  {r.delta_percent.toFixed(1)}%
                </td>
                <td className={vshellStyles.mono}>
                  {r.a_calls} → {r.b_calls}
                </td>
              </tr>
            ))}
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
  return (
    <div>
      <div className={vshellStyles.panel_title} style={{ marginBottom: 8 }}>
        {title}
      </div>
      <div className={vshellStyles.table_wrap}>
        <table className={vshellStyles.table}>
          <thead>
            <tr>
              <th>Запрос</th>
              <th>Calls</th>
              <th>Σ ms</th>
              <th>avg ms</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.sql_text_hash}>
                <td title={r.query ?? ""}>{truncate(r.query ?? "—", 60)}</td>
                <td className={vshellStyles.mono}>{r.calls}</td>
                <td className={vshellStyles.mono}>{r.total_ms.toFixed(0)}</td>
                <td className={vshellStyles.mono}>{r.avg_ms.toFixed(1)}</td>
              </tr>
            ))}
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
