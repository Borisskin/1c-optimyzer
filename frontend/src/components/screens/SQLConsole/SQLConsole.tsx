// SQL Console (Sprint 2 Phase B).
// Полноценный SQL редактор поверх per-archive DuckDB: validate + execute,
// результаты в таблицу + raw JSON. Charts / Timeline tabs появятся в Phase C-D.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { Editor, type EditorHandle } from "./Editor";
import { SavedQueriesMenu } from "./SavedQueriesMenu";
import { SchemaPanel } from "./SchemaPanel";
import { TemplatesBar } from "./TemplatesBar";
import { useTableState } from "@/components/tables/useTableState";
import { TableFilter } from "@/components/tables/TableFilter";
import styles from "./SQLConsole.module.css";

const SPLITTER_STORAGE_KEY = "optimyzer:sql:editor_pct";
const MIN_PANE_PCT = 18;
const MAX_PANE_PCT = 82;

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
  const editorRef = useRef<EditorHandle>(null);

  // Resizable splitter: ширина editor pane в процентах. Сохраняется в localStorage.
  const [editorPct, setEditorPct] = useState<number>(() => {
    if (typeof window === "undefined") return 50;
    const raw = window.localStorage.getItem(SPLITTER_STORAGE_KEY);
    const parsed = raw ? Number.parseFloat(raw) : NaN;
    return Number.isFinite(parsed) && parsed >= MIN_PANE_PCT && parsed <= MAX_PANE_PCT
      ? parsed
      : 50;
  });
  const [dragging, setDragging] = useState(false);
  const workareaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const el = workareaRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0) return;
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      const clamped = Math.min(MAX_PANE_PCT, Math.max(MIN_PANE_PCT, pct));
      setEditorPct(clamped);
    };
    const onUp = () => setDragging(false);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [dragging]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(SPLITTER_STORAGE_KEY, editorPct.toFixed(2));
  }, [editorPct]);

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

  // F5 — выполнить запрос (как в DBeaver / SSMS). preventDefault блокирует
  // браузерный reload даже если архив не загружен или запрос уже идёт —
  // иначе случайное нажатие сбрасывает редактор и результаты.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key !== "F5") return;
      e.preventDefault();
      if (running) return;
      runQuery();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [runQuery, running]);

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
              title={`${t.sql.actions.run} (Ctrl+Enter · F5)`}
            >
              <Icon name="Play" size={11} />
              {running ? t.sql.runningPlaceholder : t.sql.actions.run} <KBD>Ctrl+↵</KBD>
            </button>
          </>
        }
      />

      <div
        className={styles.workarea}
        ref={workareaRef}
        style={{ gridTemplateColumns: `${editorPct}% 6px 1fr` }}
      >
        <section className={styles.editor_pane}>
          <div className={styles.pane_head}>
            <span className={styles.tab_label}>
              <Icon name="FileText" size={11} color="var(--o-text-3)" /> {t.sql.editor.filenameDefault}
            </span>
          </div>
          <Editor
            ref={editorRef}
            value={query}
            onChange={setQuery}
            onRun={runQuery}
            schema={schema}
          />
        </section>

        <div
          className={`${styles.splitter} ${dragging ? styles.splitter_dragging : ""}`}
          onMouseDown={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDoubleClick={() => setEditorPct(50)}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize editor / results"
        />

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
        <TemplatesBar onLoadTemplate={setQuery} />
        <SchemaPanel
          schema={schema}
          onInsert={(text) => editorRef.current?.insertAtCursor(text)}
        />
        <SavedQueriesMenu currentQuery={query} onLoadQuery={setQuery} />
      </div>
    </div>
  );
}

function ResultsTable({ result }: { result: SQLExecuteResult }) {
  const columns = result.columns ?? [];
  const rows = result.rows ?? [];
  const table = useTableState({ rows, columns });
  return (
    <>
      {/* Sprint 5 hotfix: тулбар с TableFilter вынесен наружу .table_wrap.
          Раньше при скролле результатов фильтр уезжал вверх вместе со
          строками. Теперь thead sticky внутри .table_wrap, а тулбар
          flex-shrink:0 в родительском flex-контейнере results pane. */}
      <div className={styles.results_toolbar}>
        <TableFilter
          value={table.filter}
          onChange={table.setFilter}
          total={table.totalRows}
          visible={table.visibleRows}
        />
      </div>
      <div className={styles.table_wrap}>
        <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((c) => (
              <Th key={c.name} {...table.headerProps(c.name)}>
                {/* Sprint 5 hotfix: тип колонки виден явно — пользователю
                    понятно, нужно ли в WHERE писать IS NULL для пропусков
                    (VARCHAR/UUID nullable) или просто `= 0` (NOT NULL INTEGER). */}
                <span>{c.name}</span>
                {c.type && <span style={columnTypeStyle}>{c.type}</span>}
              </Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <Td key={ci} mono>
                  {renderCell(cell)}
                </Td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </>
  );
}

/** Sprint 5 hotfix: NULL отрендерен явным светло-серым курсивным chip'ом,
 *  пустая строка — действительно пустая ячейка. Раньше оба показывались
 *  как "—" и нельзя было понять `WHERE col IS NULL` vs `WHERE col = ''`. */
function renderCell(v: unknown): React.ReactNode {
  if (v === null || v === undefined) {
    return <span style={nullChipStyle} title="SQL NULL">NULL</span>;
  }
  if (typeof v === "string") {
    return v.length > 200 ? v.slice(0, 200) + "…" : v;
  }
  return String(v);
}

const nullChipStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "0 6px",
  borderRadius: 3,
  background: "var(--o-subtle)",
  color: "var(--o-text-mute, var(--o-text-3))",
  fontFamily: "var(--o-font-mono)",
  fontSize: 10.5,
  fontStyle: "italic",
  letterSpacing: "0.04em",
};

const columnTypeStyle: React.CSSProperties = {
  marginLeft: 6,
  padding: "0 4px",
  background: "var(--o-subtle)",
  color: "var(--o-text-3)",
  fontFamily: "var(--o-font-mono)",
  fontSize: 9.5,
  fontWeight: 400,
  textTransform: "uppercase",
  letterSpacing: "0.03em",
  borderRadius: 2,
};

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
    // Percent — из сырого bytes_done, без useAnimatedCounter. Это синхронизирует
    // отображение с ProgressCard, который тоже использует raw bytes_done.
    // liveBytes остаётся анимированным для красоты счётчика выше.
    const rawBytesDone = ingest?.bytes_done ?? 0;
    const percent =
      bytesTotal > 0
        ? Math.min(100, (rawBytesDone / bytesTotal) * 100)
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
