/**
 * Sprint 8 Phase B — отображение PostgreSQL EXPLAIN TEXT плана.
 *
 * PG planSQLText из ТЖ архива (DBPOSTGRS events) или paste из pgAdmin/DBeaver.
 * Аналог PlanTextView (MSSQL), но с подсветкой PG-specific operators и метрик.
 *
 * Что подсвечивается:
 *  - Операторы (Seq Scan, Index Scan, Hash Join, Memoize, ...) — bold
 *  - Cost (cost=X..Y rows=N width=N) — muted dim
 *  - Actual stats (actual time=... rows=N loops=N) — accent green/red
 *    в зависимости от estimated vs actual rows divergence
 *  - Filter / Index Cond / Hash Cond — italic accent
 *  - Rows Removed by Filter — warning orange если N большое
 *  - Buffers: shared hit/read — small caption
 *  - Footer (Planning Time, Execution Time) — separator + small caption
 *
 * Опционально показывает кнопку «Получить интерактивный план» если PG
 * connection в Settings подключён (Phase B.4 + B.5 — pev2 visualization).
 */

import { useState } from "react";
import styles from "./PgPlanTextView.module.css";

interface Props {
  planText: string;
  /** Опционально: контекст события из ТЖ для header'а. */
  meta?: {
    ts?: string | null;
    duration_us?: number | null;
    context?: string | null;
  };
  /** Sprint 8 Phase B.4/B.5 — callback для opt-in re-EXPLAIN → JSON → pev2. */
  onRequestInteractive?: () => void;
  /** Sprint 8 Phase B.4 — PG connection в Settings подключён? */
  isInteractiveAvailable?: boolean;
}

export function PgPlanTextView({
  planText,
  meta,
  onRequestInteractive,
  isInteractiveAvailable = false,
}: Props) {
  const [collapsed, setCollapsed] = useState(false);

  if (!planText.trim()) {
    return <div className={styles.empty}>План пуст — нечего показать.</div>;
  }

  // Highlight стратегия: проще всего — line-by-line парсинг с классификацией.
  // Каждая строка получает свой className по типу содержимого.
  const lines = planText.split("\n");
  const annotatedLines = lines.map((line, idx) => annotateLine(line, idx));

  return (
    <div className={styles.container}>
      <div
        className={styles.header}
        onClick={() => setCollapsed((v) => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setCollapsed((v) => !v); } }}
        aria-expanded={!collapsed}
      >
        <div className={styles.title}>
          <span className={styles.engineBadge}>PostgreSQL</span>
          План запроса (EXPLAIN ANALYZE)
        </div>
        {meta && (
          <div className={styles.meta}>
            {meta.ts && <span className={styles.metaItem}>{formatTs(meta.ts)}</span>}
            {meta.duration_us != null && (
              <span className={styles.metaItem}>
                {formatDuration(meta.duration_us)}
              </span>
            )}
            {meta.context && (
              <span className={styles.metaContext} title={meta.context}>
                {meta.context}
              </span>
            )}
          </div>
        )}
      </div>

      {!collapsed && (
        <>
          {/* Sprint 8 Phase B.4/B.5: opt-in re-EXPLAIN → pev2 visualization */}
          {onRequestInteractive && (
            <div className={styles.interactiveBar}>
              {isInteractiveAvailable ? (
                <button
                  type="button"
                  className={styles.interactiveButton}
                  onClick={onRequestInteractive}
                  title="Backend выполнит EXPLAIN (FORMAT JSON, ANALYZE) повторно через настроенное PG подключение и покажет интерактивный план."
                >
                  Получить интерактивный план
                </button>
              ) : (
                <div className={styles.interactiveHint}>
                  Подключите PostgreSQL базу в Настройках, чтобы получить
                  интерактивную визуализацию плана через pev2.
                </div>
              )}
            </div>
          )}

          <div className={styles.hint}>
            Это план в формате PostgreSQL EXPLAIN ANALYZE. 1С запускает PG со
            специальными настройками: <code>enable_mergejoin=off</code> (Merge
            Join отключён), <code>cpu_operator_cost=0.001</code> (cost в 5×
            меньше PG default). Учитывайте это при оценке cost numbers.
          </div>

          <pre className={styles.body}>
            {annotatedLines.map((parts, lineIdx) => (
              <div key={lineIdx} className={styles.line}>
                {parts}
              </div>
            ))}
          </pre>
        </>
      )}
    </div>
  );
}

// ============================================================
// Line annotation — классификация частей одной строки плана
// ============================================================

const OPERATOR_RE =
  /^(\s*(?:->\s*)?)(Seq Scan|Index Scan|Index Only Scan|Bitmap Heap Scan|Bitmap Index Scan|Hash Join|Hash|Nested Loop|Merge Join|Aggregate|HashAggregate|GroupAggregate|Sort|Limit|Append|Gather(?: Merge)?|Materialize|Memoize|Unique|WindowAgg|CTE Scan|Subquery Scan|Result|ProjectSet|Function Scan|Values Scan|Table Function Scan|Foreign Scan|LockRows|SetOp|RecursiveUnion|Modify Table|Insert|Update|Delete)\b/;

const COST_RE = /(\(cost=[\d.]+\.\.[\d.]+\s+rows=[\d.]+\s+width=\d+\))/;
const ACTUAL_RE = /(\(actual time=[\d.]+\.\.[\d.]+\s+rows=[\d.]+\s+loops=\d+\))/;
const ACTUAL_NEVER_RE = /(\(never executed\))/;
const COND_RE = /^(\s+)(Filter|Index Cond|Recheck Cond|Hash Cond|Join Filter|Sort Key|Group Key|One-Time Filter|Output|Index|Cache Key|Merge Cond):/;
const REMOVED_RE = /^(\s+)Rows Removed by Filter:\s+(\d+)/;
const BUFFERS_RE = /^(\s+)Buffers:/;
const TIMING_RE = /^(Planning Time|Execution Time|Planning|Execution):\s+([\d.]+)\s*(ms|s)?/;
const QUERY_IDENT_RE = /^(Query Identifier:)/;
const HEAP_FETCHES_RE = /^(\s+)Heap Fetches:\s+(\d+)/;
const WORKERS_RE = /^(\s+)(Workers? (?:Planned|Launched)):\s+(\d+)/;

function annotateLine(line: string, lineIdx: number): React.ReactNode[] {
  // Пустая строка — возвращаем NBSP чтобы pre сохранил высоту строки.
  if (!line) return [<span key="empty">{" "}</span>];

  // === Операторы (главная строка node) ===
  const opMatch = line.match(OPERATOR_RE);
  if (opMatch) {
    const indent = opMatch[1];
    const op = opMatch[2];
    const rest = line.slice(opMatch[0].length);
    return [
      <span key="indent">{indent}</span>,
      <span key="op" className={styles.operator}>
        {op}
      </span>,
      ...annotateRestOfOperatorLine(rest, lineIdx),
    ];
  }

  // === Predicate-строки (Filter/Index Cond/Hash Cond) ===
  const condMatch = line.match(COND_RE);
  if (condMatch) {
    const indent = condMatch[1];
    const condName = condMatch[2];
    const rest = line.slice(condMatch[0].length);
    return [
      <span key="indent">{indent}</span>,
      <span key="cond" className={styles.condName}>
        {condName}:
      </span>,
      <span key="rest" className={styles.condValue}>
        {rest}
      </span>,
    ];
  }

  // === Rows Removed by Filter — warning если большое значение ===
  const rmMatch = line.match(REMOVED_RE);
  if (rmMatch) {
    const indent = rmMatch[1];
    const count = parseInt(rmMatch[2], 10);
    const isLarge = count >= 1000;
    return [
      <span key="indent">{indent}</span>,
      <span
        key="label"
        className={isLarge ? styles.removedLarge : styles.removed}
      >
        Rows Removed by Filter: {count.toLocaleString("ru-RU")}
        {isLarge && (
          <span className={styles.warningIcon} title="Большое количество отбракованных строк — predicate может быть не-SARGable">
            {" ⚠"}
          </span>
        )}
      </span>,
    ];
  }

  // === Heap Fetches — warning если > 0 (vacuum нужен для Index Only Scan) ===
  const hfMatch = line.match(HEAP_FETCHES_RE);
  if (hfMatch) {
    const indent = hfMatch[1];
    const count = parseInt(hfMatch[2], 10);
    const isWarn = count > 0;
    return [
      <span key="indent">{indent}</span>,
      <span key="hf" className={isWarn ? styles.removedLarge : styles.buffers}>
        Heap Fetches: {count}
        {isWarn && (
          <span className={styles.warningIcon} title="Heap fetches > 0 — нужен VACUUM для эффективного Index Only Scan">
            {" ⚠"}
          </span>
        )}
      </span>,
    ];
  }

  // === Workers (parallel query) ===
  const wMatch = line.match(WORKERS_RE);
  if (wMatch) {
    return [
      <span key="indent">{wMatch[1]}</span>,
      <span key="w" className={styles.workers}>
        {wMatch[2]}: {wMatch[3]}
      </span>,
    ];
  }

  // === Buffers ===
  if (BUFFERS_RE.test(line)) {
    return [<span key="buf" className={styles.buffers}>{line}</span>];
  }

  // === Timing footer ===
  const tMatch = line.match(TIMING_RE);
  if (tMatch) {
    return [
      <span key="t" className={styles.timing}>
        {line}
      </span>,
    ];
  }

  // === Query Identifier ===
  if (QUERY_IDENT_RE.test(line)) {
    return [<span key="qi" className={styles.queryIdent}>{line}</span>];
  }

  // Default: plain line.
  return [<span key="d">{line}</span>];
}

function annotateRestOfOperatorLine(rest: string, lineIdx: number): React.ReactNode[] {
  // Внутри rest могут быть cost/actual в скобках. Подсветим.
  const parts: React.ReactNode[] = [];
  let remaining = rest;
  let partIdx = 0;

  while (remaining.length > 0) {
    // Сначала ищем actual — оно более specific.
    const aMatch = remaining.match(ACTUAL_RE);
    const cMatch = remaining.match(COST_RE);
    const aneverMatch = remaining.match(ACTUAL_NEVER_RE);

    // Берём то совпадение что встретилось раньше.
    let nextMatch: RegExpMatchArray | null = null;
    let className = "";
    if (aMatch && (cMatch == null || aMatch.index! <= cMatch.index!)) {
      nextMatch = aMatch;
      className = styles.actual;
    } else if (cMatch) {
      nextMatch = cMatch;
      className = styles.cost;
    } else if (aneverMatch) {
      nextMatch = aneverMatch;
      className = styles.actualNever;
    }

    if (nextMatch && nextMatch.index !== undefined) {
      if (nextMatch.index > 0) {
        parts.push(
          <span key={`p-${lineIdx}-${partIdx++}`}>
            {remaining.slice(0, nextMatch.index)}
          </span>,
        );
      }
      parts.push(
        <span key={`m-${lineIdx}-${partIdx++}`} className={className}>
          {nextMatch[0]}
        </span>,
      );
      remaining = remaining.slice(nextMatch.index + nextMatch[0].length);
    } else {
      parts.push(<span key={`t-${lineIdx}-${partIdx++}`}>{remaining}</span>);
      break;
    }
  }
  return parts;
}

// ============================================================
// Format helpers
// ============================================================

function formatTs(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function formatDuration(us: number): string {
  const ms = us / 1000;
  if (ms < 1) return `${us} мкс`;
  if (ms < 1000) return `${ms.toFixed(0)} мс`;
  return `${(ms / 1000).toFixed(2)} с`;
}
