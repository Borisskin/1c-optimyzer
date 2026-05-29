/**
 * configStore — Remote Config с сервера (S13).
 *
 * Desktop тянет конфиг через GET /v1/config при старте и периодически
 * (см. hooks/useRemoteConfig). Конфиг кешируется в localStorage: при
 * недоступности сервера работаем на последнем известном (graceful, не падаем).
 *
 * Дефолт — максимально пермиссивный (discovery): всё включено, AI работает.
 * Применяется при самом первом запуске (ещё не было ни одного fetch) и если
 * localStorage пуст — чтобы продукт не «схлопывался» пока сервер не ответил.
 */

import { create } from "zustand";
import type { MonetizationMode, RemoteConfigPublic } from "@/api/cloud";

const STORAGE_KEY = "optimyzer.remoteconfig.v1";

export const DEFAULT_REMOTE_CONFIG: RemoteConfigPublic = {
  monetization_mode: "discovery",
  ai_kill_switch: false,
  limits: { ai_per_day: null, ai_per_month: null, per_type: {} },
  feature_flags: {
    tj_analysis: true,
    plans: true,
    logcfg: true,
    regressions: true,
    query_analyzer: false,
    sql_console: true,
  },
  config_version: 0,
};

function loadPersisted(): RemoteConfigPublic {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_REMOTE_CONFIG;
    const parsed = JSON.parse(raw) as Partial<RemoteConfigPublic>;
    // Сливаем с дефолтом — на случай если сервер добавил/убрал поля между версиями.
    return {
      ...DEFAULT_REMOTE_CONFIG,
      ...parsed,
      feature_flags: { ...DEFAULT_REMOTE_CONFIG.feature_flags, ...(parsed.feature_flags ?? {}) },
      limits: { ...DEFAULT_REMOTE_CONFIG.limits, ...(parsed.limits ?? {}) },
    };
  } catch {
    return DEFAULT_REMOTE_CONFIG;
  }
}

function persist(config: RemoteConfigPublic): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  } catch {
    /* ignored — localStorage может быть недоступен */
  }
}

interface ConfigState {
  config: RemoteConfigPublic;
  loadedAt: number | null; // ms epoch последнего успешного fetch (null = только дефолт/кеш)
  setConfig: (c: RemoteConfigPublic) => void;
  hydrate: () => void;
}

export const useConfigStore = create<ConfigState>((set) => ({
  config: DEFAULT_REMOTE_CONFIG,
  loadedAt: null,
  setConfig: (config) => {
    persist(config);
    set({ config, loadedAt: Date.now() });
  },
  hydrate: () => {
    set({ config: loadPersisted() });
  },
}));

// Авто-hydrate из localStorage один раз при загрузке модуля.
if (typeof window !== "undefined") {
  useConfigStore.getState().hydrate();
}

// --- Селекторы для применения в UI ---

/** Включён ли модуль/фича. Отсутствующий флаг трактуем как включённый (безопасный дефолт). */
export function useFeatureEnabled(flag: string): boolean {
  return useConfigStore((s) => s.config.feature_flags[flag] ?? true);
}

/** Глобальный AI kill-switch (экстренный стоп AI с сервера). */
export function useAiKillSwitch(): boolean {
  return useConfigStore((s) => s.config.ai_kill_switch);
}

export function useMonetizationMode(): MonetizationMode {
  return useConfigStore((s) => s.config.monetization_mode);
}

/** Не-реактивный доступ (вне React) — например в обработчиках. */
export function isFeatureEnabled(flag: string): boolean {
  return useConfigStore.getState().config.feature_flags[flag] ?? true;
}

export function isAiKillSwitchOn(): boolean {
  return useConfigStore.getState().config.ai_kill_switch;
}
