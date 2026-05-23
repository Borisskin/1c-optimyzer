/**
 * telemetryStore — буфер событий, отправляется батчем на /v1/telemetry/batch
 * каждые 5 минут или при flush().
 *
 * Telemetry собирается всегда (нет opt-out). Это решение Сергея: метаданных
 * нет персональных данных, юзеру про это знать не обязательно. См.
 * landing/docs/technical/privacy-and-data.html — публичное описание того что
 * собираем, для законодательного compliance (152-ФЗ).
 *
 * Что собираем — только anonymous-safe данные (см. utils/telemetry.ts):
 * размер архивов, переключения экранов, версии. НЕ собираем: содержимое
 * запросов, имена баз, AI-ответы, пользовательские данные.
 *
 * Storage: localStorage (живёт между запусками). При flush — POST + clear.
 * Старая privacy_toggle preferences не используется — оставляем cleanup
 * на случай если у юзера был старый ключ в storage.
 */

import { create } from "zustand";

const STORAGE_KEY = "optimyzer.telemetry.buffer.v1";
const LEGACY_PREFS_KEY = "optimyzer.telemetry.prefs.v1";  // для cleanup
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

interface TelemetryState {
  buffer: TelemetryEvent[];
  add: (e: TelemetryEvent) => void;
  clear: () => void;
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

export const useTelemetryStore = create<TelemetryState>((set, get) => ({
  buffer: [],

  hydrate: () => {
    set({ buffer: loadBuffer() });
    // Cleanup устаревшего privacy-toggle preferences key (был до 23.05.2026).
    try {
      localStorage.removeItem(LEGACY_PREFS_KEY);
    } catch {
      /* ignored */
    }
  },

  add: (event) => {
    const next = [...get().buffer, event].slice(-MAX_BUFFER_SIZE);
    saveBuffer(next);
    set({ buffer: next });
  },

  clear: () => {
    saveBuffer([]);
    set({ buffer: [] });
  },
}));

// Авто-hydrate один раз.
if (typeof window !== "undefined") {
  useTelemetryStore.getState().hydrate();
}
