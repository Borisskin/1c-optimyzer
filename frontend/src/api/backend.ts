// JSON-RPC wrapper over Tauri invoke -> Rust shell -> Python sidecar.

import { invoke } from "@tauri-apps/api/core";

export interface ArchiveState {
  archive_id: string;
  path: string;
  size_bytes: number;
  file_count: number;
  status: "loading" | "extracting" | "parsing" | "ready" | "error";
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

async function rpc<T = unknown>(method: string, params: Record<string, unknown> = {}): Promise<T> {
  return invoke<T>("rpc_call", { method, params });
}

export const backend = {
  ping: () => rpc<{ status: string; version: string }>("ping"),
  getAppInfo: () => rpc<AppInfo>("get_app_info"),
  loadArchive: (path: string) => rpc<ArchiveState>("load_archive", { path }),
  getArchiveStatus: (archive_id: string) => rpc<ArchiveState>("get_archive_status", { archive_id }),
  listRecentArchives: () => rpc<RecentArchive[]>("list_recent_archives"),
  unloadArchive: (archive_id: string) => rpc<{ ok: boolean }>("unload_archive", { archive_id }),
  queryEventsPreset: (archive_id: string, preset: "first_100" | "longest" | "deadlocks", limit = 100) =>
    rpc<QueryResult>("query_events_preset", { archive_id, preset, limit }),
  getStorageStats: (archive_id: string) => rpc<StorageStats>("get_storage_stats", { archive_id }),
  sidecarStatus: () => invoke<boolean>("sidecar_status"),
};

export type Backend = typeof backend;
