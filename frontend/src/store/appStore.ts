import { create } from "zustand";
import type { ArchiveState, ProgressEvent, QueryResult, StorageStats } from "@/api/backend";

export type ScreenId =
  | "sql"
  | "dashboard"
  | "apdex"
  | "workbench"
  | "queries"
  | "locks"
  | "cluster"
  | "indexes"
  | "profiler"
  | "health"
  | "compare"
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

  toasts: [],
  pushToast: (text, tone = "info") =>
    set((st) => ({ toasts: [...st.toasts, { id: ++_toastCounter, text, tone }] })),
  dismissToast: (id) => set((st) => ({ toasts: st.toasts.filter((t) => t.id !== id) })),
}));
