import { useEffect, useState } from "react";
import { cabinetUrl, cloud, CloudError, pricingUrl } from "@/api/cloud";
import { useAccountStore } from "@/store/accountStore";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import { computeFingerprint, detectDeviceName, detectPlatform } from "@/utils/fingerprint";

interface Props {
  open: boolean;
  reason: "free_limit_exceeded" | "credits_depleted" | "not_authenticated" | string | null;
  onClose: () => void;
  freeQuotaRemaining: number | null;
}

/**
 * Paywall modal. Сценарии:
 *   - not_authenticated → инлайн поле email + кнопка «Привязать».
 *     Server создаёт Free user (или находит существующий) → юзер сразу
 *     получает 5 AI/мес.
 *   - free_limit_exceeded / credits_depleted → CTA «Перейти на Pro» / «Купить
 *     кредиты» через cabinet.
 */
export function PaywallModal({ open, reason, onClose, freeQuotaRemaining }: Props) {
  const activate = useAccountStore((s) => s.activate);
  const pushToast = useAppStore((s) => s.pushToast);

  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) {
      setEmail("");
      setError(null);
    }
  }, [open]);

  if (!open) return null;

  const isNotAuthenticated = reason === "not_authenticated";

  async function submitEmail() {
    const trimmed = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setError(t.paywall.emailInvalid);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const fp = await computeFingerprint();
      const resp = await cloud.lookupByEmail({
        email: trimmed,
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
      pushToast(t.paywall.emailLinked, "ok");
      onClose();
    } catch (err) {
      const ce = err as CloudError;
      setError(
        ce.reason === "conflict"
          ? t.account.errors.deviceLimit
          : ce.reason === "network"
            ? t.account.errors.network
            : ce.message || t.account.errors.generic,
      );
    } finally {
      setBusy(false);
    }
  }

  const title = isNotAuthenticated
    ? t.paywall.titleNotAuthenticated
    : reason === "credits_depleted"
      ? t.paywall.titleCredits
      : t.paywall.titleFree;
  const description = isNotAuthenticated
    ? t.paywall.descriptionNotAuthenticated
    : freeQuotaRemaining === 0
      ? t.paywall.descriptionExhausted
      : t.paywall.descriptionGeneric;

  return (
    <div style={backdropStyle} onClick={onClose}>
      <div
        style={dialogStyle}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={titleStyle}>{title}</h3>
        <p style={descStyle}>{description}</p>

        {isNotAuthenticated ? (
          <div style={emailFormStyle}>
            <input
              type="email"
              style={emailInputStyle}
              placeholder={t.paywall.emailPlaceholder}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={busy}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") void submitEmail();
              }}
            />
            <button
              type="button"
              style={primaryBtnStyle}
              onClick={() => void submitEmail()}
              disabled={busy || !email.trim()}
            >
              {busy ? t.paywall.emailLinking : t.paywall.emailLink}
            </button>
            {error && <div style={errorStyle}>{error}</div>}
            <button type="button" style={linkBtnStyle} onClick={onClose}>
              {t.paywall.dismiss}
            </button>
          </div>
        ) : (
          <div style={actionsStyle}>
            <a
              href={pricingUrl()}
              target="_blank"
              rel="noreferrer noopener"
              style={primaryBtnStyle}
              onClick={onClose}
            >
              {t.paywall.upgrade}
            </a>
            <a
              href={cabinetUrl("/credits")}
              target="_blank"
              rel="noreferrer noopener"
              style={secondaryBtnStyle}
              onClick={onClose}
            >
              {t.paywall.buyCredits}
            </a>
            <button type="button" style={linkBtnStyle} onClick={onClose}>
              {t.paywall.dismiss}
            </button>
          </div>
        )}

        <p style={footnoteStyle}>{t.paywall.footnote}</p>
      </div>
    </div>
  );
}

// ---------- Styles ----------

const backdropStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 27, 45, 0.6)",
  display: "grid",
  placeItems: "center",
  zIndex: 9998,
  padding: 24,
};

const dialogStyle: React.CSSProperties = {
  width: "min(480px, 100%)",
  background: "#fff",
  borderRadius: 12,
  padding: "32px 28px",
  boxShadow: "0 20px 60px rgba(15, 27, 45, 0.3)",
};

const titleStyle: React.CSSProperties = {
  margin: "0 0 12px",
  fontSize: 20,
  fontWeight: 700,
  color: "#0f172a",
};

const descStyle: React.CSSProperties = {
  margin: "0 0 20px",
  color: "#475569",
  fontSize: 14,
  lineHeight: 1.55,
};

const actionsStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 8,
};

const emailFormStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 10,
};

const emailInputStyle: React.CSSProperties = {
  padding: "12px 14px",
  border: "1px solid #cbd5e1",
  borderRadius: 8,
  fontSize: 15,
};

const primaryBtnStyle: React.CSSProperties = {
  display: "block",
  textAlign: "center" as const,
  width: "100%",
  padding: "12px 18px",
  background: "#0ea5a4",
  color: "#fff",
  border: "none",
  borderRadius: 8,
  fontSize: 15,
  fontWeight: 600,
  cursor: "pointer",
  textDecoration: "none",
};

const secondaryBtnStyle: React.CSSProperties = {
  ...primaryBtnStyle,
  background: "#fff",
  color: "#0ea5a4",
  border: "1px solid #99f6e4",
};

const linkBtnStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  background: "transparent",
  border: "none",
  color: "#64748b",
  fontSize: 14,
  cursor: "pointer",
  padding: 8,
};

const errorStyle: React.CSSProperties = {
  padding: "10px 12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: 8,
  color: "#b91c1c",
  fontSize: 13,
};

const footnoteStyle: React.CSSProperties = {
  margin: "20px 0 0",
  fontSize: 12,
  color: "#94a3b8",
  textAlign: "center" as const,
  lineHeight: 1.5,
};
