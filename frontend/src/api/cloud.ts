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
 * В dev задаётся через .env (localhost); по умолчанию — прод, чтобы релизная
 * сборка без переопределения env не уходила на несуществующий localhost.
 */

const DEFAULT_BASE = "https://api.optimyzer.pro";

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
  init: RequestInit & { token?: string; timeoutMs?: number },
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.token) headers.set("authorization", `Bearer ${init.token}`);
  if (init.body) headers.set("content-type", "application/json");

  // Таймаут на запрос. Без него «зависший» сервер (порт открыт, но HTTP не
  // отвечает) даёт бесконечный спиннер в UI. AbortController гарантирует выход.
  // AI-вызовы передают увеличенный timeoutMs (см. методы ниже).
  const timeoutMs = init.timeoutMs ?? 20_000;
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);

  let resp: Response;
  try {
    resp = await fetch(`${baseUrl()}${path}`, { ...init, headers, signal: ac.signal });
  } catch (err) {
    const e = err as Error;
    const isTimeout = e.name === "AbortError";
    // Тех-детали (порт, причина) — только в консоль разработчика, НЕ в UI.
    console.warn(
      `[cloud] ${path}: ${isTimeout ? `таймаут ${timeoutMs} мс` : "ошибка сети — " + e.message}`,
    );
    throw new CloudError("Не удалось связаться с сервером.", 0, "network");
  } finally {
    clearTimeout(timer);
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
    // FastAPI HTTPException(detail={"error": "...", "message": "..."}) — извлекаем
    // human-readable message из вложенного объекта. Иначе на UI вылезает
    // JSON.stringify({error: "ai_not_configured", message: "..."}) → не читаемо.
    let detailStr: string;
    if (typeof detail === "string") {
      detailStr = detail;
    } else if (
      detail &&
      typeof detail === "object" &&
      "message" in detail &&
      typeof (detail as { message: unknown }).message === "string"
    ) {
      detailStr = (detail as { message: string }).message;
    } else if (detail) {
      detailStr = JSON.stringify(detail);
    } else {
      detailStr = `HTTP ${resp.status}`;
    }
    throw new CloudError(detailStr, resp.status, reason, bodyJson);
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

  // Sprint 6 Phase D — AI structured explanation поверх bsl-LS diagnostics.
  // Sprint 6 endpoint работает без auth (localhost dev mode); Phase 1 INFRA
  // позже добавит JWT, caching, multi-model routing.
  async aiExplain(payload: AiExplainRequest, token?: string | null): Promise<AiExplainResponse> {
    return request<AiExplainResponse>("/v1/ai/explain", {
      method: "POST",
      token: token ?? undefined,
      body: JSON.stringify(payload),
      timeoutMs: 90_000, // AI-вызов: сервер сам ограничен 60с на Anthropic + буфер
    });
  },

  // Sprint 7 Phase C — AI structured explanation поверх execution plan.
  async aiExplainPlan(
    payload: AiExplainPlanRequest,
    token?: string | null,
  ): Promise<AiExplainPlanResponse> {
    return request<AiExplainPlanResponse>("/v1/ai/explain_plan", {
      method: "POST",
      token: token ?? undefined,
      body: JSON.stringify(payload),
      timeoutMs: 90_000, // AI-вызов: сервер сам ограничен 60с на Anthropic + буфер
    });
  },

  // Sprint 10 — AI генерация настройки logcfg.xml через Haiku.
  async aiGenerateLogcfg(
    payload: AiLogcfgGenerateRequest,
  ): Promise<AiLogcfgGenerateResponse> {
    return request<AiLogcfgGenerateResponse>("/v1/ai/generate_logcfg", {
      method: "POST",
      body: JSON.stringify(payload),
      timeoutMs: 90_000, // AI-вызов: сервер сам ограничен 60с на Anthropic + буфер
    });
  },

  // Sprint 11 Phase D — Force Refresh status (для UI countdown).
  async aiForceRefreshStatus(cacheKey: string): Promise<ForceRefreshStatus> {
    return request<ForceRefreshStatus>(
      `/v1/ai/force_refresh_status/${encodeURIComponent(cacheKey)}`,
      { method: "GET" },
    );
  },

  // S13 — Remote Config: desktop тянет конфиг при старте + периодически.
  // Публичный endpoint, без авторизации. Короткий таймаут — конфиг не критичен
  // к моменту (при недоступности работаем на последнем известном, см. configStore).
  async getRemoteConfig(): Promise<RemoteConfigPublic> {
    return request<RemoteConfigPublic>("/v1/config", { method: "GET", timeoutMs: 10_000 });
  },
};

// ---------- S13 — Remote Config ----------

export type MonetizationMode = "discovery" | "paid" | "mixed";

export interface RemoteConfigLimits {
  ai_per_day: number | null;
  ai_per_month: number | null;
  per_type: Record<string, number | null>;
}

export interface RemoteConfigPublic {
  monetization_mode: MonetizationMode;
  ai_kill_switch: boolean;
  limits: RemoteConfigLimits;
  /** Тумблеры модулей: tj_analysis / plans / logcfg / regressions / query_analyzer / sql_console */
  feature_flags: Record<string, boolean>;
  config_version: number;
}

// ---------- Sprint 6 — AI types ----------

export interface AiExplainDiagnosticInput {
  code: string;
  message: string;
  severity: "Blocker" | "Critical" | "Major" | "Minor" | "Info";
  range_start_line: number;
  range_start_char: number;
  range_end_line: number;
  range_end_char: number;
  snippet: string;
}

export interface AiExplainConfigContext {
  mdo_types_used?: string[];
  tabular_sections_used?: string[];
  registers_used?: string[];
}

export interface AiExplainRequest {
  query_sdbl: string;
  diagnostics: AiExplainDiagnosticInput[];
  configuration_context?: AiExplainConfigContext;
  related_tj_summary?: string | null;
  /** Sprint 11 — bypass cache lookup. Server применяет rate limiting. */
  force_refresh?: boolean;
}

export interface AiIssueExplanation {
  title: string;
  severity: "Blocker" | "Critical" | "Major" | "Minor" | "Info";
  what: string;
  why: string;
  what_to_do: string;
  linked_diagnostic_codes: string[];
}

export interface AiSuggestedRewrite {
  available: boolean;
  sdbl?: string | null;
  reasoning?: string | null;
}

export interface AiExplainResponse {
  explanation_summary: string;
  issues: AiIssueExplanation[];
  suggested_rewrite: AiSuggestedRewrite;
  model_used: string;
  duration_ms: number;
  /** Sprint 11 — cache metadata. */
  was_cached?: boolean;
  cache_age_seconds?: number | null;
  cache_key?: string | null;
}

// ---------- Sprint 7 — Plan Analyzer AI types ----------

export type PlanSeverity = "Info" | "Warning" | "Critical";

export interface AiExplainPlanRequest {
  sql_text: string;
  // План в одном из трёх форматов: XML (.sqlplan от SSMS), text (SHOWPLAN_TEXT
  // от 1С MSSQL или EXPLAIN ANALYZE от 1С PG) или JSON (EXPLAIN FORMAT JSON от PG).
  // Поле называется plan_xml для backward-compat — сервер смотрит на plan_format
  // чтобы понять как интерпретировать. См. Sprint 7 ADR-038, Sprint 8 Phase B.
  plan_xml: string;
  /** "xml" — SSMS .sqlplan (MSSQL), "text" — TEXT (MSSQL или PG), "json" — PG FORMAT JSON. */
  plan_format?: "xml" | "text" | "json";
  /**
   * Sprint 8 Phase B — движок СУБД источника плана. Сервер использует это
   * для выбора правильного AI prompt: "mssql" → MSSQL терминология (Clustered
   * Index Seek, Hash Match...), "postgres" → PG терминология (Seq Scan,
   * Memoize...) + 1С-specific знание (enable_mergejoin=off, mchar/mvarchar, ...).
   * Default "mssql" для backward-compat с Sprint 7 clients.
   */
  engine?: "mssql" | "postgres";
  planview_warnings: unknown[];
  missing_indexes: unknown[];
  plan_summary?: Record<string, unknown> | null;
  configuration_context?: AiExplainConfigContext;
  related_tj_summary?: string | null;
  /**
   * Sprint 8 Phase C — антипаттерны, обнаруженные локально через sqlglot
   * engine (backend.sqlAntipatternsDetect). Передаются AI как контекст —
   * AI расширяет их конкретикой плана, не дублирует в hotspots.
   */
  detected_antipatterns?: Record<string, unknown>[];
  /** Sprint 11 — bypass cache lookup. */
  force_refresh?: boolean;
}

export interface AiPlanHotspot {
  operator_node_id?: number | null;
  operator_type: string;
  severity: PlanSeverity;
  what: string;
  why: string;
  what_to_do: string;
}

export interface AiPlanRecommendation {
  category: "index" | "query_rewrite" | "config" | "stats";
  title: string;
  description: string;
  impact_estimate: "Critical" | "High" | "Medium" | "Low";
}

export interface AiPlanSuggestedIndex {
  table: string;
  columns: string[];
  include: string[];
  rationale: string;
  impact_estimate: "Critical" | "High" | "Medium" | "Low";
}

export interface AiExplainPlanResponse {
  summary: string;
  overall_severity: PlanSeverity;
  hotspots: AiPlanHotspot[];
  recommendations: AiPlanRecommendation[];
  suggested_indexes: AiPlanSuggestedIndex[];
  model_used: string;
  duration_ms: number;
  plan_truncated: boolean;
  /** Sprint 11 — cache metadata. */
  was_cached?: boolean;
  cache_age_seconds?: number | null;
  cache_key?: string | null;
}

// ---------- Sprint 10 — TJ Config Builder AI types ----------

export interface AiLogcfgGenerateRequest {
  problem_description: string;
  platform_version?: string | null;
  dbms?: "mssql" | "postgres" | "both" | "unknown";
  /** Sprint 11 — bypass cache lookup. */
  force_refresh?: boolean;
}

export interface AiLogcfgEventConfig {
  enabled: boolean;
  threshold_cs?: number | null;
}

export interface AiLogcfgConfigResult {
  events: Record<string, AiLogcfgEventConfig>;
  capture_plans: boolean;
  log_directory: string;
  history_hours: number;
}

export interface AiLogcfgEventRationale {
  event: string;
  threshold: string;
  why: string;
}

export interface AiLogcfgGenerateResponse {
  config: AiLogcfgConfigResult;
  explanation: string;
  events_rationale: AiLogcfgEventRationale[];
  estimated_use_duration: string;
  warnings: string[];
  model_used: string;
  duration_ms: number;
  /** Sprint 11 — cache metadata. */
  was_cached?: boolean;
  cache_age_seconds?: number | null;
  cache_key?: string | null;
}

/** Sprint 11 Phase D — Force Refresh status response. */
export interface ForceRefreshStatus {
  allowed: boolean;
  per_item_remaining_seconds: number;
  per_session_used: number;
  per_session_limit: number;
  per_session_remaining_seconds: number;
}

export function cabinetUrl(path = "/"): string {
  // В проде это account.optimyzer.pro. В dev — vite сервер на :5173.
  const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
    ?.VITE_CABINET_URL;
  const base = (env && env.replace(/\/+$/, "")) || "https://account.optimyzer.pro";
  return `${base}${path}`;
}

function landingBase(): string {
  // Локальный fallback — landing на :8000 (см. QUICKSTART.md §5).
  // В проде задаётся через VITE_LANDING_URL=https://optimyzer.pro при build.
  const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
    ?.VITE_LANDING_URL;
  return (env && env.replace(/\/+$/, "")) || "https://optimyzer.pro";
}

export function pricingUrl(): string {
  return `${landingBase()}/#pricing`;
}

/** Ссылка на статью в docs/ лендинга — например docsUrl("/technical/configuring-tj.html"). */
export function docsUrl(path: string): string {
  return `${landingBase()}/docs${path.startsWith("/") ? path : "/" + path}`;
}
