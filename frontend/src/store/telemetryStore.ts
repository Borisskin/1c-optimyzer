/**
 * telemetryStore — буфер событий, отправляется батчем на /v1/telemetry/batch
 * каждые 5 минут или при flush().
 *
 * Privacy:
 *   • Включена по умолчанию для Pro юзеров
 *   • Opt-in для Free (default: false) — см. AccountTab toggle
 *   • Содержимое payload — только anonymous-safe данные (см. utils/telemetry.ts)
 *
 * Storage: пока — localStorage (живёт между запусками). При flush — POST + clear.
 */

import { create } from "zustand";

const STORAGE_KEY = "optimyzer.telemetry.buffer.v1";
const PREFS_KEY = "optimyzer.telemetry.prefs.v1";
const MAX_BUFFER_SIZE = 1000; // если больше — старейшие выбрасываются

export type EventCategory = "tech" | "behavior" | "conversion";

export interface TelemetryEvent {
  device_fingerprint: string;
  app_version: string;
  platform: string;
  category: EventCategory;
  event_type: string;
  payload: Record<string, unknown>;
  timestamp: string; // ISO
}

export interface TelemetryPrefs {
  enabled: boolean;
}

interface TelemetryState {
  buffer: TelemetryEvent[];
  prefs: TelemetryPrefs;
  add: (e: TelemetryEvent) => void;
  clear: () => void;
  setEnabled: (v: boolean) => void;
  hydrate: () => void;
}

function loadBuffer(): TelemetryEvent[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as TelemetryEvent[]) : [];
  } catch {
    return [];
  }
}

function saveBuffer(events: TelemetryEvent[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events.slice(-MAX_BUFFER_SIZE)));
  } catch {
    /* ignored */
  }
}

function loadPrefs(): TelemetryPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (raw) return JSON.parse(raw) as TelemetryPrefs;
  } catch {
    /* ignored */
  }
  // Default: включаем для всех (но юзер может отключить в Settings → Аккаунт)
  return { enabled: true };
}

function savePrefs(prefs: TelemetryPrefs): void {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    /* ignored */
  }
}

export const useTelemetryStore = create<TelemetryState>((set, get) => ({
  buffer: [],
  prefs: { enabled: true },

  hydrate: () => {
    set({ buffer: loadBuffer(), prefs: loadPrefs() });
  },

  add: (event) => {
    if (!get().prefs.enabled) return;
    const next = [...get().buffer, event].slice(-MAX_BUFFER_SIZE);
    saveBuffer(next);
    set({ buffer: next });
  },

  clear: () => {
    saveBuffer([]);
    set({ buffer: [] });
  },

  setEnabled: (v) => {
    const prefs = { enabled: v };
    savePrefs(prefs);
    set({ prefs });
    if (!v) {
      // Юзер отключил — сразу выбрасываем накопленный буфер.
      saveBuffer([]);
      set({ buffer: [] });
    }
  },
}));

// Авто-hydrate один раз.
if (typeof window !== "undefined") {
  useTelemetryStore.getState().hydrate();
}
