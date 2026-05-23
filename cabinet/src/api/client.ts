/**
 * Простой fetch-wrapper для cabinet.
 *
 * Auth: cookie-based (HttpOnly access_token + refresh из /v1/auth/yandex/callback).
 * Cabinet и API на одном домене в проде (account.optimyzer.pro + api.optimyzer.pro
 * с шарингом cookie через CORS credentials).
 */

const API_BASE = (import.meta.env.VITE_API_BASE || "http://127.0.0.1:8001").replace(/\/+$/, "");

export type Method = "GET" | "POST" | "PATCH" | "DELETE";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export async function api<T>(
  path: string,
  init: { method?: Method; body?: unknown } = {},
): Promise<T> {
  const headers: HeadersInit = { accept: "application/json" };
  let body: BodyInit | undefined;
  if (init.body !== undefined) {
    headers["content-type"] = "application/json";
    body = JSON.stringify(init.body);
  }
  const resp = await fetch(`${API_BASE}${path}`, {
    method: init.method || "GET",
    headers,
    body,
    credentials: "include",
  });
  if (!resp.ok) {
    let detail: unknown = null;
    try {
      detail = await resp.json();
    } catch {
      detail = await resp.text();
    }
    const message =
      detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `HTTP ${resp.status}`;
    throw new ApiError(message, resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const apiBase = API_BASE;
