import { create } from "zustand";
import type { ArchiveState, ProgressEvent, QueryResult, StorageStats, ViewFiltersDto } from "@/api/backend";

export type ScreenId =
  | "sql"
  | "slow-queries"
  | "locks"
  | "process-roles"
  | "duration"
  | "errors"
  | "activity"
  | "comparison"
  | "dashboard"
  | "apdex"
  | "workbench"
  | "cluster"
  | "indexes"
  | "profiler"
  | "health"
  | "predictive"
  | "resolution"
  | "multibase"
  | "knowledge"
  | "alerts"
  | "reports"
  | "mobile";

export interface ToastMessage {
  id: number;
  text: string;
  tone: "info" | "ok" | "warn" | "err";
}

/** Cross-filter state применяется ко всем views (Phase E, ADR-017).
 *
 *  Любая view может выставить filter; остальные views на следующем render
 *  re-fetch'ятся через useView dep. Поле source_view — для debug и для
 *  условного "уведомления" откуда фильтр пришёл.
 */
export interface CrossFilters {
  time_from: string | null;
  time_to: string | null;
  process_role: string | null;
  event_type: string | null;
  source_view: string | null;
}

export const EMPTY_FILTERS: CrossFilters = {
  time_from: null,
  time_to: null,
  process_role: null,
  event_type: null,
  source_view: null,
};

export function filtersToDto(f: CrossFilters): ViewFiltersDto {
  return {
    time_from: f.time_from,
    time_to: f.time_to,
    process_role: f.process_role,
    event_type: f.event_type,
  };
}

interface AppStore {
  currentScreen: ScreenId;
  setScreen: (s: ScreenId) => void;

  sidebarOpen: boolean;
  toggleSidebar: () => void;

  cmdOpen: boolean;
  setCmdOpen: (v: boolean) => void;

  archive: ArchiveState | null;
  setArchive: (a: ArchiveState | null) => void;

  ingest: ProgressEvent | null;
  setIngest: (p: ProgressEvent | null) => void;
  progressCardMinimized: boolean;
  setProgressCardMinimized: (v: boolean) => void;

  storageStats: StorageStats | null;
  setStorageStats: (s: StorageStats | null) => void;

  lastResult: QueryResult | null;
  setLastResult: (r: QueryResult | null) => void;

  filters: CrossFilters;
  setFilters: (patch: Partial<CrossFilters>) => void;
  clearFilters: () => void;

  toasts: ToastMessage[];
  pushToast: (text: string, tone?: ToastMessage["tone"]) => void;
  dismissToast: (id: number) => void;
}

let _toastCounter = 0;

export const useAppStore = create<AppStore>((set) => ({
  currentScreen: "sql",
  setScreen: (s) => set({ currentScreen: s }),

  sidebarOpen: false,
  toggleSidebar: () => set((st) => ({ sidebarOpen: !st.sidebarOpen })),

  cmdOpen: false,
  setCmdOpen: (v) => set({ cmdOpen: v }),

  archive: null,
  setArchive: (a) => set({ archive: a }),

  ingest: null,
  setIngest: (p) => set({ ingest: p }),
  progressCardMinimized: false,
  setProgressCardMinimized: (v) => set({ progressCardMinimized: v }),

  storageStats: null,
  setStorageStats: (s) => set({ storageStats: s }),

  lastResult: null,
  setLastResult: (r) => set({ lastResult: r }),

  filters: EMPTY_FILTERS,
  setFilters: (patch) => set((st) => ({ filters: { ...st.filters, ...patch } })),
  clearFilters: () => set({ filters: EMPTY_FILTERS }),

  toasts: [],
  pushToast: (text, tone = "info") =>
    set((st) => ({ toasts: [...st.toasts, { id: ++_toastCounter, text, tone }] })),
  dismissToast: (id) => set((st) => ({ toasts: st.toasts.filter((t) => t.id !== id) })),
}));
