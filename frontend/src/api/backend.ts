// JSON-RPC wrapper over Tauri invoke -> Rust shell -> Python sidecar.

import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

export type ArchivePhase =
  | "discovering"
  | "extracting"
  | "parsing"
  | "indexing"
  | "ready"
  | "error";

export type SourceType = "folder" | "archive";

export interface ArchiveState {
  archive_id: string;
  path: string;
  source_type: SourceType;
  size_bytes: number;
  file_count: number;
  status: ArchivePhase;
  progress: number;
  events_parsed: number;
  errors: string[];
  parsing_time_sec: number | null;
  loaded_at: string | null;
}

export interface AppInfo {
  backend_version: string;
  python_version: string;
  duckdb_version: string;
  platform: string;
}

export interface QueryColumn {
  name: string;
  type: string;
}

export interface QueryResult {
  columns: QueryColumn[];
  rows: unknown[][];
  total_count: number;
  truncated: boolean;
  executed_in_ms: number;
}

export interface StorageStats {
  events_count: number;
  db_size_bytes: number;
  parsing_speed_eps: number;
  archive_metadata: {
    path: string;
    size_bytes: number;
    file_count: number | null;
    loaded_at: string | null;
  };
}

export interface RecentArchive {
  archive_id: string;
  path: string;
  size_bytes: number;
  events_count: number;
  loaded_at: string;
  parsing_time_sec: number | null;
}

export interface StoredArchive extends RecentArchive {
  db_size_bytes: number;
  is_loaded: boolean;
  is_orphan: boolean;
}

export interface StoredArchivesResponse {
  archives: StoredArchive[];
  total_db_size_bytes: number;
}

export interface DeleteArchiveResult {
  ok: boolean;
  sqlite_removed: boolean;
  was_loaded: boolean;
}

export interface DeleteAllArchivesResult {
  ok: boolean;
  closed: number;
  files_deleted: number;
  sqlite_removed: number;
}

export type ProgressPhase =
  | "discovering"
  | "parsing"
  | "indexing"
  | "done"
  | "error"
  | "cancelled";

export interface ProgressEvent {
  archive_id: string;
  phase: ProgressPhase;
  files_done: number;
  files_total: number;
  bytes_done: number;
  bytes_total: number;
  events_inserted: number;
  current_file: string | null;
  error_message: string | null;
}

async function rpc<T = unknown>(method: string, params: Record<string, unknown> = {}): Promise<T> {
  return invoke<T>("rpc_call", { method, params });
}

export interface SQLExecuteResult {
  ok: boolean;
  error?: string;
  phase?: "validate" | "execute" | string;
  columns?: QueryColumn[];
  rows?: unknown[][];
  row_count?: number;
  truncated?: boolean;
  executed_ms?: number;
}

export interface SQLValidationResult {
  ok: boolean;
  error: string | null;
}

export type TableSchema = Record<string, Array<{ name: string; type: string }>>;

export interface SqlTemplate {
  id: string;
  category: string;
  label: string;
  description: string;
  sql: string;
}

// ----- Multi-archive comparison (Sprint 2 Phase G) -----

export interface ComparisonMetric {
  key: string;
  label: string;
  a: number;
  b: number;
  delta: number;
  delta_percent: number | null;
}

export interface CompareSummaryResult {
  ok: boolean;
  error?: string;
  metrics?: ComparisonMetric[];
}

export interface SlowQueryDiffRow {
  sql_text_hash: string;
  query: string | null;
  a_avg_ms: number;
  b_avg_ms: number;
  a_calls: number;
  b_calls: number;
  delta_percent: number;
}

export interface SlowQueryOnly {
  sql_text_hash: string;
  query: string | null;
  calls: number;
  total_ms: number;
  avg_ms: number;
}

// Sprint 11 Phase E — Performance Regression Tracking types
export type RegressionChangeType =
  | "regression"
  | "improvement"
  | "new"
  | "disappeared"
  | "stable";

export type RegressionConfidence = "high" | "medium" | "low";

export interface RegressionResultDto {
  operation_name: string;
  context_signature: string;
  change_type: RegressionChangeType;
  confidence: RegressionConfidence;
  baseline_p50_ms: number | null;
  baseline_p95_ms: number | null;
  baseline_count: number | null;
  current_p50_ms: number | null;
  current_p95_ms: number | null;
  current_count: number | null;
  p95_ratio: number | null;
  count_ratio: number | null;
  priority_score: number;
}

export interface RegressionSummary {
  total_operations_matched: number;
  total_regressions: number;
  total_improvements: number;
  total_new: number;
  total_disappeared: number;
  total_stable: number;
  threshold: number;
  min_samples: number;
}

export interface RegressionComputeResult {
  ok: boolean;
  error?: string;
  details?: string;
  summary?: RegressionSummary;
  regressions?: RegressionResultDto[];
  improvements?: RegressionResultDto[];
  new?: RegressionResultDto[];
  disappeared?: RegressionResultDto[];
  stable_count?: number;
}

export interface CompareSlowQueriesResult {
  ok: boolean;
  error?: string;
  in_both?: SlowQueryDiffRow[];
  regressed?: SlowQueryDiffRow[];
  improved?: SlowQueryDiffRow[];
  only_a?: SlowQueryOnly[];
  only_b?: SlowQueryOnly[];
}

// ----- Pre-built views (Sprint 2 Phase D) -----

export interface ViewFiltersDto {
  time_from?: string | null;
  time_to?: string | null;
  process_role?: string | null;
  event_type?: string | null;
}

export interface ViewResult {
  ok: boolean;
  error?: string;
  phase?: string;
  columns?: QueryColumn[];
  rows?: unknown[][];
  row_count?: number;
  /** Общее число строк до LIMIT (по тем же filter conditions). Заполняется
   *  только для views с limit (slow_queries / errors_feed / top_business_operations). */
  total_rows?: number;
  truncated?: boolean;
  executed_ms?: number;
  bucket?: string;
  /** Distinct event_type из всего архива (по фильтрам). [[type, count], ...].
   *  Заполняется errors_feed — нужно для UI-фильтра, который не может строиться
   *  из ограниченного rows. */
  event_types?: [string, number][];
}

interface SubTable {
  columns: QueryColumn[];
  rows: unknown[][];
  row_count: number;
}

export interface OperationAnatomyResult {
  ok: boolean;
  error?: string;
  summary: {
    operation: string;
    found: boolean;
    total_events?: number;
    total_duration_ms?: number;
    avg_duration_ms?: number;
    max_duration_ms?: number;
    min_duration_ms?: number;
    unique_sessions?: number;
    unique_processes?: number;
    process_roles?: string | null;
    exception_count?: number;
    lock_count?: number;
    sql_count?: number;
    first_seen?: string | null;
    last_seen?: string | null;
    wall_clock_ms?: number;
  };
  timeline: SubTable;
  breakdown: Array<{
    event_type: string;
    events: number;
    total_duration_ms: number;
    avg_duration_ms: number;
  }>;
  top_sql: SubTable;
  related_exceptions: SubTable;
}

export interface RuleClassifyResult {
  ok: boolean;
  matched: boolean;
  rule_id?: string;
  title?: string;
  body?: string;
  priority?: number;
  error?: string;
}

export interface AiExplanationResult {
  ok: boolean;
  text?: string;
  from_cache?: boolean;
  model?: string;
  tokens_in?: number;
  tokens_out?: number;
  elapsed_ms?: number;
  created_at?: string;
  enabled?: boolean;
  error?: string;
}

export interface ExplainerStatus {
  ok: boolean;
  ai_enabled: boolean;
  model: string | null;
  rules_count: number;
  cache_entries: number;
}

export interface ExplainerCacheCheckResult {
  ok: boolean;
  found: boolean;
  text?: string;
  model?: string;
  tokens_in?: number;
  tokens_out?: number;
  created_at?: string;
}

export interface ExplainerCacheEntry {
  cache_key: string;
  archive_id: string;
  anatomy_kind: string;
  target_id: string;
  rule_id: string | null;
  ai_text_len: number;
  model: string;
  tokens_in: number;
  tokens_out: number;
  created_at: string;
}

export interface DeadlockAnatomyResult {
  ok: boolean;
  error?: string;
  found: boolean;
  event_id?: number;
  event?: {
    id: number;
    ts: string;
    session_id: number | null;
    user_name: string | null;
    process_role: string | null;
    process_pid: number | null;
    context: string | null;
    context_normalized: string | null;
    duration_ms: number | null;
  };
  parsed_extra?: {
    regions: Array<{ raw: string; object_name: string; mode: string | null }>;
    wait_connections: string[];
    edges: Array<{ waiter: string; blocker: string; resource: string }>;
    raw_extra: Record<string, unknown>;
    _parse_error?: boolean;
  };
  participants?: string[];
  surrounding?: SubTable & { window_seconds: number };
}

export interface SessionAnatomyResult {
  ok: boolean;
  error?: string;
  summary: {
    session_id: number;
    found: boolean;
    total_events?: number;
    users?: string | null;
    process_roles?: string | null;
    process_pids?: string | null;
    distinct_operations?: number;
    total_duration_ms?: number;
    exception_count?: number;
    lock_count?: number;
    sql_count?: number;
    first_seen?: string | null;
    last_seen?: string | null;
    wall_clock_ms?: number;
  };
  timeline: SubTable;
  breakdown: Array<{
    event_type: string;
    events: number;
    total_duration_ms: number;
  }>;
  top_sql: SubTable;
}

// Sprint 6 — bsl-language-server adapter
export type BslLsSeverity = "Blocker" | "Critical" | "Major" | "Minor" | "Info";

export interface BslLsPosition {
  line: number;
  character: number;
}

export interface BslLsRange {
  start: BslLsPosition;
  end: BslLsPosition;
}

export interface BslLsDiagnostic {
  code: string;
  code_description_href: string | null;
  message: string;
  range: BslLsRange;
  severity: BslLsSeverity;
  source: string;
  tags: string[];
  snippet: string | null;
}

export interface BslLsDiagnosticGroup {
  range: BslLsRange;
  severity: BslLsSeverity;
  codes: string[];
  messages: string[];
  snippet: string | null;
  primary: BslLsDiagnostic;
}

export interface BslLsAnalyzeResult {
  ok: boolean;
  error?: string;
  details?: string;
  hint?: string;
  diagnostics?: BslLsDiagnostic[];
  grouped?: BslLsDiagnosticGroup[];
  parse_success?: boolean;
  analysis_duration_ms?: number;
  bsl_ls_version?: string;
  configuration_root?: string | null;
  configuration_connected?: boolean;
}

export interface BslLsStatus {
  ok: boolean;
  binaries_available: boolean;
  binaries_source: string | null;
  binaries_error: string | null;
  configuration_connected: boolean;
  configuration_root: string | null;
  configuration_info: {
    name: string;
    synonym_ru: string;
    vendor: string;
    version: string;
    source_path: string;
    indexed_at: string;
    object_count: number;
  } | null;
  bsl_ls_version: string;
}

// Sprint 4 — Query Analyzer (legacy regex-based, остаётся как secondary)
export interface QAFinding {
  source: "native" | "bsl-language-server";
  rule_id: string;
  severity: "critical" | "warning" | "info";
  category: "performance" | "correctness" | "style";
  line_start: number;
  line_end: number;
  col_start: number;
  col_end: number;
  message: string;
  explanation_md: string;
  tags: string[];
  solution_template_id: string | null;
}

export interface QAAnalyzeResult {
  ok: boolean;
  query_text: string;
  findings: QAFinding[];
  bsl_ls_available: boolean;
  summary: { critical: number; warning: number; info: number };
  rules_count: number;
}

export interface QARewriteChange {
  what: string;
  why: string;
  lines_in_original?: number[];
}

export interface QARewriteResult {
  ok: boolean;
  from_cache?: boolean;
  rewritten_query?: string;
  changes?: QARewriteChange[];
  notes_for_developer?: string;
  estimated_improvement?: string;
  model?: string;
  tokens_in?: number;
  tokens_out?: number;
  elapsed_ms?: number;
  error?: string;
  enabled?: boolean;
}

export interface QAStatus {
  ok: boolean;
  native_rules_count: number;
  /** Sprint 5: количество загруженных semantic rules. */
  semantic_rules_count?: number;
  bsl_ls_available: boolean;
  ai_enabled: boolean;
  model: string | null;
  cache_entries: number;
  /** Sprint 5: подключена ли XML-выгрузка конфигурации. */
  configuration_connected?: boolean;
}

/* ---------------- Sprint 5 — Configuration metadata ---------------- */

/** Описание конфигурации (имя, синоним, поставщик, версия). */
export interface ConfigurationInfo {
  name: string;
  synonym_ru: string;
  vendor: string;
  version: string;
}

/** Ответ configuration.connect / configuration.reindex. */
export interface ConfigurationConnectResult {
  ok: boolean;
  error?: string;
  status?: "indexed" | "already_indexed";
  object_count?: number;
  by_kind?: Record<string, number>;
  configuration?: ConfigurationInfo;
  indexed_at?: string;
  source_path?: string;
}

/** Ответ configuration.status — два варианта (connected / not connected). */
export interface ConfigurationStatusResult {
  ok: boolean;
  connected: boolean;
  source_path?: string;
  indexed_at?: string;
  object_count?: number;
  by_kind?: Record<string, number>;
  configuration?: ConfigurationInfo;
}

/* ---------------- Sprint 7 — Plan Analyzer ---------------- */

/** Одно warning от PerformanceStudio CLI (или нативное из SQL Server engine).
 *  Severity = "Info" | "Warning" | "Critical" (PerformanceStudio scheme),
 *  отдельная от bsl-LS severity — у Plan Analyzer своя номенклатура (ADR-040). */
export interface PlanWarning {
  type: string;
  severity: string;
  message: string;
  operator?: string | null;
  node_id?: number | null;
  max_benefit_percent?: number | null;
  actionable_fix?: string | null;
  is_legacy?: boolean;
}

export interface PlanMissingIndex {
  table: string;
  impact: number;
  equality_columns: string[];
  inequality_columns: string[];
  include_columns: string[];
  create_statement: string;
}

export interface PlanMemoryGrant {
  requested_kb: number;
  granted_kb: number;
  max_used_kb: number;
  grant_wait_ms: number;
  feedback_adjusted?: string | null;
  estimated_available_memory_grant_kb: number;
  desired_kb: number;
  serial_required_kb: number;
}

export interface PlanQueryTime {
  cpu_time_ms: number;
  elapsed_time_ms: number;
  external_wait_ms: number;
}

export interface PlanOperator {
  node_id: number;
  physical_op: string;
  logical_op: string;
  cost_percent: number;
  estimated_rows: number;
  estimated_cost: number;
  estimated_io: number;
  estimated_cpu: number;
  object_name?: string | null;
  index_name?: string | null;
  seek_predicates?: string | null;
  predicate?: string | null;
  parallel?: boolean;
  actual_rows?: number | null;
  actual_elapsed_ms?: number | null;
  actual_cpu_ms?: number | null;
  warnings?: PlanWarning[];
  children?: PlanOperator[];
}

export interface PlanStatement {
  statement_text: string;
  statement_type: string;
  estimated_cost: number;
  estimated_rows: number;
  optimization_level?: string | null;
  early_abort_reason?: string | null;
  cardinality_estimation_model?: number;
  compile_time_ms?: number;
  compile_memory_kb?: number;
  cached_plan_size_kb?: number;
  degree_of_parallelism?: number;
  non_parallel_reason?: string | null;
  query_hash?: string | null;
  query_plan_hash?: string | null;
  memory_grant?: PlanMemoryGrant | null;
  query_time?: PlanQueryTime | null;
  warnings: PlanWarning[];
  missing_indexes: PlanMissingIndex[];
  operator_tree?: PlanOperator | null;
}

export interface PlanAnalysisSummary {
  total_statements: number;
  total_warnings: number;
  critical_warnings: number;
  missing_indexes: number;
  has_actual_stats: boolean;
  max_estimated_cost: number;
  warning_types: string[];
}

export interface PlanAnalysisResult {
  plan_source: string;
  sql_server_version?: string | null;
  sql_server_build?: string | null;
  statements: PlanStatement[];
  summary: PlanAnalysisSummary;
}

export interface PlanAnalyzeResponse {
  ok: boolean;
  error?: string;
  details?: string;
  hint?: string;
  result?: PlanAnalysisResult;
  file_name?: string;
}

export interface PlanAnalyzerStatus {
  ok: boolean;
  available: boolean;
  binary_path: string | null;
  version: string;
  rules_count: number;
}

// Sprint 7 Phase D + Sprint 8 Phase B — TJ archive plan import (MSSQL + PG)
export type PlanEngine = "mssql" | "postgres";

export interface PlanAnalyzerTjItem {
  event_id: number;
  ts: string | null;
  duration_us: number | null;
  sql_preview: string;
  plan_size_bytes: number;
  context: string | null;
  // Sprint 8 Phase B — движок СУБД источника плана. UI использует это для
  // показа badge (MSSQL / PG) и выбора view (PlanVisualization vs PgPlanTextView).
  engine?: PlanEngine | null;
}

export interface PlanAnalyzerTjListResponse {
  ok: boolean;
  error?: string;
  details?: string;
  items?: PlanAnalyzerTjItem[];
  total?: number;
  // false → в архиве нет ни одного события с plan_text. UI показывает
  // banner с инструкцией про <plansql/> в logcfg.xml.
  has_planSQLText?: boolean;
  // Sprint 8 Phase B — разбивка по engine (для UI filter toggle).
  // Например: { mssql: 156, postgres: 42 }
  counts_by_engine?: Partial<Record<PlanEngine | "unknown", number>>;
}

export interface PlanAnalyzerTjPlanResponse {
  ok: boolean;
  error?: string;
  details?: string;
  event_id?: number;
  sql_text?: string;
  plan_text?: string;
  ts?: string | null;
  duration_us?: number | null;
  context?: string | null;
  // Sprint 8 Phase B.
  engine?: PlanEngine | null;
}

// Sprint 8 Phase B — PG connections + re-EXPLAIN.
export interface PgConnectionPublic {
  id: number;
  name: string;
  host: string;
  port: number;
  database: string;
  username: string;
  created_at: string;
  last_used_at: string | null;
  is_default: boolean;
}

export interface PgListConnectionsResponse {
  ok: boolean;
  error?: string;
  details?: string;
  items?: PgConnectionPublic[];
  total?: number;
}

export interface PgConnectionResponse {
  ok: boolean;
  error?: string;
  details?: string;
  connection?: PgConnectionPublic;
}

export interface PgTestConnectionResponse {
  ok: boolean;
  error?: string;
  details?: string;
  version?: string;
  is_1c_build?: boolean;
}

export interface PlanAnalyzerReExplainResponse {
  ok: boolean;
  error?: string;
  details?: string;
  plan_json?: string;
  engine?: "postgres";
}

// Sprint 8 Phase C — SQL antipatterns
export type SqlAntipatternSeverity =
  | "Critical"
  | "Warning"
  | "Info"
  | "Blocker"
  | "Major"
  | "Minor";

export interface SqlAntipatternFinding {
  code: string;
  title: string;
  description: string;
  severity: SqlAntipatternSeverity;
  dialect: PlanEngine;
  is_1c_context_only: boolean;
  snippet: string | null;
  rationale: string;
  recommendation: string;
}

export interface SqlAntipatternsResponse {
  ok: boolean;
  error?: string;
  engine?: PlanEngine;
  is_1c_context?: boolean;
  findings?: SqlAntipatternFinding[];
}

export interface SavedQuery {
  id: number;
  name: string;
  description: string | null;
  query: string;
  created_at: string | null;
  last_run_at: string | null;
  run_count: number;
}

export const backend = {
  ping: () => rpc<{ status: string; version: string }>("ping"),
  getAppInfo: () => rpc<AppInfo>("get_app_info"),
  loadArchive: (path: string) => rpc<ArchiveState>("load_archive", { path }),
  loadDirectory: (path: string) => rpc<ArchiveState>("load_directory", { path }),
  cancelIngestion: (archive_id: string) =>
    rpc<{ ok: boolean; reason?: string; status?: string }>("cancel_ingestion", { archive_id }),
  getArchiveStatus: (archive_id: string) => rpc<ArchiveState>("get_archive_status", { archive_id }),
  listRecentArchives: () => rpc<RecentArchive[]>("list_recent_archives"),
  listStoredArchives: () => rpc<StoredArchivesResponse>("list_stored_archives"),
  deleteArchive: (archive_id: string) => rpc<DeleteArchiveResult>("delete_archive", { archive_id }),
  deleteAllArchives: () => rpc<DeleteAllArchivesResult>("delete_all_archives"),
  unloadArchive: (archive_id: string) => rpc<{ ok: boolean }>("unload_archive", { archive_id }),
  openStoredArchive: (archive_id: string) =>
    rpc<ArchiveState>("open_stored_archive", { archive_id }),
  queryEventsPreset: (archive_id: string, preset: "first_100" | "longest" | "deadlocks", limit = 100) =>
    rpc<QueryResult>("query_events_preset", { archive_id, preset, limit }),
  getStorageStats: (archive_id: string) => rpc<StorageStats>("get_storage_stats", { archive_id }),
  sidecarStatus: () => invoke<boolean>("sidecar_status"),

  // SQL Engine (Sprint 2 Phase B)
  executeSql: (archive_id: string, sql: string, max_rows = 10000) =>
    rpc<SQLExecuteResult>("execute_sql", { archive_id, sql, max_rows }),
  validateSql: (sql: string) => rpc<SQLValidationResult>("validate_sql", { sql }),
  getSchema: (archive_id: string) => rpc<TableSchema>("get_schema", { archive_id }),
  listSqlTemplates: () => rpc<SqlTemplate[]>("list_sql_templates"),

  // Multi-archive comparison (Sprint 2 Phase G)
  compareSummary: (archive_id_a: string, archive_id_b: string) =>
    rpc<CompareSummaryResult>("compare_summary", { archive_id_a, archive_id_b }),
  compareSlowQueries: (archive_id_a: string, archive_id_b: string, limit = 50) =>
    rpc<CompareSlowQueriesResult>("compare_slow_queries", { archive_id_a, archive_id_b, limit }),

  // Sprint 11 Phase E — Performance Regression Tracking
  regressionCompute: (
    baseline_archive_id: string,
    current_archive_id: string,
    threshold = 2.0,
    min_samples = 5,
    top_n = 50,
  ) =>
    rpc<RegressionComputeResult>("regression.compute", {
      baseline_archive_id,
      current_archive_id,
      threshold,
      min_samples,
      top_n,
    }),

  // Pre-built views (Sprint 2 Phase D)
  viewSlowQueries: (archive_id: string, filters?: ViewFiltersDto, sort_by = "total_duration", limit = 100) =>
    rpc<ViewResult>("view_slow_queries", { archive_id, filters, sort_by, limit }),
  viewLocksTimeline: (archive_id: string, filters?: ViewFiltersDto, limit = 5000) =>
    rpc<ViewResult>("view_locks_timeline", { archive_id, filters, limit }),
  viewProcessRoles: (archive_id: string, filters?: ViewFiltersDto) =>
    rpc<ViewResult>("view_process_roles", { archive_id, filters }),
  viewDurationHistogram: (archive_id: string, filters?: ViewFiltersDto) =>
    rpc<ViewResult>("view_duration_histogram", { archive_id, filters }),
  viewErrorsFeed: (
    archive_id: string,
    filters?: ViewFiltersDto,
    limit = 500,
    event_types?: string[],
    context_presence?: "with" | "without",
  ) =>
    rpc<ViewResult>("view_errors_feed", {
      archive_id,
      filters,
      limit,
      ...(event_types && event_types.length > 0 ? { event_types } : {}),
      ...(context_presence ? { context_presence } : {}),
    }),
  viewActivityHeatmap: (archive_id: string, filters?: ViewFiltersDto, metric = "count") =>
    rpc<ViewResult>("view_activity_heatmap", { archive_id, filters, metric }),

  // Top Business Operations (Sprint 3 Phase B)
  viewTopBusinessOperations: (
    archive_id: string,
    filters?: ViewFiltersDto,
    sort_by = "total_duration_ms",
    limit = 100,
    event_types?: string[],
  ) =>
    rpc<ViewResult>("view_top_business_operations", {
      archive_id,
      filters,
      sort_by,
      limit,
      event_types,
    }),

  // Operation / Session Anatomy (Sprint 3 Phase C)
  viewOperationAnatomy: (archive_id: string, operation: string) =>
    rpc<OperationAnatomyResult>("view_operation_anatomy", { archive_id, operation }),
  viewSessionAnatomy: (archive_id: string, session_id: number) =>
    rpc<SessionAnatomyResult>("view_session_anatomy", { archive_id, session_id }),

  // Deadlock Anatomy (Sprint 3 Phase D)
  viewListDeadlocks: (archive_id: string, limit = 200) =>
    rpc<ViewResult>("view_list_deadlocks", { archive_id, limit }),
  viewDeadlockAnatomy: (archive_id: string, event_id: number, window_seconds = 30) =>
    rpc<DeadlockAnatomyResult>("view_deadlock_anatomy", { archive_id, event_id, window_seconds }),

  // Explainer engine (Sprint 3 Phase E/F)
  explainerClassify: (
    archive_id: string,
    anatomy_kind: string,
    target_id: string,
    features: Record<string, unknown>,
  ) =>
    rpc<RuleClassifyResult>("explainer_classify", { archive_id, anatomy_kind, target_id, features }),
  explainerAi: (
    archive_id: string,
    anatomy_kind: string,
    target_id: string,
    anatomy_data: Record<string, unknown>,
    rule_id: string | null,
    rule_body: string | null,
    force_refresh = false,
  ) =>
    rpc<AiExplanationResult>("explainer_ai", {
      archive_id, anatomy_kind, target_id, anatomy_data, rule_id, rule_body, force_refresh,
    }),
  explainerCheckCache: (
    archive_id: string,
    anatomy_kind: string,
    target_id: string,
  ) =>
    rpc<ExplainerCacheCheckResult>("explainer_check_cache", {
      archive_id, anatomy_kind, target_id,
    }),
  explainerStatus: () => rpc<ExplainerStatus>("explainer_status"),
  explainerReloadRules: () => rpc<{ ok: boolean; rules_count: number }>("explainer_reload_rules"),

  // DevTools (admin) — список и очистка кеша. Не вызывается из обычного UI.
  explainerCacheList: (limit = 500) =>
    rpc<{ ok: boolean; entries: ExplainerCacheEntry[] }>("explainer_cache_list", { limit }),
  explainerCacheClearAll: () =>
    rpc<{ ok: boolean; removed: number }>("explainer_cache_clear_all"),
  explainerCacheClearArchive: (archive_id: string) =>
    rpc<{ ok: boolean; removed: number }>("explainer_cache_clear_archive", { archive_id }),
  explainerCacheDeleteEntry: (cache_key: string) =>
    rpc<{ ok: boolean; deleted: boolean }>("explainer_cache_delete_entry", { cache_key }),

  // Sprint 4 — Query Analyzer
  queryAnalyzerAnalyze: (query_text: string) =>
    rpc<QAAnalyzeResult>("query_analyzer.analyze", { query_text }),
  queryAnalyzerRewrite: (
    query_text: string,
    findings: QAFinding[],
    force_refresh = false,
  ) => rpc<QARewriteResult>("query_analyzer.rewrite", { query_text, findings, force_refresh }),
  queryAnalyzerStatus: () => rpc<QAStatus>("query_analyzer.status"),

  // Sprint 6 — bsl-language-server adapter (production-grade SDBL analyzer)
  bslLsAnalyze: (query_sdbl: string, enabled_rules?: string[]) =>
    rpc<BslLsAnalyzeResult>("bsl_ls.analyze", { query_sdbl, enabled_rules }),
  bslLsStatus: () => rpc<BslLsStatus>("bsl_ls.status"),

  // Sprint 7 — Plan Analyzer (PerformanceStudio CLI + html-query-plan visualizer + AI)
  planAnalyzerAnalyzeFile: (file_path: string, warnings_only = false) =>
    rpc<PlanAnalyzeResponse>("plan_analyzer.analyze_file", { file_path, warnings_only }),
  planAnalyzerAnalyzeXml: (plan_xml: string, warnings_only = false) =>
    rpc<PlanAnalyzeResponse>("plan_analyzer.analyze_xml", { plan_xml, warnings_only }),
  planAnalyzerStatus: () => rpc<PlanAnalyzerStatus>("plan_analyzer.status"),
  // Sprint 7 Phase D + Sprint 8 Phase B — импорт планов из загруженного ТЖ архива.
  // engine: optional filter ("mssql" / "postgres" / undefined для всех).
  planAnalyzerListTjPlans: (
    archive_id: string,
    limit = 100,
    offset = 0,
    engine?: PlanEngine,
  ) =>
    rpc<PlanAnalyzerTjListResponse>("plan_analyzer.list_tj_plans", {
      archive_id,
      limit,
      offset,
      engine,
    }),
  planAnalyzerGetTjPlan: (archive_id: string, event_id: number) =>
    rpc<PlanAnalyzerTjPlanResponse>("plan_analyzer.get_tj_plan", { archive_id, event_id }),

  // Sprint 8 Phase B — PostgreSQL connections + re-EXPLAIN.
  pgListConnections: () =>
    rpc<PgListConnectionsResponse>("pg.list_connections"),
  pgAddConnection: (
    name: string,
    host: string,
    port: number,
    database: string,
    username: string,
    password: string,
  ) =>
    rpc<PgConnectionResponse>("pg.add_connection", {
      name,
      host,
      port,
      database,
      username,
      password,
    }),
  pgDeleteConnection: (connection_id: number) =>
    rpc<{ ok: boolean; error?: string; details?: string }>(
      "pg.delete_connection",
      { connection_id },
    ),
  pgSetDefault: (connection_id: number) =>
    rpc<{ ok: boolean; error?: string; details?: string }>(
      "pg.set_default",
      { connection_id },
    ),
  pgTestConnection: (connection_id: number) =>
    rpc<PgTestConnectionResponse>("pg.test_connection", { connection_id }),
  pgTestConnectionForm: (
    host: string,
    port: number,
    database: string,
    username: string,
    password: string,
  ) =>
    rpc<PgTestConnectionResponse>("pg.test_connection_form", {
      host,
      port,
      database,
      username,
      password,
    }),
  planAnalyzerReExplain: (
    sql: string,
    connection_id?: number,
    timeout_seconds = 30.0,
  ) =>
    rpc<PlanAnalyzerReExplainResponse>("plan_analyzer.re_explain", {
      sql,
      connection_id,
      timeout_seconds,
    }),

  // Sprint 8 Phase C — SQL antipatterns detection
  sqlAntipatternsDetect: (
    sql: string,
    engine: PlanEngine,
    force_1c_context?: boolean | null,
  ) =>
    rpc<SqlAntipatternsResponse>("sql_antipatterns.detect", {
      sql,
      engine,
      force_1c_context: force_1c_context ?? null,
    }),

  // Sprint 10 — TJ Config Builder
  logcfgDetectPlatform: () =>
    rpc<{ version: string; confidence: "high" | "medium" | "low" }>(
      "logcfg.detect_platform",
    ),

  // Sprint 5 — Configuration metadata
  configurationConnect: (path: string) =>
    rpc<ConfigurationConnectResult>("configuration.connect", { path }),
  configurationStatus: () => rpc<ConfigurationStatusResult>("configuration.status"),
  configurationDisconnect: () => rpc<{ ok: boolean }>("configuration.disconnect"),
  configurationReindex: () => rpc<ConfigurationConnectResult>("configuration.reindex"),
  queryAnalyzerReloadRules: () =>
    rpc<{ ok: boolean; rules_count: number }>("query_analyzer.reload_rules"),

  // Saved queries
  listSavedQueries: () => rpc<SavedQuery[]>("list_saved_queries"),
  saveQuery: (name: string, query: string, description?: string) =>
    rpc<{ id: number }>("save_query", description ? { name, query, description } : { name, query }),
  deleteSavedQuery: (id: number) => rpc<{ ok: boolean }>("delete_saved_query", { id }),
  renameSavedQuery: (id: number, new_name: string) =>
    rpc<{ ok: boolean }>("rename_saved_query", { id, new_name }),
  markQueryRun: (id: number) => rpc<{ ok: boolean }>("mark_query_run", { id }),
};

export type Backend = typeof backend;

/** Подписка на push-notifications прогресса от backend (ADR-012).
 *
 *  Возвращает функцию отписки. Под капотом — Tauri event 'rpc-notification:progress'.
 */
export function onProgress(cb: (e: ProgressEvent) => void): () => void {
  let unlisten: UnlistenFn | undefined;
  let cancelled = false;
  listen<ProgressEvent>("rpc-notification:progress", (event) => {
    cb(event.payload);
  }).then((fn) => {
    if (cancelled) {
      fn();
    } else {
      unlisten = fn;
    }
  });
  return () => {
    cancelled = true;
    unlisten?.();
  };
}
