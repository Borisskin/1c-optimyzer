/**
 * useHeartbeat — каждый раз когда юзер открывает приложение, и далее раз в 24 часа,
 * стучимся в /v1/license/heartbeat для синхронизации подписки.
 *
 * Если не получается > MAX_OFFLINE_DAYS — accountStore.setOfflineDegradation()
 * downgrade'ит юзера в Free режим (без полного блокирования — analyze всё равно работает).
 */

import { useEffect, useRef } from "react";
import { cloud, CloudError } from "@/api/cloud";
import { useAccountStore } from "@/store/accountStore";
import { t } from "@/i18n/ru";

const PERIOD_MS = 24 * 3600 * 1000;
const RETRY_MS = 60 * 60 * 1000; // если ошибка — через час повтор

export function useHeartbeat() {
  const accessToken = useAccountStore((s) => s.accessToken);
  const applyHeartbeat = useAccountStore((s) => s.applyHeartbeat);
  const setOfflineDegradation = useAccountStore((s) => s.setOfflineDegradation);
  const signOut = useAccountStore((s) => s.signOut);
  const lastTokenRef = useRef<string | null>(null);

  useEffect(() => {
    if (!accessToken) {
      lastTokenRef.current = null;
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function tick() {
      try {
        const resp = await cloud.heartbeat(accessToken!, t.app.version);
        if (cancelled) return;
        applyHeartbeat({
          plan: resp.subscription_plan,
          endsAt: resp.subscription_ends_at,
          aiQuotaRemaining: resp.ai_quota_remaining,
          creditsRemaining: resp.credits_remaining,
        });
        timer = setTimeout(tick, PERIOD_MS);
      } catch (err) {
        const ce = err as CloudError;
        if (ce.reason === "unauthorized" || ce.reason === "not_found") {
          // Токен невалидный — выкидываем юзера локально.
          signOut();
          return;
        }
        // Сетевая ошибка — degrade если давно не было успешного heartbeat
        if (useAccountStore.getState().isOfflineTooLong()) {
          setOfflineDegradation();
        }
        timer = setTimeout(tick, RETRY_MS);
      }
    }

    // Не дёргаем повторно если только что был успешный heartbeat (<5 минут назад).
    const lastAt = useAccountStore.getState().cache.lastHeartbeatAt;
    const fresh = lastAt && Date.now() - new Date(lastAt).getTime() < 5 * 60 * 1000;
    if (!fresh) {
      void tick();
    } else {
      timer = setTimeout(tick, PERIOD_MS);
    }

    lastTokenRef.current = accessToken;
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [accessToken, applyHeartbeat, setOfflineDegradation, signOut]);
}
