/**
 * useTelemetryFlush — каждые 5 минут (или при unmount) flush'ит буфер на
 * /v1/telemetry/batch. На сетевую ошибку — оставляет буфер как был и
 * пробует через 5 минут снова.
 */

import { useEffect } from "react";
import { useTelemetryStore } from "@/store/telemetryStore";
import { useAccountStore } from "@/store/accountStore";

const FLUSH_PERIOD_MS = 5 * 60 * 1000;

async function flushOnce(token: string | null): Promise<void> {
  const buffer = useTelemetryStore.getState().buffer;
  if (buffer.length === 0) return;
  try {
    const headers: HeadersInit = { "content-type": "application/json" };
    if (token) headers["authorization"] = `Bearer ${token}`;
    const base =
      (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
        ?.VITE_CLOUD_API_BASE || "http://127.0.0.1:8001";
    const resp = await fetch(`${base.replace(/\/+$/, "")}/v1/telemetry/batch`, {
      method: "POST",
      headers,
      body: JSON.stringify({ events: buffer }),
    });
    if (resp.ok) {
      // Очищаем только если backend подтвердил приём.
      useTelemetryStore.getState().clear();
    }
  } catch {
    // Network error — оставим буфер.
  }
}

export function useTelemetryFlush() {
  const accessToken = useAccountStore((s) => s.accessToken);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const tick = () => {
      if (cancelled) return;
      void flushOnce(accessToken);
      timer = setTimeout(tick, FLUSH_PERIOD_MS);
    };

    // Запускаем первый flush через 30 секунд после mount — даём приложению прогреться.
    timer = setTimeout(tick, 30 * 1000);

    // При unmount или закрытии вкладки — попытка финального flush'а.
    const handleBeforeUnload = () => {
      void flushOnce(accessToken);
    };
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [accessToken]);
}
