import { t } from "@/i18n/ru";
import { docsUrl } from "@/api/cloud";

interface Props {
  onLoadArchive: () => void;
}

/**
 * Показывается на главном экране когда никакой архив не загружен.
 *
 * UX (Phase 2.2):
 * - Большая drop-zone иконка
 * - Кнопка «Загрузить архив»
 * - Ссылка «Что такое ТЖ?» — открывает docs
 */
export function EmptyArchiveState({ onLoadArchive }: Props) {
  return (
    <div style={wrapStyle}>
      <div style={cardStyle}>
        <FolderIcon />
        <h2 style={titleStyle}>{t.onboarding.empty.title}</h2>
        <p style={leadStyle}>{t.onboarding.empty.lead}</p>
        <div style={actionsStyle}>
          <button type="button" style={primaryBtnStyle} onClick={onLoadArchive}>
            {t.onboarding.empty.loadBtn}
          </button>
          <a
            href={docsUrl("/technical/configuring-tj.html")}
            target="_blank"
            rel="noreferrer noopener"
            style={secondaryBtnStyle}
          >
            {t.onboarding.empty.whatIsTj}
          </a>
        </div>
        <p style={footnoteStyle}>{t.onboarding.empty.footnote}</p>
      </div>
    </div>
  );
}

function FolderIcon() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#0ea5a4"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ marginBottom: 16 }}
      aria-hidden="true"
    >
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}

const wrapStyle: React.CSSProperties = {
  display: "grid",
  placeItems: "center",
  minHeight: "calc(100vh - 120px)",
  padding: 24,
};

const cardStyle: React.CSSProperties = {
  textAlign: "center",
  maxWidth: 480,
};

const titleStyle: React.CSSProperties = {
  margin: "0 0 8px",
  fontSize: 22,
  fontWeight: 700,
  color: "var(--o-text-1)",
};

const leadStyle: React.CSSProperties = {
  margin: "0 0 20px",
  color: "var(--o-text-2)",
  fontSize: 14,
  lineHeight: 1.55,
};

const actionsStyle: React.CSSProperties = {
  display: "flex",
  gap: 10,
  justifyContent: "center",
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
  border: "1px solid var(--o-border, #e2e8f0)",
  color: "var(--o-text-1, #0f172a)",
  fontWeight: 600,
  fontSize: 14,
  textDecoration: "none",
  display: "inline-flex",
  alignItems: "center",
};

const footnoteStyle: React.CSSProperties = {
  margin: "20px 0 0",
  fontSize: 12,
  color: "var(--o-text-3, #94a3b8)",
};
