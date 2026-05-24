/**
 * useHeartbeat — стучимся в /v1/license/heartbeat для синхронизации подписки
 * и квоты с сервером.
 *
 * Сервер = source of truth. Локальный store отражает то что сервер вернул.
 *
 * Когда вызывается:
 *   • при mount компонента (App), если есть token
 *   • каждые HEARTBEAT_PERIOD_MS
 *   • явно через useAccountStore.getState() ... — после critical events
 *     (после AI consultation, после открытия Settings/Аккаунт)
 *
 * Если token невалиден (401/404) — локально signOut, юзер видит paywall.
 * Сетевая ошибка — просто retry через RETRY_MS, без degraded-режима
 * (он создавал больше проблем чем решал; всё равно при следующем запросе
 * к серверу мы получим правду).
 */

import { useCallback, useEffect, useRef } from "react";
import { cloud, CloudError } from "@/api/cloud";
import { useAccountStore } from "@/store/accountStore";
import { t } from "@/i18n/ru";

const HEARTBEAT_PERIOD_MS = 5 * 60 * 1000; // 5 минут
const RETRY_MS = 60 * 1000; // если ошибка — через минуту повтор

/**
 * Прямой вызов heartbeat — не привязан к компоненту. Используется,
 * например, после trackUsage чтобы немедленно синхронизировать счётчик.
 */
export async function triggerHeartbeat(): Promise<void> {
  const state = useAccountStore.getState();
  if (!state.accessToken) return;
  try {
    const resp = await cloud.heartbeat(state.accessToken, t.app.version);
    useAccountStore.getState().applyHeartbeat({
      plan: resp.subscription_plan,
      endsAt: resp.subscription_ends_at,
      aiQuotaRemaining: resp.ai_quota_remaining,
      creditsRemaining: resp.credits_remaining,
    });
  } catch (err) {
    const ce = err as CloudError;
    if (ce.reason === "unauthorized" || ce.reason === "not_found") {
      useAccountStore.getState().signOut();
    }
    // Сетевая ошибка — просто игнорируем, следующий heartbeat подхватит.
  }
}

export function useHeartbeat() {
  const accessToken = useAccountStore((s) => s.accessToken);
  const lastTokenRef = useRef<string | null>(null);

  const tick = useCallback(async () => {
    await triggerHeartbeat();
  }, []);

  useEffect(() => {
    if (!accessToken) {
      lastTokenRef.current = null;
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function scheduleNext(delay: number) {
      timer = setTimeout(async () => {
        if (cancelled) return;
        await tick();
        if (!cancelled) scheduleNext(HEARTBEAT_PERIOD_MS);
      }, delay);
    }

    // Сразу при mount/token-change — если давно не было heartbeat.
    const lastAt = useAccountStore.getState().cache.lastHeartbeatAt;
    const fresh = lastAt && Date.now() - new Date(lastAt).getTime() < 60 * 1000; // меньше минуты
    if (!fresh) {
      void tick();
    }
    scheduleNext(HEARTBEAT_PERIOD_MS);

    lastTokenRef.current = accessToken;
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [accessToken, tick]);
}
