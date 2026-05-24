/**
 * accountStore — состояние лицензии/аккаунта в desktop приложении.
 *
 * Хранит:
 *   • access_token (JWT для cloud API)
 *   • профиль (email, display_name)
 *   • подписка (plan, ends_at)
 *   • кеш heartbeat (ai_quota_remaining, credits_remaining)
 *
 * Персистентность: пока — localStorage. В Phase 2 переедет в OS keychain
 * через @tauri-apps/plugin-keyring (или custom Rust команду) — JWT в plaintext
 * на диске юзера не подарок.
 */

import { create } from "zustand";

const STORAGE_KEY = "optimyzer.account.v1";
const MAX_OFFLINE_DAYS = 7; // graceful degradation: после 7 дней без heartbeat → Free

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
  accessToken: string | null;
  deviceId: string | null;
  profile: AccountProfile | null;
  subscription: AccountSubscription | null;
  cache: AccountCache;
  // —— mutators
  hydrate: () => void;
  activate: (payload: {
    accessToken: string;
    profile: AccountProfile;
    subscription: AccountSubscription;
    deviceId: string;
  }) => void;
  applyHeartbeat: (payload: {
    plan: SubscriptionPlan;
    endsAt: string;
    aiQuotaRemaining: number;
    creditsRemaining: number;
  }) => void;
  /** После успешного trackUsage — локально декрементируем счётчик, чтобы UI не ждал heartbeat (24ч). */
  applyUsageTracked: (billedAgainst: "free_quota" | "pro_quota" | "credits_balance") => void;
  setOfflineDegradation: () => void;
  signOut: () => void;
  // —— derived
  isProActive: () => boolean;
  isOfflineTooLong: () => boolean;
}

interface PersistShape {
  accessToken: string | null;
  deviceId: string | null;
  profile: AccountProfile | null;
  subscription: AccountSubscription | null;
  cache: AccountCache;
}

function loadFromStorage(): PersistShape {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults();
    const parsed = JSON.parse(raw) as PersistShape;
    return { ...defaults(), ...parsed };
  } catch {
    return defaults();
  }
}

function saveToStorage(value: PersistShape): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // ignored: quota / private mode
  }
}

function defaults(): PersistShape {
  return {
    accessToken: null,
    deviceId: null,
    profile: null,
    subscription: null,
    cache: {
      aiQuotaRemaining: 5, // Free default
      creditsRemaining: 0,
      lastHeartbeatAt: null,
    },
  };
}

export const useAccountStore = create<AccountState>((set, get) => ({
  ...defaults(),

  hydrate: () => {
    const loaded = loadFromStorage();
    set(loaded);
  },

  activate: ({ accessToken, profile, subscription, deviceId }) => {
    const next: PersistShape = {
      accessToken,
      deviceId,
      profile,
      subscription,
      cache: {
        aiQuotaRemaining: subscription.proActive ? -1 : 5,
        creditsRemaining: get().cache.creditsRemaining,
        lastHeartbeatAt: new Date().toISOString(),
      },
    };
    saveToStorage(next);
    set(next);
  },

  applyHeartbeat: ({ plan, endsAt, aiQuotaRemaining, creditsRemaining }) => {
    const current = get();
    const subscription: AccountSubscription = {
      plan,
      endsAt,
      proActive: plan === "pro" && new Date(endsAt) > new Date(),
    };
    const cache: AccountCache = {
      aiQuotaRemaining,
      creditsRemaining,
      lastHeartbeatAt: new Date().toISOString(),
    };
    const next: PersistShape = {
      accessToken: current.accessToken,
      deviceId: current.deviceId,
      profile: current.profile,
      subscription,
      cache,
    };
    saveToStorage(next);
    set(next);
  },

  applyUsageTracked: (billedAgainst) => {
    const current = get();
    let nextAi = current.cache.aiQuotaRemaining;
    let nextCredits = current.cache.creditsRemaining;
    if (billedAgainst === "free_quota") {
      // Free pool — decrement, не уходим ниже 0.
      nextAi = Math.max(0, current.cache.aiQuotaRemaining - 1);
    } else if (billedAgainst === "credits_balance") {
      nextCredits = Math.max(0, current.cache.creditsRemaining - 1);
    } // pro_quota — unlimited, не двигаем
    const next: PersistShape = {
      accessToken: current.accessToken,
      deviceId: current.deviceId,
      profile: current.profile,
      subscription: current.subscription,
      cache: {
        aiQuotaRemaining: nextAi,
        creditsRemaining: nextCredits,
        lastHeartbeatAt: current.cache.lastHeartbeatAt,
      },
    };
    saveToStorage(next);
    set(next);
  },

  setOfflineDegradation: () => {
    const current = get();
    if (!current.subscription) return;
    const downgraded: AccountSubscription = {
      ...current.subscription,
      plan: "free",
      proActive: false,
    };
    const next: PersistShape = {
      accessToken: current.accessToken,
      deviceId: current.deviceId,
      profile: current.profile,
      subscription: downgraded,
      cache: current.cache,
    };
    saveToStorage(next);
    set(next);
  },

  signOut: () => {
    saveToStorage(defaults());
    set(defaults());
  },

  isProActive: () => {
    const s = get().subscription;
    return !!(s && s.proActive && new Date(s.endsAt) > new Date());
  },

  isOfflineTooLong: () => {
    const last = get().cache.lastHeartbeatAt;
    if (!last) return false;
    const ageMs = Date.now() - new Date(last).getTime();
    return ageMs > MAX_OFFLINE_DAYS * 24 * 3600 * 1000;
  },
}));

// Авто-hydrate при импорте модуля (один раз).
if (typeof window !== "undefined") {
  useAccountStore.getState().hydrate();
}
