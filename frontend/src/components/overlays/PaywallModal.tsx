import { useEffect } from "react";
import { cabinetUrl, pricingUrl } from "@/api/cloud";
import { t } from "@/i18n/ru";

interface Props {
  open: boolean;
  reason: "free_limit_exceeded" | "credits_depleted" | string | null;
  onClose: () => void;
  freeQuotaRemaining: number | null;
}

/**
 * Paywall modal — показывается когда soft cap не разрешил AI-операцию.
 * Юзер выбирает: купить Pro / купить кредиты / закрыть.
 */
export function PaywallModal({ open, reason, onClose, freeQuotaRemaining }: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const title =
    reason === "credits_depleted" ? t.paywall.titleCredits : t.paywall.titleFree;
  const description =
    freeQuotaRemaining === 0
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

        <p style={footnoteStyle}>{t.paywall.footnote}</p>
      </div>
    </div>
  );
}

const backdropStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 27, 45, 0.55)",
  backdropFilter: "blur(2px)",
  display: "grid",
  placeItems: "center",
  zIndex: 1000,
};

const dialogStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 12,
  padding: "24px 28px",
  width: "min(440px, 90vw)",
  boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
};

const titleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 18,
  fontWeight: 700,
  color: "#0f172a",
};

const descStyle: React.CSSProperties = {
  margin: "12px 0 20px",
  color: "#475569",
  fontSize: 14,
  lineHeight: 1.55,
};

const actionsStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 8,
};

const primaryBtnStyle: React.CSSProperties = {
  padding: "10px 16px",
  borderRadius: 8,
  background: "#0ea5a4",
  color: "#fff",
  fontWeight: 600,
  fontSize: 14,
  textAlign: "center",
  textDecoration: "none",
  border: "none",
  cursor: "pointer",
};

const secondaryBtnStyle: React.CSSProperties = {
  padding: "10px 16px",
  borderRadius: 8,
  background: "#fff",
  color: "#0f172a",
  fontWeight: 600,
  fontSize: 14,
  textAlign: "center",
  textDecoration: "none",
  border: "1px solid #e2e8f0",
  cursor: "pointer",
};

const linkBtnStyle: React.CSSProperties = {
  padding: "8px 16px",
  background: "transparent",
  color: "#64748b",
  fontSize: 13,
  border: "none",
  cursor: "pointer",
};

const footnoteStyle: React.CSSProperties = {
  margin: "16px 0 0",
  fontSize: 12,
  color: "#94a3b8",
};
