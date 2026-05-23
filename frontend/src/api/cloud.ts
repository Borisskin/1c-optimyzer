/**
 * Cloud API client — общение с api.optimyzer.pro (server/).
 *
 * Используется для:
 *   • активации лицензии (license/activate)
 *   • heartbeat (license/heartbeat)
 *   • soft cap check / usage tracking
 *   • telemetry batch send (Phase 1.6)
 *
 * Конфигурация base URL — через переменную VITE_CLOUD_API_BASE (vite env).
 * В dev по умолчанию — http://127.0.0.1:8001.
 */

const DEFAULT_BASE = "http://127.0.0.1:8001";

function baseUrl(): string {
  // Vite exposes env vars prefixed VITE_*.
  const url = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env?.VITE_CLOUD_API_BASE;
  return (url && url.replace(/\/+$/, "")) || DEFAULT_BASE;
}

export interface UserInfo {
  id: string;
  email: string;
  display_name: string | null;
}

export interface DeviceInfo {
  id: string;
  name: string;
}

export interface SubscriptionInfo {
  plan: "free" | "pro";
  ends_at: string;
  pro_active: boolean;
}

export interface ActivateResponse {
  access_token: string;
  user: UserInfo;
  device: DeviceInfo;
  subscription: SubscriptionInfo;
}

export interface ActivateConflictPayload {
  detail: string;
  active_devices: Array<{
    id: string;
    name: string;
    platform: string;
    last_seen_at: string;
  }>;
}

export interface HeartbeatResponse {
  subscription_plan: "free" | "pro";
  subscription_ends_at: string;
  ai_quota_remaining: number; // -1 = Pro unlimited
  credits_remaining: number;
}

export interface UsageCheckResponse {
  allowed: boolean;
  reason: string | null;
  billed_against: "free_quota" | "pro_quota" | "credits_balance" | null;
  options: Array<"upgrade" | "buy_credits">;
  free_quota_remaining: number | null;
  credits_remaining: number | null;
  pro_active: boolean;
}

export interface UsageTrackResponse {
  usage_id: string;
  billed_against: "free_quota" | "pro_quota" | "credits_balance";
}

export type CloudErrorReason =
  | "network"
  | "unauthorized"
  | "not_found"
  | "conflict"
  | "denied"
  | "server"
  | "unknown";

export class CloudError extends Error {
  status: number;
  reason: CloudErrorReason;
  payload?: unknown;

  constructor(message: string, status: number, reason: CloudErrorReason, payload?: unknown) {
    super(message);
    this.status = status;
    this.reason = reason;
    this.payload = payload;
  }
}

async function request<T>(
  path: string,
  init: RequestInit & { token?: string },
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.token) headers.set("authorization", `Bearer ${init.token}`);
  if (init.body) headers.set("content-type", "application/json");
  let resp: Response;
  try {
    resp = await fetch(`${baseUrl()}${path}`, { ...init, headers });
  } catch (err) {
    throw new CloudError(`Сетевая ошибка: ${(err as Error).message}`, 0, "network");
  }
  let bodyJson: unknown = undefined;
  const text = await resp.text();
  if (text) {
    try {
      bodyJson = JSON.parse(text);
    } catch {
      bodyJson = text;
    }
  }
  if (!resp.ok) {
    const reason: CloudErrorReason =
      resp.status === 401 || resp.status === 403
        ? "unauthorized"
        : resp.status === 404
          ? "not_found"
          : resp.status === 409
            ? "conflict"
            : resp.status === 402
              ? "denied"
              : resp.status >= 500
                ? "server"
                : "unknown";
    const detail =
      bodyJson && typeof bodyJson === "object" && bodyJson !== null && "detail" in bodyJson
        ? (bodyJson as { detail: unknown }).detail
        : null;
    throw new CloudError(
      typeof detail === "string"
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `HTTP ${resp.status}`,
      resp.status,
      reason,
      bodyJson,
    );
  }
  return bodyJson as T;
}

export const cloud = {
  async activate(input: {
    key: string;
    fingerprint: string;
    deviceName: string;
    platform: "windows" | "macos" | "linux";
    appVersion: string;
  }): Promise<ActivateResponse> {
    return request<ActivateResponse>("/v1/license/activate", {
      method: "POST",
      body: JSON.stringify({
        key: input.key,
        fingerprint: input.fingerprint,
        device_name: input.deviceName,
        platform: input.platform,
        app_version: input.appVersion,
      }),
    });
  },

  async heartbeat(token: string, appVersion: string): Promise<HeartbeatResponse> {
    return request<HeartbeatResponse>("/v1/license/heartbeat", {
      method: "POST",
      body: JSON.stringify({ app_version: appVersion }),
      token,
    });
  },

  async checkUsage(token: string, cost = 1): Promise<UsageCheckResponse> {
    return request<UsageCheckResponse>(`/v1/usage/check?cost=${cost}`, {
      method: "GET",
      token,
    });
  },

  async trackUsage(
    token: string,
    payload: {
      operationType:
        | "ai_explanation"
        | "ai_deadlock_explanation"
        | "ai_rewrite"
        | "ai_slow_query_explanation";
      archiveHash?: string | null;
      costCredits?: number;
      success?: boolean;
      aiTokensInput?: number;
      aiTokensOutput?: number;
      aiCostUsd?: number;
    },
  ): Promise<UsageTrackResponse> {
    return request<UsageTrackResponse>("/v1/usage/track", {
      method: "POST",
      token,
      body: JSON.stringify({
        operation_type: payload.operationType,
        archive_hash: payload.archiveHash ?? null,
        cost_credits: payload.costCredits ?? 1,
        success: payload.success ?? true,
        ai_tokens_input: payload.aiTokensInput ?? null,
        ai_tokens_output: payload.aiTokensOutput ?? null,
        ai_cost_usd: payload.aiCostUsd ?? null,
      }),
    });
  },
};

export function cabinetUrl(path = "/"): string {
  // В проде это account.optimyzer.pro. В dev — vite сервер на :5173.
  const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
    ?.VITE_CABINET_URL;
  const base = (env && env.replace(/\/+$/, "")) || "http://127.0.0.1:5173";
  return `${base}${path}`;
}

function landingBase(): string {
  // Локальный fallback — landing на :8000 (см. QUICKSTART.md §5).
  // В проде задаётся через VITE_LANDING_URL=https://optimyzer.pro при build.
  const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
    ?.VITE_LANDING_URL;
  return (env && env.replace(/\/+$/, "")) || "http://localhost:8000";
}

export function pricingUrl(): string {
  return `${landingBase()}/#pricing`;
}

/** Ссылка на статью в docs/ лендинга — например docsUrl("/technical/configuring-tj.html"). */
export function docsUrl(path: string): string {
  return `${landingBase()}/docs${path.startsWith("/") ? path : "/" + path}`;
}
