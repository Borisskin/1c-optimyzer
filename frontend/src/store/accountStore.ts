/**
 * accountStore — состояние лицензии/аккаунта в desktop приложении.
 *
 * Архитектура: server = source of truth. Локально храним МИНИМУМ — ровно
 * одно поле, без которого юзер не может работать при старте:
 *
 *   • accessToken (JWT) — persisted в localStorage. Иначе при каждом запуске
 *     нужен повторный login через Yandex. Подмена не страшна — сервер сам
 *     декодирует JWT и проверяет подпись. device_id, user_id зашиты в сам
 *     токен как JWT claims — отдельно их хранить не нужно.
 *
 * Всё остальное (profile, subscription, ai_quota, credits) — мираж от сервера:
 *   • Кеш в памяти (НЕ persisted).
 *   • Загружается на старте через heartbeat.
 *   • Обновляется после каждого track-usage и периодически через useHeartbeat.
 *   • При перезапуске десктопа кратко показываем skeleton, потом данные с сервера.
 *
 * Подмена в localStorage не даёт ничего: все billing-решения (AI explainer,
 * credits spend) проверяются на сервере через checkUsage/trackUsage. Локальный
 * plan='pro' от подмены не активирует Pro-фичи — сервер вернёт paywall.
 */

import { create } from "zustand";

const STORAGE_KEY = "optimyzer.account.v3"; // v3 — только accessToken в персисте

export type SubscriptionPlan = "free" | "pro";

export interface AccountProfile {
  userId: string;
  email: string;
  displayName: string | null;
}

export interface AccountSubscription {
  plan: SubscriptionPlan;
  endsAt: string; // ISO datetime
  proActive: boolean;
}

export interface AccountCache {
  aiQuotaRemaining: number; // -1 = unlimited (Pro)
  creditsRemaining: number;
  lastHeartbeatAt: string | null;
}

export interface AccountState {
  // Persisted (localStorage):
  accessToken: string | null;

  // In-memory only — отражение сервера:
  profile: AccountProfile | null;
  subscription: AccountSubscription | null;
  cache: AccountCache;
  loading: boolean;

  // —— mutators
  /** При старте приложения — подтягивает persisted accessToken в state. */
  hydrate: () => void;
  /** После /v1/license/activate — кладёт token + сразу заполняет state с сервера. */
  activate: (payload: {
    accessToken: string;
    profile: AccountProfile;
    subscription: AccountSubscription;
  }) => void;
  /** Применить ответ /v1/license/heartbeat к локальному состоянию. */
  applyHeartbeat: (payload: {
    plan: SubscriptionPlan;
    endsAt: string;
    aiQuotaRemaining: number;
    creditsRemaining: number;
  }) => void;
  signOut: () => void;

  // —— derived
  isProActive: () => boolean;
}

interface PersistShape {
  accessToken: string | null;
}

function loadPersisted(): PersistShape {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { accessToken: null };
    const parsed = JSON.parse(raw) as PersistShape;
    return { accessToken: parsed.accessToken ?? null };
  } catch {
    return { accessToken: null };
  }
}

function savePersisted(value: PersistShape): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // ignored: quota / private mode
  }
}

function emptyCache(): AccountCache {
  return {
    aiQuotaRemaining: 5, // дефолт пока сервер не ответил (соответствует Free)
    creditsRemaining: 0,
    lastHeartbeatAt: null,
  };
}

export const useAccountStore = create<AccountState>((set, get) => ({
  accessToken: null,
  profile: null,
  subscription: null,
  cache: emptyCache(),
  loading: false,

  hydrate: () => {
    const persisted = loadPersisted();
    set({ accessToken: persisted.accessToken });
  },

  activate: ({ accessToken, profile, subscription }) => {
    savePersisted({ accessToken });
    set({
      accessToken,
      profile,
      subscription,
      cache: {
        aiQuotaRemaining: subscription.proActive ? -1 : 5,
        creditsRemaining: get().cache.creditsRemaining,
        lastHeartbeatAt: new Date().toISOString(),
      },
    });
  },

  applyHeartbeat: ({ plan, endsAt, aiQuotaRemaining, creditsRemaining }) => {
    const current = get();
    const subscription: AccountSubscription = {
      plan,
      endsAt,
      proActive: plan === "pro" && new Date(endsAt) > new Date(),
    };
    set({
      subscription,
      cache: {
        aiQuotaRemaining,
        creditsRemaining,
        lastHeartbeatAt: new Date().toISOString(),
      },
      // profile не трогаем — heartbeat его не возвращает; он подгружается через activate
      // или может быть подгружен отдельно через /v1/auth/me при необходимости.
      profile: current.profile,
    });
  },

  signOut: () => {
    savePersisted({ accessToken: null });
    set({
      accessToken: null,
      profile: null,
      subscription: null,
      cache: emptyCache(),
      loading: false,
    });
  },

  isProActive: () => {
    const s = get().subscription;
    return !!(s && s.proActive && new Date(s.endsAt) > new Date());
  },
}));

// Авто-hydrate accessToken при импорте модуля (один раз).
if (typeof window !== "undefined") {
  useAccountStore.getState().hydrate();
}
