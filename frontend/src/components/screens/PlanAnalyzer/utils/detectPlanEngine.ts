/**
 * Sprint 8 Phase B — детектор движка СУБД по содержимому плана.
 *
 * Используется в PlanAnalyzer для автоматического выбора нужного view
 * (PlanVisualization для MSSQL XML, PgPlanTextView/Pev2PlanVisualization
 * для PostgreSQL, PlanTextView для MSSQL TEXT).
 *
 * Источник плана может быть:
 *  - File upload (.sqlplan / .json / .txt)
 *  - Paste из буфера обмена
 *  - ТЖ архив (поле plan_text из DBMSSQL/DBPOSTGRS event)
 *
 * Когда RPC дал явный engine (из event_type) — используем его. Когда нет
 * (file upload / paste) — детектим по сигнатурам в самом тексте.
 */

export type PlanEngine = "mssql" | "postgres" | "unknown";

export type PlanFormat = "xml" | "json" | "text";

export interface DetectionResult {
  engine: PlanEngine;
  format: PlanFormat;
}

/**
 * Определяет engine + format плана по его содержимому.
 *
 * Стратегия — сначала пробуем определить format (XML/JSON/TEXT — самое
 * однозначное), потом по format и keyword-сигнатурам — engine.
 *
 * Реальные случаи:
 *  - .sqlplan файл / paste из SSMS → XML начинается с <?xml или <ShowPlanXML
 *    → engine = "mssql", format = "xml"
 *  - 1С MSSQL planSQLText → text с indent "|--" + операторами SQL Server
 *    (Clustered Index Seek, Hash Match, ...) → engine = "mssql", format = "text"
 *  - 1С PG planSQLText → text с PG операторами (Seq Scan, Index Scan, ...)
 *    + "Planning Time:" / "Execution Time:" → engine = "postgres", format = "text"
 *  - pgAdmin / EXPLAIN (FORMAT JSON) → JSON array [{"Plan": ...}] или
 *    {"Plan": ...} → engine = "postgres", format = "json"
 *  - Не распознали → engine = "unknown", format = "text" (fallback на <pre>)
 */
export function detectPlanEngine(planContent: string): DetectionResult {
  const trimmed = planContent.trim();
  if (!trimmed) {
    return { engine: "unknown", format: "text" };
  }

  // === XML format → почти всегда MSSQL .sqlplan ===
  // PostgreSQL EXPLAIN (FORMAT XML) тоже существует, но 1С его не использует —
  // и SSMS-style .sqlplan однозначно XML с ShowPlanXML root. Любой XML с
  // ShowPlanXML / StmtSimple маркером — MSSQL.
  if (trimmed.startsWith("<?xml") || trimmed.startsWith("<ShowPlanXML")) {
    return { engine: "mssql", format: "xml" };
  }
  // Иногда XML начинается с <StmtSimple> когда выдернут один statement без
  // wrapper'а. Проверим первую строку на типичные SSMS-tags.
  if (
    /^<(?:ShowPlanXML|StmtSimple|StmtBlock|QueryPlan|RelOp)\b/i.test(trimmed)
  ) {
    return { engine: "mssql", format: "xml" };
  }

  // === JSON format → почти всегда PostgreSQL EXPLAIN (FORMAT JSON) ===
  // pgAdmin / DBeaver / pg-планы из re-EXPLAIN — массив с одним элементом
  // [{"Plan": {...}, "Planning Time": ..., "Execution Time": ...}], либо
  // одиночный объект {"Plan": {...}}.
  if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
    try {
      const parsed = JSON.parse(trimmed);
      const root = Array.isArray(parsed) ? parsed[0] : parsed;
      if (root && typeof root === "object" && "Plan" in root) {
        return { engine: "postgres", format: "json" };
      }
    } catch {
      // Не валидный JSON — продолжаем по другим сигнатурам как text.
    }
  }

  // === TEXT format — engine по keyword-сигнатурам ===

  // MSSQL SHOWPLAN_TEXT использует indent "|--" и характерные имена
  // операторов SQL Server. Эти имена в PG не встречаются (PG: "Seq Scan",
  // "Index Scan", "Hash Join"; MSSQL: "Clustered Index Seek", "Hash Match",
  // "Stream Aggregate", "Nested Loops").
  const mssqlSig =
    /\|--|Clustered Index Seek|Clustered Index Scan|NonClustered Index|Hash Match|Stream Aggregate|Compute Scalar|Nested Loops|Bitmap\(\)|Constant Scan|Merge Join \(/i;

  // PostgreSQL EXPLAIN ANALYZE TEXT использует "->" arrows + операторы PG +
  // обязательные строки "Planning Time:" / "Execution Time:" в конце
  // (для ANALYZE форматов). Без ANALYZE — нет Execution Time, только cost=.
  const pgOperatorSig =
    /\b(?:Seq Scan|Index Scan|Index Only Scan|Bitmap Heap Scan|Bitmap Index Scan|Hash Join|Merge Join|Nested Loop|Aggregate|HashAggregate|GroupAggregate|Sort|Limit|Append|Gather|Materialize|Memoize|Unique|WindowAgg|CTE Scan|Subquery Scan|Result|ProjectSet)\b/;
  const pgMetricsSig =
    /\b(?:Planning Time:|Execution Time:|Planning:|Execution:|cost=\d|actual time=)/;

  // Принимаем решение в порядке specificity:
  // PG metrics + PG operator → точно PG.
  if (pgOperatorSig.test(trimmed) && pgMetricsSig.test(trimmed)) {
    return { engine: "postgres", format: "text" };
  }
  // MSSQL signature → MSSQL text.
  if (mssqlSig.test(trimmed)) {
    return { engine: "mssql", format: "text" };
  }
  // Только PG operator без metrics — всё равно PG (короткий plan без ANALYZE).
  if (pgOperatorSig.test(trimmed)) {
    return { engine: "postgres", format: "text" };
  }
  // Только PG metrics без operator (странно, но возможно для пустых
  // result-only планов) — PG.
  if (pgMetricsSig.test(trimmed)) {
    return { engine: "postgres", format: "text" };
  }

  return { engine: "unknown", format: "text" };
}

/**
 * Helper: для случаев когда engine уже известен (например из RPC поля
 * tj-item.engine), но нужен только format. Чуть быстрее чем полный detect.
 */
export function detectPlanFormat(planContent: string): PlanFormat {
  const trimmed = planContent.trim();
  if (!trimmed) return "text";
  if (trimmed.startsWith("<?xml") || /^<(?:ShowPlanXML|StmtSimple|StmtBlock|QueryPlan|RelOp)\b/i.test(trimmed)) {
    return "xml";
  }
  if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
    try {
      const parsed = JSON.parse(trimmed);
      const root = Array.isArray(parsed) ? parsed[0] : parsed;
      if (root && typeof root === "object" && "Plan" in root) {
        return "json";
      }
    } catch {
      // not JSON
    }
  }
  return "text";
}
