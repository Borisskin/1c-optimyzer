import { useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { Badge, KBD, PageHeader, Tabs, Th, Td } from "@/components/primitives/Primitives";
import { backend } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t, format } from "@/i18n/ru";
import styles from "./OQLConsole.module.css";

type ResultTab = "table" | "chart" | "timeline" | "raw";

type PresetId = "first_100" | "longest" | "deadlocks";

interface PresetSpec {
  id: PresetId;
  label: string;
}

const PRESETS: PresetSpec[] = [
  { id: "first_100", label: "Первые 100 событий" },
  { id: "longest",   label: "Самые долгие 100" },
  { id: "deadlocks", label: "Дедлоки" },
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
      pushToast(`${id}: ${r.total_count} ${t.oql.results.rowsCounter} · ${r.executed_in_ms.toFixed(0)} мс`, "ok");
    } catch (e) {
      pushToast(format(t.errors.queryFailed, { detail: String(e) }), "err");
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className={styles.screen}>
      <PageHeader
        breadcrumbs={[t.oql.breadcrumb, t.oql.pageTitle]}
        title={
          <span className={styles.title_inline}>
            {t.oql.pageTitle} <Badge tone="teal">{t.oql.badgeFreeTier}</Badge>
            <Badge tone="mute">{t.oql.sprintLabel}</Badge>
          </span>
        }
        sub={t.oql.description}
        right={
          <>
            <button className={styles.btn} disabled title={t.oql.actions.templates}>
              <Icon name="Book" size={11} />
              {t.oql.actions.templates}
            </button>
            <button className={styles.btn} disabled title={t.oql.actions.docs}>
              <Icon name="FileText" size={11} />
              {t.oql.actions.docs}
            </button>
            <button className={styles.btn} disabled title={t.oql.actions.share}>
              <Icon name="Share" size={11} />
              {t.oql.actions.share}
            </button>
            <button className={styles.btn_primary} disabled title={t.oql.actions.run}>
              <Icon name="Play" size={11} />
              {t.oql.actions.run} <KBD>⌘↵</KBD>
            </button>
          </>
        }
      />

      <div className={styles.workarea}>
        <section className={styles.editor_pane}>
          <div className={styles.pane_head}>
            <span className={styles.tab_label}>
              <Icon name="FileText" size={11} color="var(--o-text-3)" /> {t.oql.editor.filenameDefault}
            </span>
            <Badge tone="mute">{t.oql.editor.readonly}</Badge>
            <span className={styles.cursor_info}>
              {t.oql.editor.cursor} 1 · {t.oql.editor.column} 1 · 0 {t.oql.editor.rows}
            </span>
          </div>
          <textarea
            className={styles.editor}
            readOnly
            value={t.oql.editor.placeholderSprint0}
          />
        </section>

        <section className={styles.results_pane}>
          <div className={styles.pane_head}>
            <Tabs
              value={rtab}
              onChange={(v) => setRtab(v as ResultTab)}
              dense
              tabs={[
                { id: "table",    label: t.oql.results.tabs.table,    icon: "FlaskList", count: lastResult?.total_count },
                { id: "chart",    label: t.oql.results.tabs.chart,    icon: "Trend" },
                { id: "timeline", label: t.oql.results.tabs.timeline, icon: "Activity" },
                { id: "raw",      label: t.oql.results.tabs.raw,      icon: "Code" },
              ]}
            />
            {lastResult && (
              <span className={styles.exec_info}>
                <span>{lastResult.total_count} {t.oql.results.rowsCounter}</span>
                <span>
                  {t.oql.results.executedIn} {lastResult.executed_in_ms.toFixed(0)} мс
                </span>
                {lastResult.truncated && <Badge tone="warn">{t.oql.results.truncated}</Badge>}
              </span>
            )}
          </div>

          {!ready && <EmptyState onLoadArchive={onLoadArchive} archive={archive} />}
          {ready && rtab === "table" && lastResult && <ResultsTable result={lastResult} />}
          {ready && rtab === "table" && !lastResult && (
            <div className={styles.placeholder}>{t.oql.results.placeholderTable}</div>
          )}
          {ready && rtab === "chart" && (
            <div className={styles.placeholder}>{t.oql.results.placeholderChart}</div>
          )}
          {ready && rtab === "timeline" && (
            <div className={styles.placeholder}>{t.oql.results.placeholderTimeline}</div>
          )}
          {ready && rtab === "raw" && lastResult && (
            <pre className={styles.raw_json}>{JSON.stringify(lastResult, null, 2)}</pre>
          )}
        </section>
      </div>

      <div className={styles.templates_bar}>
        <span className={styles.templates_label}>{t.oql.presets.label}</span>
        {PRESETS.map((p) => (
          <button
            key={p.id}
            disabled={!ready || running != null}
            className={styles.template_btn}
            onClick={() => runPreset(p.id)}
          >
            {running === p.id ? t.oql.runningPlaceholder : p.label}
          </button>
        ))}
        <span className={styles.saved_label}>{t.oql.saved.label}</span>
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
    const verbMap: Record<string, string> = {
      extracting: t.oql.archiveLoading.extracting,
      discovering: t.oql.archiveLoading.discovering,
      parsing: t.oql.archiveLoading.parsing,
      indexing: t.oql.archiveLoading.indexing,
    };
    const verb = verbMap[archive.status] ?? t.oql.archiveLoading.parsing;
    return (
      <div className={styles.empty}>
        <Icon name="Refresh" size={22} color="var(--o-accent)" className="pulse" />
        <div className={styles.empty_title}>{verb}</div>
        <div className={styles.empty_sub}>
          {archive.events_parsed.toLocaleString("ru-RU")} {t.statusbar.events} ·{" "}
          {Math.round(archive.progress * 100)}%
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
        <div className={styles.empty_title}>{t.oql.archiveError.title}</div>
        <div className={styles.empty_sub}>{archive.errors[0] || t.oql.archiveError.unknown}</div>
        <button className={styles.empty_btn} onClick={onLoadArchive}>
          <Icon name="Upload" size={13} /> {t.oql.archiveError.chooseAnother}
        </button>
      </div>
    );
  }
  return (
    <div className={styles.empty}>
      <Icon name="Database" size={26} color="var(--o-text-3)" />
      <div className={styles.empty_title}>{t.oql.results.empty.noArchive}</div>
      <div className={styles.empty_sub}>{t.oql.results.empty.hint}</div>
      <button className={styles.empty_btn} onClick={onLoadArchive}>
        <Icon name="Upload" size={13} /> {t.oql.results.empty.loadButton}
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
                <Td key={ci} mono>
                  {formatCell(cell)}
                </Td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v == null) return t.oql.results.empty_cell;
  if (typeof v === "string") return v.length > 200 ? v.slice(0, 200) + "…" : v;
  return String(v);
}
