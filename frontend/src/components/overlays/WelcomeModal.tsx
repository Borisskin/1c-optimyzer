import { useEffect, useState } from "react";
import { t } from "@/i18n/ru";

const FIRST_RUN_KEY = "optimyzer.first_run_completed";

interface Props {
  onComplete: () => void;
  onLoadArchive: () => void;
}

/**
 * Welcome modal — показывается один раз при первом запуске.
 * Юзер либо «Начать с примера» (open demo), либо «У меня свой архив»
 * (закрыть модалку, юзер сам нажмёт «Загрузить»).
 */
export function WelcomeModal({ onComplete, onLoadArchive }: Props) {
  function done() {
    try {
      localStorage.setItem(FIRST_RUN_KEY, new Date().toISOString());
    } catch {
      /* ignored */
    }
    onComplete();
  }

  return (
    <div style={backdropStyle}>
      <div style={dialogStyle} role="dialog" aria-modal="true">
        <h2 style={titleStyle}>{t.onboarding.welcomeTitle}</h2>
        <p style={leadStyle}>{t.onboarding.welcomeLead}</p>

        <ul style={listStyle}>
          <li>{t.onboarding.bullets.parse}</li>
          <li>{t.onboarding.bullets.anatomy}</li>
          <li>{t.onboarding.bullets.ai}</li>
        </ul>

        <div style={actionsStyle}>
          <button
            type="button"
            style={primaryBtnStyle}
            onClick={() => {
              done();
              onLoadArchive();
            }}
          >
            {t.onboarding.loadMyArchive}
          </button>
          <button type="button" style={secondaryBtnStyle} onClick={done}>
            {t.onboarding.startWithEmpty}
          </button>
        </div>

        <p style={footnoteStyle}>{t.onboarding.demoArchiveHint}</p>
      </div>
    </div>
  );
}

export function shouldShowWelcomeModal(): boolean {
  try {
    return !localStorage.getItem(FIRST_RUN_KEY);
  } catch {
    return false; // private mode — не доставать
  }
}

/** Хук для App.tsx — единое управление видимостью. */
export function useWelcomeModal(): {
  open: boolean;
  hide: () => void;
} {
  const [open, setOpen] = useState(() => shouldShowWelcomeModal());

  useEffect(() => {
    // если кто-то ещё (тесты / dev tools) выставил флаг — не открываемся
    if (!shouldShowWelcomeModal()) setOpen(false);
  }, []);

  return {
    open,
    hide: () => setOpen(false),
  };
}

// ---------- styles ----------

const backdropStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 27, 45, 0.55)",
  display: "grid",
  placeItems: "center",
  zIndex: 1500,
  backdropFilter: "blur(2px)",
};

const dialogStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 14,
  padding: "28px 32px",
  width: "min(540px, 92vw)",
  boxShadow: "0 24px 60px rgba(0,0,0,0.25)",
};

const titleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 22,
  fontWeight: 700,
  color: "#0f172a",
};

const leadStyle: React.CSSProperties = {
  margin: "12px 0 16px",
  color: "#475569",
  fontSize: 14,
  lineHeight: 1.55,
};

const listStyle: React.CSSProperties = {
  margin: "0 0 20px",
  paddingLeft: 18,
  color: "#0f172a",
  fontSize: 13,
  lineHeight: 1.6,
};

const actionsStyle: React.CSSProperties = {
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
};

const primaryBtnStyle: React.CSSProperties = {
  padding: "10px 18px",
  borderRadius: 8,
  background: "#0ea5a4",
  border: "none",
  color: "#fff",
  fontWeight: 600,
  fontSize: 14,
  cursor: "pointer",
};

const secondaryBtnStyle: React.CSSProperties = {
  padding: "10px 18px",
  borderRadius: 8,
  background: "#fff",
  border: "1px solid #e2e8f0",
  color: "#0f172a",
  fontWeight: 600,
  fontSize: 14,
  cursor: "pointer",
};

const footnoteStyle: React.CSSProperties = {
  margin: "16px 0 0",
  fontSize: 12,
  color: "#64748b",
};
