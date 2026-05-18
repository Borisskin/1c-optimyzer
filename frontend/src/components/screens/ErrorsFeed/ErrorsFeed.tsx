import type { CSSProperties } from "react";
import { useMemo, useState } from "react";
import { backend } from "@/api/backend";
import { ViewShell } from "@/components/views/ViewShell";
import { colIndex, useView } from "@/components/views/useView";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

export function ErrorsFeedScreen({ archiveId }: Props) {
  const [filter, setFilter] = useState<"all" | "EXCP" | "TDEADLOCK" | "TLOCK">("all");
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewErrorsFeed(archiveId)
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId],
  );

  const rows = useMemo(() => {
    if (!data?.rows) return [] as unknown[][];
    if (filter === "all") return data.rows;
    const idx = colIndex(data.columns);
    return data.rows.filter((r) => String(r[idx["event_type"]]) === filter);
  }, [data, filter]);

  const idx = useMemo(() => colIndex(data?.columns), [data?.columns]);

  return (
    <ViewShell
      breadcrumbs={["Анализ", "Ошибки и исключения"]}
      title={<>Ошибки и исключения</>}
      sub="EXCP / TDEADLOCK / TLOCK — последние сначала"
      right={
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as typeof filter)}
          style={selectStyle}
        >
          <option value="all">Все типы</option>
          <option value="EXCP">EXCP</option>
          <option value="TDEADLOCK">TDEADLOCK</option>
          <option value="TLOCK">TLOCK</option>
        </select>
      }
    >
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.panel_head}>
          <div className={vshellStyles.panel_title}>{rows.length} событий</div>
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
                  <th>Время</th>
                  <th>Тип</th>
                  <th>Роль</th>
                  <th>PID</th>
                  <th>Контекст</th>
                  <th>ms</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => {
                  const tone = badgeTone(String(row[idx["event_type"]] ?? ""));
                  return (
                    <tr key={ri}>
                      <td className={vshellStyles.mono}>{formatTs(row[idx["ts"]])}</td>
                      <td>
                        <span style={badgeStyle(tone)}>{String(row[idx["event_type"]] ?? "")}</span>
                      </td>
                      <td>{String(row[idx["process_role"]] ?? "—")}</td>
                      <td className={vshellStyles.mono}>{String(row[idx["process_pid"]] ?? "—")}</td>
                      <td title={String(row[idx["context"]] ?? "")}>
                        {truncate(String(row[idx["context"]] ?? ""), 60)}
                      </td>
                      <td className={vshellStyles.mono}>{fmtMs(row[idx["duration_ms"]])}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {archiveId && !loading && !error && rows.length === 0 && (
          <div className={vshellStyles.empty}>Нет ошибок и исключений</div>
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

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n) + "…";
}
