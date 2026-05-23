/**
 * LoginGate — full-screen блокировка приложения пока юзер не активирован.
 *
 * Device flow (как Apple TV / GitHub CLI):
 *   1. Юзер кликает «Войти через Yandex»
 *   2. Desktop POST'ит cloud.desktopInit → получает session_id + cabinet_url
 *   3. Открывается system browser на cabinet/desktop-activate?session=...
 *   4. Юзер логинится через Yandex в browser
 *   5. Cabinet auto-confirms сессию через /v1/license/desktop-confirm
 *   6. Desktop polling'ом (раз в 2 сек) ждёт status=confirmed
 *   7. Как только получил access_token — accountStore.activate() → LoginGate уходит
 *
 * Без ключей активации и копи-паста.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useAccountStore } from "@/store/accountStore";
import { cloud, CloudError } from "@/api/cloud";
import { t } from "@/i18n/ru";
import { computeFingerprint, detectDeviceName, detectPlatform } from "@/utils/fingerprint";
import { PulseLogo } from "@/components/icons/PulseLogo";

type Phase = "idle" | "initiating" | "waiting" | "error";

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 10 * 60 * 1000; // 10 минут

export function LoginGate() {
  const activate = useAccountStore((s) => s.activate);

  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const sessionRef = useRef<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const startedAtRef = useRef<number>(0);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const pollOnce = useCallback(async () => {
    const sessionId = sessionRef.current;
    if (!sessionId) return;

    if (Date.now() - startedAtRef.current > POLL_TIMEOUT_MS) {
      stopPolling();
      setPhase("error");
      setError(t.loginGate.errors.timeout);
      return;
    }

    try {
      const resp = await cloud.desktopPoll(sessionId);
      if (resp.status === "confirmed" && resp.access_token && resp.user && resp.device && resp.subscription) {
        stopPolling();
        activate({
          accessToken: resp.access_token,
          deviceId: resp.device.id,
          profile: {
            userId: resp.user.id,
            email: resp.user.email,
            displayName: resp.user.display_name,
          },
          subscription: {
            plan: resp.subscription.plan,
            endsAt: resp.subscription.ends_at,
            proActive: resp.subscription.pro_active,
          },
        });
        return;
      }
      if (resp.status === "expired" || resp.status === "cancelled") {
        stopPolling();
        setPhase("error");
        setError(
          resp.status === "expired"
            ? t.loginGate.errors.timeout
            : t.loginGate.errors.cancelled,
        );
        return;
      }
      // pending — продолжаем ждать
      pollTimerRef.current = setTimeout(pollOnce, POLL_INTERVAL_MS);
    } catch (err) {
      // Сетевая ошибка — ретраим
      console.warn("Desktop poll failed:", (err as CloudError).message);
      pollTimerRef.current = setTimeout(pollOnce, POLL_INTERVAL_MS);
    }
  }, [activate, stopPolling]);

  const startLogin = useCallback(async () => {
    setPhase("initiating");
    setError(null);
    try {
      const fp = await computeFingerprint();
      const init = await cloud.desktopInit({
        fingerprint: fp,
        deviceName: detectDeviceName(),
        platform: detectPlatform(),
        appVersion: t.app.version,
      });
      sessionRef.current = init.session_id;
      startedAtRef.current = Date.now();
      // Открываем system browser на cabinet
      window.open(init.cabinet_url, "_blank", "noreferrer");
      setPhase("waiting");
      // Стартуем polling через секунду — даём browser открыться
      pollTimerRef.current = setTimeout(pollOnce, 1000);
    } catch (err) {
      setPhase("error");
      setError((err as CloudError).message || t.loginGate.errors.network);
    }
  }, [pollOnce]);

  const cancelWaiting = useCallback(() => {
    stopPolling();
    sessionRef.current = null;
    setPhase("idle");
    setError(null);
  }, [stopPolling]);

  return (
    <div style={backdropStyle}>
      <div style={cardStyle}>
        <PulseLogo size={72} style={{ marginBottom: 20 }} />
        <h1 style={titleStyle}>Optimyzer</h1>
        <p style={leadStyle}>{t.loginGate.lead}</p>

        {phase === "idle" && (
          <button type="button" style={primaryBtnStyle} onClick={startLogin}>
            {t.loginGate.signInYandex}
          </button>
        )}

        {phase === "initiating" && (
          <button type="button" style={primaryBtnStyle} disabled>
            {t.loginGate.initiating}
          </button>
        )}

        {phase === "waiting" && (
          <>
            <div style={waitingBoxStyle}>
              <div style={spinnerStyle} />
              <p style={{ margin: 0, fontSize: 14, color: "var(--o-text-2, #475569)" }}>
                {t.loginGate.waiting}
              </p>
            </div>
            <button type="button" style={linkBtnStyle} onClick={cancelWaiting}>
              {t.loginGate.cancel}
            </button>
          </>
        )}

        {phase === "error" && (
          <>
            <div style={errorStyle}>{error}</div>
            <button type="button" style={primaryBtnStyle} onClick={startLogin}>
              {t.loginGate.retry}
            </button>
          </>
        )}

        <p style={footnoteStyle}>{t.loginGate.footnote}</p>
      </div>
    </div>
  );
}

// ---------- Styles ----------

const backdropStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "linear-gradient(180deg, #ffffff 0%, #f0fdfa 100%)",
  display: "grid",
  placeItems: "center",
  zIndex: 9999,
  padding: 24,
  fontFamily: '"Manrope", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
};

const cardStyle: React.CSSProperties = {
  width: "min(480px, 100%)",
  background: "#ffffff",
  borderRadius: 16,
  padding: "48px 40px",
  boxShadow: "0 20px 60px rgba(15, 27, 45, 0.15)",
  textAlign: "center",
};

const titleStyle: React.CSSProperties = {
  margin: "0 0 12px",
  fontSize: 32,
  fontWeight: 800,
  color: "#0f172a",
  letterSpacing: "-0.02em",
};

const leadStyle: React.CSSProperties = {
  margin: "0 0 28px",
  color: "#475569",
  fontSize: 15,
  lineHeight: 1.55,
};

const primaryBtnStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "14px 20px",
  background: "#ffdb4d",
  color: "#000",
  border: "none",
  borderRadius: 8,
  fontSize: 16,
  fontWeight: 700,
  cursor: "pointer",
};

const linkBtnStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  background: "transparent",
  border: "none",
  color: "#64748b",
  fontSize: 14,
  fontWeight: 500,
  cursor: "pointer",
  padding: 8,
  marginTop: 8,
};

const waitingBoxStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 12,
  padding: "16px 18px",
  background: "#f0fdfa",
  borderRadius: 8,
  border: "1px solid #99f6e4",
};

const spinnerStyle: React.CSSProperties = {
  width: 20,
  height: 20,
  border: "3px solid #99f6e4",
  borderTopColor: "#0ea5a4",
  borderRadius: "50%",
  animation: "spin 0.8s linear infinite",
};

const errorStyle: React.CSSProperties = {
  marginBottom: 16,
  padding: "12px 16px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: 8,
  color: "#b91c1c",
  fontSize: 14,
  textAlign: "left",
};

const footnoteStyle: React.CSSProperties = {
  margin: "28px 0 0",
  fontSize: 12,
  color: "#94a3b8",
  lineHeight: 1.5,
};

// Inject keyframes для спиннера один раз
if (typeof document !== "undefined" && !document.getElementById("loginGateSpinKeyframes")) {
  const style = document.createElement("style");
  style.id = "loginGateSpinKeyframes";
  style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
  document.head.appendChild(style);
}
