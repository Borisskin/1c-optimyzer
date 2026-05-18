import { useCallback, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { Badge, KBD, PageHeader, Tabs, Th, Td } from "@/components/primitives/Primitives";
import { backend, type OQLExecuteResult, type QueryResult } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t, format } from "@/i18n/ru";
import { useAnimatedCounter } from "@/hooks/useAnimatedCounter";
import { Editor } from "./Editor";
import { TemplatesBar } from "./TemplatesBar";
import { SavedQueriesMenu } from "./SavedQueriesMenu";
import styles from "./OQLConsole.module.css";

type ResultTab = "table" | "chart" | "timeline" | "raw";

const DEFAULT_QUERY = `// OptimyzerQL — декларативный язык запросов поверх ТЖ.
// Sprint 1 — встроенный редактор + компилятор в SQL.
// Выберите шаблон ниже или напишите свой запрос.

events
| order by ts asc
| take 100
`;

interface ExecutedResult {
  ok: boolean;
  columns: { name: string; type: string }[];
  rows: unknown[][];
  total_count: number;
  truncated: boolean;
  executed_in_ms: number;
  error?: string;
  phase?: string;
  render?: string | null;
  sql_compiled?: string;
}

function adaptResult(r: OQLExecuteResult): ExecutedResult {
  return {
    ok: r.ok,
    columns: r.columns ?? [],
    rows: r.rows ?? [],
    total_count: r.row_count ?? (r.rows?.length ?? 0),
    truncated: false,
    executed_in_ms: r.executed_ms ?? 0,
    error: r.error,
    phase: r.phase,
    render: r.render,
    sql_compiled: r.sql_compiled,
  };
}

export function OQLConsoleScreen({ onLoadArchive }: { onLoadArchive: () => void }) {
  const [rtab, setRtab] = useState<ResultTab>("table");
  const [query, setQuery] = useState<string>(DEFAULT_QUERY);
  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState<ExecutedResult | null>(null);
  const archive = useAppStore((s) => s.archive);
  const pushToast = useAppStore((s) => s.pushToast);

  const ready = archive?.status === "ready";

  const runQuery = useCallback(async () => {
    if (!archive || !ready) return;
    setRunning(true);
    try {
      const raw = await backend.executeOqlQuery(archive.archive_id, query);
      const result = adaptResult(raw);
      setLastResult(result);
      if (result.ok) {
        pushToast(
          `${result.total_count} ${t.oql.results.rowsCounter} · ${result.executed_in_ms.toFixed(0)} мс`,
          "ok",
        );
      } else {
        pushToast(
          format(t.errors.oqlExecuteError, { detail: result.error ?? "—" }),
          "err",
        );
      }
    } catch (e) {
      pushToast(format(t.errors.queryFailed, { detail: String(e) }), "err");
    } finally {
      setRunning(false);
    }
  }, [archive, ready, query, pushToast]);

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
            <button className={styles.btn} disabled title={t.oql.actions.docs}>
              <Icon name="FileText" size={11} />
              {t.oql.actions.docs}
            </button>
            <button className={styles.btn} disabled title={t.oql.actions.share}>
              <Icon name="Share" size={11} />
              {t.oql.actions.share}
            </button>
            <button
              className={styles.btn_primary}
              onClick={runQuery}
              disabled={!ready || running}
              title={t.oql.actions.run}
            >
              <Icon name="Play" size={11} />
              {running ? t.oql.runningPlaceholder : t.oql.actions.run} <KBD>Ctrl+↵</KBD>
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
          </div>
          <Editor value={query} onChange={setQuery} onRun={runQuery} />
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
            {lastResult && lastResult.ok && (
              <span className={styles.exec_info}>
                <span>{lastResult.total_count} {t.oql.results.rowsCounter}</span>
                <span>
                  {t.oql.results.executedIn} {lastResult.executed_in_ms.toFixed(0)} мс
                </span>
              </span>
            )}
          </div>

          {!ready && <EmptyState onLoadArchive={onLoadArchive} archive={archive} />}
          {ready && lastResult && !lastResult.ok && (
            <div className={styles.placeholder}>{lastResult.error}</div>
          )}
          {ready && rtab === "table" && lastResult?.ok && <ResultsTable result={asQueryResult(lastResult)} />}
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
        <TemplatesBar onLoadTemplate={setQuery} />
        <SavedQueriesMenu currentQuery={query} onLoadQuery={setQuery} />
      </div>
    </div>
  );
}

function asQueryResult(r: ExecutedResult): QueryResult {
  return {
    columns: r.columns,
    rows: r.rows,
    total_count: r.total_count,
    truncated: r.truncated,
    executed_in_ms: r.executed_in_ms,
  };
}

function EmptyState({
  onLoadArchive,
  archive,
}: {
  onLoadArchive: () => void;
  archive: ReturnType<typeof useAppStore.getState>["archive"];
}) {
  const ingest = useAppStore((s) => s.ingest);
  const isParsing =
    archive && archive.status !== "ready" && archive.status !== "error";
  const ingestActive = Boolean(ingest && ingest.phase !== "done" && ingest.phase !== "error");

  // Хук всегда вызывается; за пределами parsing-режима active=false и просто отдаёт target.
  const liveEvents = useAnimatedCounter(
    ingest?.events_inserted ?? archive?.events_parsed ?? 0,
    Boolean(isParsing) && ingestActive,
  );
  const liveBytes = useAnimatedCounter(
    ingest?.bytes_done ?? 0,
    Boolean(isParsing) && ingestActive,
  );

  if (isParsing) {
    const verbMap: Record<string, string> = {
      extracting: t.oql.archiveLoading.extracting,
      discovering: t.oql.archiveLoading.discovering,
      parsing: t.oql.archiveLoading.parsing,
      indexing: t.oql.archiveLoading.indexing,
    };
    const verb = verbMap[archive.status] ?? t.oql.archiveLoading.parsing;
    const bytesTotal = ingest?.bytes_total ?? archive.size_bytes ?? 0;
    const percent =
      bytesTotal > 0
        ? Math.min(100, (liveBytes / bytesTotal) * 100)
        : archive.progress * 100;
    return (
      <div className={styles.empty}>
        <Icon name="Refresh" size={22} color="var(--o-accent)" className="pulse" />
        <div className={styles.empty_title}>{verb}</div>
        <div className={styles.empty_events}>
          {Math.floor(liveEvents).toLocaleString("ru-RU")}
        </div>
        <div className={styles.empty_sub}>
          {t.statusbar.events} · {percent.toFixed(1)}%
        </div>
        <div className={styles.progress}>
          <div className={styles.progress_fill} style={{ width: `${percent}%` }} />
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
