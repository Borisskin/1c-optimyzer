/**
 * Типизированные обёртки над server API.
 * Имена и payload'ы должны совпадать с server/schemas/*.
 */

import { api } from "./client";

// --- types (mirror of server schemas) ---

export interface UserPublic {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  last_login_at: string | null;
}

export interface SubscriptionRead {
  plan: "free" | "pro";
  status: "active" | "past_due" | "cancelled" | "expired";
  starts_at: string;
  ends_at: string;
  auto_renew: boolean;
  early_adopter: boolean;
  price_locked_kopecks: number;
}

export interface DashboardSummary {
  user: UserPublic;
  subscription: SubscriptionRead;
  credits_remaining: number;
  devices_active: number;
  devices_limit: number;
  ai_operations_this_month: number;
  ai_operations_free_remaining: number;
  pro_active: boolean;
  server_time: string;
}

export interface CreditsPackageRead {
  id: string;
  package: string;
  operations_total: number;
  operations_used: number;
  operations_remaining: number;
  purchased_at: string;
  expires_at: string;
  is_active: boolean;
}

export interface CreditsBalance {
  operations_remaining: number;
  operations_total_purchased: number;
  operations_used_total: number;
  active_packages: CreditsPackageRead[];
}

export interface DeviceRead {
  id: string;
  name: string;
  platform: string;
  app_version: string;
  activated_at: string;
  last_seen_at: string;
  last_ip_masked: string | null;
  is_active: boolean;
}

export interface UsageSummary {
  period_start: string;
  period_end: string;
  ai_operations_count: number;
  ai_operations_by_type: Record<string, number>;
  devices_seen_count: number;
  free_quota_used: number;
  free_quota_limit: number;
  credits_used_this_period: number;
}

// --- endpoints ---

export const apiAuth = {
  me: () => api<{ user: UserPublic }>("/v1/auth/me"),
  yandexLoginUrl: () => api<{ authorize_url: string; state: string }>("/v1/auth/yandex/login"),
  logout: () => api<void>("/v1/auth/logout", { method: "POST" }),
};

export const apiDashboard = {
  summary: () => api<DashboardSummary>("/v1/dashboard/summary"),
};

export const apiSubscriptions = {
  current: () => api<{ subscription: SubscriptionRead }>("/v1/subscriptions/current"),
  cancel: () =>
    api<{ subscription: SubscriptionRead; message: string }>(
      "/v1/subscriptions/cancel",
      { method: "POST" },
    ),
  reactivate: () =>
    api<{ subscription: SubscriptionRead; message: string }>(
      "/v1/subscriptions/reactivate",
      { method: "POST" },
    ),
  purchase: () =>
    api<{ payment_id: string; confirmation_url: string; amount_kopecks: number }>(
      "/v1/subscriptions/purchase",
      { method: "POST" },
    ),
};

export const apiCredits = {
  balance: () => api<CreditsBalance>("/v1/credits/balance"),
  history: () => api<{ items: CreditsPackageRead[] }>("/v1/credits/history"),
  purchase: (pkg: "mini" | "standard" | "bulk") =>
    api<{
      payment_id: string;
      confirmation_url: string;
      amount_kopecks: number;
      package: string;
    }>("/v1/credits/purchase", { method: "POST", body: { package: pkg } }),
};

export const apiDevices = {
  list: () => api<{ devices: DeviceRead[]; limit: number }>("/v1/devices"),
  deactivate: (id: string) =>
    api<DeviceRead>(`/v1/devices/${encodeURIComponent(id)}/deactivate`, { method: "POST" }),
};

export const apiUsage = {
  summary: () => api<UsageSummary>("/v1/usage/summary"),
};

export const apiLicense = {
  /** GET /v1/license/my-key — текущий персональный ключ (создаёт если не было). */
  myKey: () =>
    api<{ key: string; deep_link: string }>("/v1/license/my-key"),
  /** POST /v1/license/regenerate-key — выдать новый, старый отозвать. */
  regenerate: () =>
    api<{ key: string; deep_link: string }>(
      "/v1/license/regenerate-key",
      { method: "POST" },
    ),
};
