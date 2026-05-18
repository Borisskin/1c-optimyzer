// SQL Console (Sprint 2 Phase B).
// Полноценный SQL редактор поверх per-archive DuckDB: validate + execute,
// результаты в таблицу + raw JSON. Charts / Timeline tabs появятся в Phase C-D.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { Badge, KBD, PageHeader, Tabs, Th, Td } from "@/components/primitives/Primitives";
import {
  backend,
  type SQLExecuteResult,
  type TableSchema,
} from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t, format } from "@/i18n/ru";
import { useAnimatedCounter } from "@/hooks/useAnimatedCounter";
import { Editor } from "./Editor";
import { SavedQueriesMenu } from "./SavedQueriesMenu";
import styles from "./SQLConsole.module.css";

type ResultTab = "table" | "raw";

const DEFAULT_QUERY = `-- SQL поверх событий технологического журнала.
-- Ctrl+Enter — выполнить.

SELECT
    ts,
    event_type,
    process_role,
    duration_us / 1000.0 AS duration_ms,
    context
FROM events
ORDER BY duration_us DESC NULLS LAST
LIMIT 100;
`;

export function SQLConsoleScreen({ onLoadArchive }: { onLoadArchive: () => void }) {
  const [rtab, setRtab] = useState<ResultTab>("table");
  const [query, setQuery] = useState<string>(DEFAULT_QUERY);
  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState<SQLExecuteResult | null>(null);
  const [schema, setSchema] = useState<TableSchema>({});
  const archive = useAppStore((s) => s.archive);
  const pushToast = useAppStore((s) => s.pushToast);

  const ready = archive?.status === "ready";
  const archiveId = ready ? archive.archive_id : null;

  // При смене активного архива подгружаем schema для autocomplete.
  useEffect(() => {
    if (!archiveId) {
      setSchema({});
      return;
    }
    let cancelled = false;
    backend
      .getSchema(archiveId)
      .then((s) => {
        if (!cancelled) setSchema(s);
      })
      .catch(() => {
        if (!cancelled) setSchema({});
      });
    return () => {
      cancelled = true;
    };
  }, [archiveId]);

  const runQuery = useCallback(async () => {
    if (!archiveId) return;
    setRunning(true);
    try {
      const result = await backend.executeSql(archiveId, query);
      setLastResult(result);
      if (result.ok) {
        pushToast(
          `${result.row_count ?? 0} ${t.sql.results.rowsCounter} · ${(
            result.executed_ms ?? 0
          ).toFixed(0)} мс`,
          "ok",
        );
      } else {
        pushToast(
          format(t.errors.sqlExecuteError, { detail: result.error ?? "—" }),
          "err",
        );
      }
    } catch (e) {
      pushToast(format(t.errors.queryFailed, { detail: String(e) }), "err");
    } finally {
      setRunning(false);
    }
  }, [archiveId, query, pushToast]);

  const tabsModel = useMemo(
    () => [
      {
        id: "table" as const,
        label: t.sql.results.tabs.table,
        icon: "FlaskList" as const,
        count: lastResult?.row_count,
      },
      { id: "raw" as const, label: t.sql.results.tabs.raw, icon: "Code" as const },
    ],
    [lastResult?.row_count],
  );

  return (
    <div className={styles.screen}>
      <PageHeader
        breadcrumbs={[t.sql.breadcrumb, t.sql.pageTitle]}
        title={
          <span className={styles.title_inline}>
            {t.sql.pageTitle} <Badge tone="teal">{t.sql.badgeFreeTier}</Badge>
            <Badge tone="mute">{t.sql.sprintLabel}</Badge>
          </span>
        }
        sub={t.sql.description}
        right={
          <>
            <button className={styles.btn} disabled title={t.sql.actions.docs}>
              <Icon name="FileText" size={11} />
              {t.sql.actions.docs}
            </button>
            <button
              className={styles.btn_primary}
              onClick={runQuery}
              disabled={!ready || running}
              title={t.sql.actions.run}
            >
              <Icon name="Play" size={11} />
              {running ? t.sql.runningPlaceholder : t.sql.actions.run} <KBD>Ctrl+↵</KBD>
            </button>
          </>
        }
      />

      <div className={styles.workarea}>
        <section className={styles.editor_pane}>
          <div className={styles.pane_head}>
            <span className={styles.tab_label}>
              <Icon name="FileText" size={11} color="var(--o-text-3)" /> {t.sql.editor.filenameDefault}
            </span>
          </div>
          <Editor value={query} onChange={setQuery} onRun={runQuery} schema={schema} />
        </section>

        <section className={styles.results_pane}>
          <div className={styles.pane_head}>
            <Tabs
              value={rtab}
              onChange={(v) => setRtab(v as ResultTab)}
              dense
              tabs={tabsModel}
            />
            {lastResult && lastResult.ok && (
              <span className={styles.exec_info}>
                <span>{lastResult.row_count ?? 0} {t.sql.results.rowsCounter}</span>
                <span>
                  {t.sql.results.executedIn} {(lastResult.executed_ms ?? 0).toFixed(0)} мс
                </span>
                {lastResult.truncated && <span>{t.sql.results.truncated}</span>}
              </span>
            )}
          </div>

          {!ready && <EmptyState onLoadArchive={onLoadArchive} archive={archive} />}
          {ready && lastResult && !lastResult.ok && (
            <div className={styles.placeholder}>{lastResult.error}</div>
          )}
          {ready && rtab === "table" && lastResult?.ok && <ResultsTable result={lastResult} />}
          {ready && rtab === "table" && !lastResult && (
            <div className={styles.placeholder}>{t.sql.results.placeholderTable}</div>
          )}
          {ready && rtab === "raw" && lastResult && (
            <pre className={styles.raw_json}>{JSON.stringify(lastResult, null, 2)}</pre>
          )}
        </section>
      </div>

      <div className={styles.templates_bar}>
        <span className={styles.templates_label}>{t.sql.presets.label}</span>
        <span className={styles.placeholder} style={{ padding: 0 }}>
          {t.sql.results.placeholderChart === t.sql.results.placeholderChart ? "Phase F" : ""}
        </span>
        <SavedQueriesMenu currentQuery={query} onLoadQuery={setQuery} />
      </div>
    </div>
  );
}

function ResultsTable({ result }: { result: SQLExecuteResult }) {
  const columns = result.columns ?? [];
  const rows = result.rows ?? [];
  return (
    <div className={styles.table_wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((c) => (
              <Th key={c.name}>{c.name}</Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
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
  if (v == null) return t.sql.results.empty_cell;
  if (typeof v === "string") return v.length > 200 ? v.slice(0, 200) + "…" : v;
  return String(v);
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
      extracting: t.sql.archiveLoading.extracting,
      discovering: t.sql.archiveLoading.discovering,
      parsing: t.sql.archiveLoading.parsing,
      indexing: t.sql.archiveLoading.indexing,
    };
    const verb = verbMap[archive.status] ?? t.sql.archiveLoading.parsing;
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
        <div className={styles.empty_title}>{t.sql.archiveError.title}</div>
        <div className={styles.empty_sub}>{archive.errors[0] || t.sql.archiveError.unknown}</div>
        <button className={styles.empty_btn} onClick={onLoadArchive}>
          <Icon name="Upload" size={13} /> {t.sql.archiveError.chooseAnother}
        </button>
      </div>
    );
  }
  return (
    <div className={styles.empty}>
      <Icon name="Database" size={26} color="var(--o-text-3)" />
      <div className={styles.empty_title}>{t.sql.results.empty.noArchive}</div>
      <div className={styles.empty_sub}>{t.sql.results.empty.hint}</div>
      <button className={styles.empty_btn} onClick={onLoadArchive}>
        <Icon name="Upload" size={13} /> {t.sql.results.empty.loadButton}
      </button>
    </div>
  );
}
