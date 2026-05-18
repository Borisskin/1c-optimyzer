import { useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { Badge, KBD, PageHeader, Tabs, Th, Td } from "@/components/primitives/Primitives";
import { backend } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import styles from "./OQLConsole.module.css";

const SPRINT_0_PLACEHOLDER = `// OptimyzerQL — DSL parser появится в Sprint 1.
// Sprint 0 поддерживает только preset-запросы.
// Выберите один из templates ниже, чтобы запустить:
//
//   • First 100 events       — первые 100 событий по времени
//   • Longest 100 events     — самые длинные события по duration_us
//   • Deadlocks              — только TDEADLOCK события
`;

type ResultTab = "table" | "chart" | "timeline" | "raw";

type PresetId = "first_100" | "longest" | "deadlocks";

interface PresetSpec {
  id: PresetId;
  label: string;
}

const PRESETS: PresetSpec[] = [
  { id: "first_100", label: "First 100 events" },
  { id: "longest",   label: "Longest 100 events" },
  { id: "deadlocks", label: "Deadlocks" },
];

export function OQLConsoleScreen({ onLoadArchive }: { onLoadArchive: () => void }) {
  const [rtab, setRtab] = useState<ResultTab>("table");
  const [running, setRunning] = useState<PresetId | null>(null);
  const archive = useAppStore((s) => s.archive);
  const lastResult = useAppStore((s) => s.lastResult);
  const setLastResult = useAppStore((s) => s.setLastResult);
  const pushToast = useAppStore((s) => s.pushToast);

  const ready = archive?.status === "ready";

  async function runPreset(id: PresetId) {
    if (!archive || !ready) return;
    setRunning(id);
    try {
      const r = await backend.queryEventsPreset(archive.archive_id, id, 100);
      setLastResult(r);
      pushToast(`${id}: ${r.total_count} rows · ${r.executed_in_ms.toFixed(0)} ms`, "ok");
    } catch (e) {
      pushToast(`Query failed: ${e}`, "err");
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className={styles.screen}>
      <PageHeader
        breadcrumbs={["Manage", "OptimyzerQL Console"]}
        title={
          <span className={styles.title_inline}>
            OptimyzerQL Console <Badge tone="teal">free tier</Badge>
            <Badge tone="mute">Sprint 0 · preset only</Badge>
          </span>
        }
        sub="declarative query language over technical journal · DSL parser — Sprint 1"
        right={
          <>
            <button className={styles.btn} disabled title="Templates library — Sprint 1">
              <Icon name="Book" size={11} />Templates
            </button>
            <button className={styles.btn} disabled title="Docs panel — Sprint 1">
              <Icon name="FileText" size={11} />Docs
            </button>
            <button className={styles.btn} disabled title="Sharing — Sprint 2">
              <Icon name="Share" size={11} />Share
            </button>
            <button className={styles.btn_primary} disabled title="OQL execution — Sprint 1">
              <Icon name="Play" size={11} />Run <KBD>⌘↵</KBD>
            </button>
          </>
        }
      />

      <div className={styles.workarea}>
        <section className={styles.editor_pane}>
          <div className={styles.pane_head}>
            <span className={styles.tab_label}>
              <Icon name="FileText" size={11} color="var(--o-text-3)" /> untitled.oql
            </span>
            <Badge tone="mute">read-only</Badge>
            <span className={styles.cursor_info}>ln 1 · col 1 · 0 rows</span>
          </div>
          <textarea
            className={styles.editor}
            readOnly
            value={SPRINT_0_PLACEHOLDER}
          />
        </section>

        <section className={styles.results_pane}>
          <div className={styles.pane_head}>
            <Tabs
              value={rtab}
              onChange={(v) => setRtab(v as ResultTab)}
              dense
              tabs={[
                { id: "table",    label: "Table",    icon: "FlaskList", count: lastResult?.total_count },
                { id: "chart",    label: "Chart",    icon: "Trend" },
                { id: "timeline", label: "Timeline", icon: "Activity" },
                { id: "raw",      label: "Raw JSON", icon: "Code" },
              ]}
            />
            {lastResult && (
              <span className={styles.exec_info}>
                <span>{lastResult.total_count} rows</span>
                <span>executed in {lastResult.executed_in_ms.toFixed(0)} ms</span>
                {lastResult.truncated && <Badge tone="warn">truncated</Badge>}
              </span>
            )}
          </div>

          {!ready && <EmptyState onLoadArchive={onLoadArchive} archive={archive} />}
          {ready && rtab === "table" && lastResult && <ResultsTable result={lastResult} />}
          {ready && rtab === "table" && !lastResult && (
            <div className={styles.placeholder}>Выберите preset ниже, чтобы получить результаты.</div>
          )}
          {ready && rtab === "chart" && (
            <div className={styles.placeholder}>Chart view — Sprint 2.</div>
          )}
          {ready && rtab === "timeline" && (
            <div className={styles.placeholder}>Timeline view — Sprint 2.</div>
          )}
          {ready && rtab === "raw" && lastResult && (
            <pre className={styles.raw_json}>{JSON.stringify(lastResult, null, 2)}</pre>
          )}
        </section>
      </div>

      <div className={styles.templates_bar}>
        <span className={styles.templates_label}>presets</span>
        {PRESETS.map((p) => (
          <button
            key={p.id}
            disabled={!ready || running != null}
            className={styles.template_btn}
            onClick={() => runPreset(p.id)}
          >
            {running === p.id ? "running…" : p.label}
          </button>
        ))}
        <span className={styles.saved_label}>
          SAVED · Sprint 2
        </span>
      </div>
    </div>
  );
}

function EmptyState({
  onLoadArchive,
  archive,
}: {
  onLoadArchive: () => void;
  archive: ReturnType<typeof useAppStore.getState>["archive"];
}) {
  if (archive && archive.status !== "ready" && archive.status !== "error") {
    return (
      <div className={styles.empty}>
        <Icon name="Refresh" size={22} color="var(--o-accent)" className="pulse" />
        <div className={styles.empty_title}>
          {archive.status === "extracting" ? "Extracting archive…" : "Parsing archive…"}
        </div>
        <div className={styles.empty_sub}>
          {archive.events_parsed.toLocaleString("en-US")} events · {Math.round(archive.progress * 100)}%
        </div>
        <div className={styles.progress}>
          <div className={styles.progress_fill} style={{ width: `${archive.progress * 100}%` }} />
        </div>
      </div>
    );
  }
  if (archive && archive.status === "error") {
    return (
      <div className={styles.empty}>
        <Icon name="AlertTriangle" size={22} color="var(--o-err)" />
        <div className={styles.empty_title}>Archive load failed</div>
        <div className={styles.empty_sub}>{archive.errors[0] || "Unknown error"}</div>
        <button className={styles.empty_btn} onClick={onLoadArchive}>
          <Icon name="Upload" size={13} /> Choose another archive
        </button>
      </div>
    );
  }
  return (
    <div className={styles.empty}>
      <Icon name="Database" size={26} color="var(--o-text-3)" />
      <div className={styles.empty_title}>Load a TZ archive to start querying</div>
      <div className={styles.empty_sub}>Drag-and-drop .zip into the window, or click below</div>
      <button className={styles.empty_btn} onClick={onLoadArchive}>
        <Icon name="Upload" size={13} /> Load TZ archive…
      </button>
    </div>
  );
}

function ResultsTable({ result }: { result: { columns: { name: string; type: string }[]; rows: unknown[][] } }) {
  return (
    <div className={styles.table_wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {result.columns.map((c) => (
              <Th key={c.name}>{c.name}</Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <Td key={ci} mono>{formatCell(cell)}</Td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "string") return v.length > 200 ? v.slice(0, 200) + "…" : v;
  return String(v);
}
