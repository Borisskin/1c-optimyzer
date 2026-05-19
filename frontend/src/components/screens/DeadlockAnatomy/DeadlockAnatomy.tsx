import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
import { backend, type DeadlockAnatomyResult, type ViewResult } from "@/api/backend";
import { ViewShell } from "@/components/views/ViewShell";
import { ExplainerCard } from "@/components/explainer/ExplainerCard";
import { useTableState } from "@/components/tables/useTableState";
import { TableFilter } from "@/components/tables/TableFilter";
import { useAppStore } from "@/store/appStore";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

export function DeadlockAnatomyScreen({ archiveId }: Props) {
  const eventId = useAppStore((s) => s.selectedDeadlockEventId);
  const setEventId = useAppStore((s) => s.setSelectedDeadlockEventId);
  const [list, setList] = useState<ViewResult | null>(null);
  const [anatomy, setAnatomy] = useState<DeadlockAnatomyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!archiveId) return;
    let cancelled = false;
    backend
      .viewListDeadlocks(archiveId, 200)
      .then((res) => {
        if (!cancelled) setList(res);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [archiveId]);

  useEffect(() => {
    if (!archiveId || !eventId) {
      setAnatomy(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    backend
      .viewDeadlockAnatomy(archiveId, eventId, 30)
      .then((res) => {
        if (cancelled) return;
        if (!res.ok) {
          setError(res.error ?? "Ошибка");
          setAnatomy(null);
        } else {
          setAnatomy(res);
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
  }, [archiveId, eventId]);

  if (!archiveId) {
    return (
      <ViewShell breadcrumbs={["Анализ", "Анатомия дедлока"]} title={<>Анатомия дедлока</>}>
        <div className={vshellStyles.panel}>
          <div className={vshellStyles.empty}>Загрузите архив</div>
        </div>
      </ViewShell>
    );
  }

  // Когда eventId выбран — добавляем промежуточную крошку "Список" которая
  // возвращает к перечню deadlock-событий (сброс eventId).
  const breadcrumbs = eventId
    ? ["Анализ", { label: "Список дедлоков", onClick: () => setEventId(null) }, `Дедлок #${eventId}`]
    : ["Анализ", "Анатомия дедлока"];

  const noDeadlocks = list && list.ok && (list.row_count ?? 0) === 0;

  return (
    <ViewShell
      breadcrumbs={breadcrumbs}
      title={<>Анатомия дедлока</>}
      sub="TDEADLOCK events — кто кого заблокировал, на каких ресурсах"
      right={
        eventId !== null && (
          <button
            type="button"
            style={btnStyle}
            onClick={() => setEventId(null)}
          >
            ← К списку дедлоков
          </button>
        )
      }
    >
      {error && <div className={vshellStyles.error}>{error}</div>}

      {/* Список — если ничего не выбрано или нет deadlock'ов */}
      {!eventId && (
        <DeadlockListPanel
          list={list}
          noDeadlocks={noDeadlocks}
          onSelect={(id) => setEventId(id)}
        />
      )}

      {/* Anatomy view */}
      {eventId && loading && <div className={vshellStyles.loading}>Загрузка…</div>}
      {eventId && !loading && anatomy && !anatomy.found && (
        <div className={vshellStyles.panel}>
          <div className={vshellStyles.empty}>
            TDEADLOCK event #{eventId} не найден
          </div>
        </div>
      )}
      {eventId && !loading && anatomy && anatomy.found && anatomy.event && anatomy.parsed_extra && (
        <>
          <ExplainerCard
            archiveId={archiveId}
            anatomyKind="deadlock"
            targetId={String(eventId)}
            features={{
              event_type: "TDEADLOCK",
              regions_count: anatomy.parsed_extra.regions.length,
              first_region: anatomy.parsed_extra.regions[0]?.object_name ?? "",
              participants_count: anatomy.participants?.length ?? 0,
            }}
            anatomyData={{
              event: anatomy.event,
              regions: anatomy.parsed_extra.regions,
              wait_connections: anatomy.parsed_extra.wait_connections,
              edges: anatomy.parsed_extra.edges,
              participants: anatomy.participants,
            }}
          />

          {/* Header */}
          <div className={vshellStyles.panel}>
            <div className={vshellStyles.panel_head}>
              <div className={vshellStyles.panel_title}>
                Дедлок #{anatomy.event.id} · {fmtTs(anatomy.event.ts)}
              </div>
            </div>
            <div style={metaGrid}>
              <Field label="Сессия">{anatomy.event.session_id ?? "—"}</Field>
              <Field label="Пользователь">{anatomy.event.user_name ?? "—"}</Field>
              <Field label="Процесс">
                {anatomy.event.process_role ?? "—"}-{anatomy.event.process_pid ?? "—"}
              </Field>
              <Field label="Длительность">{fmtMs(anatomy.event.duration_ms)}</Field>
            </div>
            {anatomy.event.context && (
              <div style={ctxLine}>Context: {anatomy.event.context}</div>
            )}
          </div>

          {/* Lock graph */}
          {anatomy.parsed_extra.edges.length > 0 && (
            <div className={vshellStyles.panel} style={{ marginTop: 12 }}>
              <div className={vshellStyles.panel_head}>
                <div className={vshellStyles.panel_title}>Граф блокировок</div>
              </div>
              <LockGraph edges={anatomy.parsed_extra.edges} />
            </div>
          )}

          {/* Participants */}
          <div className={vshellStyles.panel} style={{ marginTop: 12 }}>
            <div className={vshellStyles.panel_head}>
              <div className={vshellStyles.panel_title}>
                Участники ({anatomy.participants?.length ?? 0})
              </div>
            </div>
            <div style={{ padding: 12 }}>
              {(anatomy.participants ?? []).map((p) => (
                <span key={p} style={chipStyle}>
                  conn:{p}
                </span>
              ))}
              {anatomy.parsed_extra.wait_connections.length > 0 && (
                <div style={{ marginTop: 8, fontSize: 11, color: "var(--o-text-3)" }}>
                  WaitConnections: {anatomy.parsed_extra.wait_connections.join(", ")}
                </div>
              )}
            </div>
          </div>

          {/* Resources */}
          <div className={vshellStyles.panel} style={{ marginTop: 12 }}>
            <div className={vshellStyles.panel_head}>
              <div className={vshellStyles.panel_title}>
                Ресурсы блокировки ({anatomy.parsed_extra.regions.length})
              </div>
            </div>
            {anatomy.parsed_extra.regions.length === 0 ? (
              <div className={vshellStyles.empty}>
                В extra JSON нет полей Regions/Locks
              </div>
            ) : (
              <table className={vshellStyles.table}>
                <thead>
                  <tr>
                    <th>Объект</th>
                    <th>Режим</th>
                  </tr>
                </thead>
                <tbody>
                  {anatomy.parsed_extra.regions.map((r, i) => (
                    <tr key={i}>
                      <td className={vshellStyles.mono}>{r.object_name}</td>
                      <td className={vshellStyles.mono}>{r.mode ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Surrounding events */}
          {anatomy.surrounding && anatomy.surrounding.row_count > 0 && (
            <SurroundingPanel
              columns={anatomy.surrounding.columns}
              rows={anatomy.surrounding.rows}
              windowSeconds={anatomy.surrounding.window_seconds}
            />
          )}

          {/* Raw extra (collapsed by default would be nice; for now always visible) */}
          <div className={vshellStyles.panel} style={{ marginTop: 12 }}>
            <div className={vshellStyles.panel_head}>
              <div className={vshellStyles.panel_title}>Полный extra payload (raw)</div>
            </div>
            <pre style={rawJsonStyle}>
              {JSON.stringify(anatomy.parsed_extra.raw_extra, null, 2)}
            </pre>
          </div>
        </>
      )}
    </ViewShell>
  );
}

function DeadlockListPanel({
  list,
  noDeadlocks,
  onSelect,
}: {
  list: ViewResult | null;
  noDeadlocks: boolean | null;
  onSelect: (id: number) => void;
}) {
  const columns = list?.columns ?? [];
  const rawRows = list?.rows ?? [];
  const table = useTableState({
    rows: rawRows,
    columns,
    defaultSortKey: "ts",
    defaultSortDir: "desc",
  });
  return (
    <div className={vshellStyles.panel}>
      <div className={vshellStyles.panel_head}>
        <div className={vshellStyles.panel_title}>
          TDEADLOCK events ({list?.row_count ?? 0})
        </div>
        {rawRows.length > 0 && (
          <TableFilter
            value={table.filter}
            onChange={table.setFilter}
            total={table.totalRows}
            visible={table.visibleRows}
          />
        )}
      </div>
      {noDeadlocks && (
        <div className={vshellStyles.empty}>
          В архиве нет TDEADLOCK событий.
          <div style={{ marginTop: 8, fontSize: 11, color: "var(--o-text-3)" }}>
            Проверь logcfg.xml — нужен filter для TDEADLOCK events.
            Подробнее в docs/EXTRA_JSON_FIELD_STUDY.md.
          </div>
        </div>
      )}
      {!noDeadlocks && rawRows.length > 0 && (
        <div className={vshellStyles.table_wrap}>
          <table className={vshellStyles.table}>
            <thead>
              <tr>
                <th {...table.headerProps("id")}>id</th>
                <th {...table.headerProps("ts")}>Время</th>
                <th {...table.headerProps("session_id")}>Сессия</th>
                <th {...table.headerProps("process_role")}>Роль</th>
                <th {...table.headerProps("process_pid")}>PID</th>
                <th {...table.headerProps("context_normalized")}>Контекст</th>
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, ri) => (
                <tr
                  key={ri}
                  className={vshellStyles.clickable}
                  onClick={() => onSelect(Number(row[0]))}
                  title="Клик — открыть анатомию"
                >
                  <td className={vshellStyles.mono}>{String(row[0])}</td>
                  <td className={vshellStyles.mono}>{fmtTs(row[1])}</td>
                  <td className={vshellStyles.mono}>{String(row[2] ?? "—")}</td>
                  <td>{String(row[3] ?? "—")}</td>
                  <td className={vshellStyles.mono}>{String(row[4] ?? "—")}</td>
                  <td className={vshellStyles.mono} style={ctxCell}>
                    {String(row[5] ?? "—")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SurroundingPanel({
  columns,
  rows,
  windowSeconds,
}: {
  columns: { name: string }[];
  rows: unknown[][];
  windowSeconds: number;
}) {
  const table = useTableState({
    rows,
    columns,
    defaultSortKey: "ts",
    defaultSortDir: "asc",
  });
  return (
    <div className={vshellStyles.panel} style={{ marginTop: 12 }}>
      <div className={vshellStyles.panel_head}>
        <div className={vshellStyles.panel_title}>
          События ±{windowSeconds}с ({rows.length})
        </div>
        {rows.length > 0 && (
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
              {columns.map((c) => (
                <th key={c.name} {...table.headerProps(c.name)}>{c.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => (
                  <td key={ci} className={vshellStyles.mono}>
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LockGraph({ edges }: { edges: { waiter: string; blocker: string; resource: string }[] }) {
  // Берём уникальных участников
  const participants = Array.from(
    new Set(edges.flatMap((e) => [e.waiter, e.blocker])),
  );
  const N = participants.length;
  if (N === 0) return null;

  // Простая раскладка по окружности
  const cx = 200;
  const cy = 130;
  const r = 90;
  const positions: Record<string, { x: number; y: number }> = {};
  participants.forEach((p, i) => {
    const angle = (2 * Math.PI * i) / N - Math.PI / 2;
    positions[p] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });

  return (
    <div style={{ padding: 12 }}>
      <svg width="400" height="280" viewBox="0 0 400 280">
        {/* edges (arrows) */}
        {edges.map((e, i) => {
          const a = positions[e.waiter];
          const b = positions[e.blocker];
          if (!a || !b) return null;
          // Сместить наконечник к окружности узла (радиус 24)
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const len = Math.sqrt(dx * dx + dy * dy) || 1;
          const ux = dx / len;
          const uy = dy / len;
          const ax = a.x + ux * 26;
          const ay = a.y + uy * 26;
          const bx = b.x - ux * 26;
          const by = b.y - uy * 26;
          const midX = (ax + bx) / 2;
          const midY = (ay + by) / 2;
          return (
            <g key={i}>
              <line
                x1={ax} y1={ay} x2={bx} y2={by}
                stroke="#DC2626"
                strokeWidth={1.5}
                markerEnd="url(#arr)"
              />
              <text x={midX + 6} y={midY - 4} fontSize="10" fontFamily="var(--o-font-mono)" fill="#525252">
                {e.resource.length > 24 ? e.resource.slice(0, 24) + "…" : e.resource}
              </text>
            </g>
          );
        })}
        {/* nodes */}
        {participants.map((p) => {
          const pos = positions[p];
          return (
            <g key={p}>
              <circle cx={pos.x} cy={pos.y} r={24} fill="#FEE2E2" stroke="#DC2626" strokeWidth={1.5} />
              <text x={pos.x} y={pos.y + 4} fontSize="11" textAnchor="middle" fontFamily="var(--o-font-mono)" fill="#7F1D1D">
                {p.length > 6 ? p.slice(0, 6) : p}
              </text>
            </g>
          );
        })}
        <defs>
          <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#DC2626" />
          </marker>
        </defs>
      </svg>
      <div style={{ fontSize: 11, color: "var(--o-text-3)", marginTop: 8 }}>
        Стрелка: сессия (waiter) → сессия (blocker), хранитель ресурса.
        Замкнутая цепочка стрелок = циклический deadlock.
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={fieldLabel}>{label}</div>
      <div style={fieldValue}>{children}</div>
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "string") return v;
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString("ru-RU") : v.toFixed(2);
  return String(v);
}

function fmtTs(v: unknown): string {
  if (v == null) return "—";
  const s = String(v);
  return s.length >= 19 ? s.slice(0, 19).replace("T", " ") : s;
}

function fmtMs(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1000) return (v / 1000).toFixed(2) + " с";
  return v.toFixed(1) + " мс";
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

const ctxCell: CSSProperties = {
  maxWidth: 400,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

const metaGrid: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
  gap: 12,
  padding: 16,
};

const ctxLine: CSSProperties = {
  padding: "0 16px 12px",
  fontFamily: "var(--o-font-mono)",
  fontSize: 11,
  color: "var(--o-text-2)",
};

const fieldLabel: CSSProperties = {
  fontSize: 10.5,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "var(--o-text-3)",
  fontFamily: "var(--o-font-mono)",
  marginBottom: 4,
};

const fieldValue: CSSProperties = {
  fontSize: 13,
  fontWeight: 500,
  color: "var(--o-text-1)",
  fontFamily: "var(--o-font-mono)",
};

const chipStyle: CSSProperties = {
  display: "inline-block",
  padding: "4px 10px",
  margin: "0 6px 6px 0",
  background: "#FEE2E2",
  color: "#7F1D1D",
  borderRadius: 4,
  fontSize: 11,
  fontFamily: "var(--o-font-mono)",
};

const rawJsonStyle: CSSProperties = {
  margin: 0,
  padding: 16,
  fontFamily: "var(--o-font-mono)",
  fontSize: 11,
  color: "var(--o-text-2)",
  background: "var(--o-codebox-bg)",
  overflow: "auto",
};
