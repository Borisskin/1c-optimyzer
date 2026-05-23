/**
 * LoginGate — full-screen блокировка приложения пока юзер не активирован.
 *
 * Показывается в App.tsx когда `accountStore.accessToken === null`.
 * Полностью блокирует анализ архивов, переключение экранов и любые
 * другие действия — решение Сергея 23.05.2026 (mandatory login для
 * учёта AI-генераций на стороне cloud).
 *
 * UX:
 *   1. PulseLogo + welcome text
 *   2. Primary кнопка «Войти через Yandex» → открывает cabinet/login?from=desktop
 *      в system browser (через @tauri-apps/plugin-shell.open)
 *   3. Fallback expander «Уже есть ключ?» → поле ввода + кнопка «Активировать»
 *
 * После активации (либо через deep link от cabinet → ловит Tauri →
 * accountStore.activate(), либо через ручной ввод ключа здесь) — LoginGate
 * исчезает, юзер видит обычный UI.
 */

import { useState } from "react";
import { useAccountStore } from "@/store/accountStore";
import { useAppStore } from "@/store/appStore";
import { cabinetUrl, cloud, CloudError } from "@/api/cloud";
import { t } from "@/i18n/ru";
import { computeFingerprint, detectDeviceName, detectPlatform } from "@/utils/fingerprint";
import { PulseLogo } from "@/components/icons/PulseLogo";

export function LoginGate() {
  const activate = useAccountStore((s) => s.activate);
  const pushToast = useAppStore((s) => s.pushToast);

  const [keyOpen, setKeyOpen] = useState(false);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openCabinetLogin() {
    // Tauri webview позволяет window.open(url, '_blank') открывать в system browser.
    // Если в будущем потребуется явный API — добавим @tauri-apps/plugin-shell
    // (требует Rust rebuild + permissions в tauri.conf.json).
    window.open(cabinetUrl("/login?from=desktop"), "_blank", "noreferrer");
  }

  async function submitKey() {
    if (!key.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const fp = await computeFingerprint();
      const resp = await cloud.activate({
        key: key.trim(),
        fingerprint: fp,
        deviceName: detectDeviceName(),
        platform: detectPlatform(),
        appVersion: t.app.version,
      });
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
      pushToast(t.loginGate.activatedToast, "ok");
    } catch (err) {
      const ce = err as CloudError;
      setError(
        ce.reason === "not_found"
          ? t.account.errors.keyNotFound
          : ce.reason === "conflict"
            ? t.account.errors.deviceLimit
            : ce.reason === "network"
              ? t.account.errors.network
              : ce.message || t.account.errors.generic,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={backdropStyle}>
      <div style={cardStyle}>
        <PulseLogo size={64} style={{ marginBottom: 16 }} />
        <h1 style={titleStyle}>Optimyzer</h1>
        <p style={leadStyle}>{t.loginGate.lead}</p>

        <button type="button" style={primaryBtnStyle} onClick={openCabinetLogin}>
          {t.loginGate.signInYandex}
        </button>

        <div style={separatorStyle}>
          <span>{t.loginGate.separator}</span>
        </div>

        {!keyOpen ? (
          <button
            type="button"
            style={linkBtnStyle}
            onClick={() => setKeyOpen(true)}
          >
            {t.loginGate.alreadyHaveKey}
          </button>
        ) : (
          <div style={keySectionStyle}>
            <input
              type="text"
              style={keyInputStyle}
              placeholder="OPTM-XXXX-XXXX-XXXX-XXXX"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              disabled={busy}
              autoComplete="off"
              spellCheck={false}
            />
            <button
              type="button"
              style={activateBtnStyle}
              onClick={submitKey}
              disabled={busy || key.trim().length < 10}
            >
              {busy ? t.account.activating : t.account.activate}
            </button>
          </div>
        )}

        {error && <div style={errorStyle}>{error}</div>}

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
};

const cardStyle: React.CSSProperties = {
  width: "min(440px, 100%)",
  background: "#ffffff",
  borderRadius: 16,
  padding: "40px 36px",
  boxShadow: "0 20px 60px rgba(15, 27, 45, 0.15)",
  textAlign: "center",
};

const titleStyle: React.CSSProperties = {
  margin: "0 0 8px",
  fontSize: 28,
  fontWeight: 700,
  color: "#0f172a",
};

const leadStyle: React.CSSProperties = {
  margin: "0 0 24px",
  color: "#475569",
  fontSize: 14,
  lineHeight: 1.55,
};

const primaryBtnStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "12px 20px",
  background: "#ffdb4d",
  color: "#000",
  border: "none",
  borderRadius: 8,
  fontSize: 15,
  fontWeight: 700,
  cursor: "pointer",
};

const separatorStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  margin: "20px 0",
  color: "#94a3b8",
  fontSize: 12,
};

const linkBtnStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  background: "transparent",
  border: "none",
  color: "#0ea5a4",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
  padding: 8,
};

const keySectionStyle: React.CSSProperties = {
  display: "flex",
  gap: 8,
};

const keyInputStyle: React.CSSProperties = {
  flex: 1,
  padding: "10px 12px",
  border: "1px solid #cbd5e1",
  borderRadius: 8,
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: 13,
  letterSpacing: "0.04em",
};

const activateBtnStyle: React.CSSProperties = {
  padding: "10px 16px",
  background: "#0ea5a4",
  color: "#fff",
  border: "none",
  borderRadius: 8,
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

const errorStyle: React.CSSProperties = {
  marginTop: 12,
  padding: "8px 12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: 8,
  color: "#b91c1c",
  fontSize: 13,
  textAlign: "left",
};

const footnoteStyle: React.CSSProperties = {
  margin: "24px 0 0",
  fontSize: 12,
  color: "#94a3b8",
  lineHeight: 1.5,
};
