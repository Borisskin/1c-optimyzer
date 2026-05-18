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

export type ProgressPhase = "discovering" | "parsing" | "indexing" | "done" | "error";

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
  truncated?: boolean;
  executed_ms?: number;
  bucket?: string;
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
    rpc<{ ok: boolean; reason?: string }>("cancel_ingestion", { archive_id }),
  getArchiveStatus: (archive_id: string) => rpc<ArchiveState>("get_archive_status", { archive_id }),
  listRecentArchives: () => rpc<RecentArchive[]>("list_recent_archives"),
  listStoredArchives: () => rpc<StoredArchivesResponse>("list_stored_archives"),
  deleteArchive: (archive_id: string) => rpc<DeleteArchiveResult>("delete_archive", { archive_id }),
  deleteAllArchives: () => rpc<DeleteAllArchivesResult>("delete_all_archives"),
  unloadArchive: (archive_id: string) => rpc<{ ok: boolean }>("unload_archive", { archive_id }),
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

  // Pre-built views (Sprint 2 Phase D)
  viewSlowQueries: (archive_id: string, filters?: ViewFiltersDto, sort_by = "total_duration", limit = 100) =>
    rpc<ViewResult>("view_slow_queries", { archive_id, filters, sort_by, limit }),
  viewLocksTimeline: (archive_id: string, filters?: ViewFiltersDto, limit = 5000) =>
    rpc<ViewResult>("view_locks_timeline", { archive_id, filters, limit }),
  viewProcessRoles: (archive_id: string, filters?: ViewFiltersDto) =>
    rpc<ViewResult>("view_process_roles", { archive_id, filters }),
  viewDurationHistogram: (archive_id: string, filters?: ViewFiltersDto) =>
    rpc<ViewResult>("view_duration_histogram", { archive_id, filters }),
  viewErrorsFeed: (archive_id: string, filters?: ViewFiltersDto, limit = 500) =>
    rpc<ViewResult>("view_errors_feed", { archive_id, filters, limit }),
  viewActivityHeatmap: (archive_id: string, filters?: ViewFiltersDto, metric = "count") =>
    rpc<ViewResult>("view_activity_heatmap", { archive_id, filters, metric }),

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
