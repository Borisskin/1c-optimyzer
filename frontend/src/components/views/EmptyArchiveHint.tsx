import type { CSSProperties } from "react";
import { Icon } from "@/components/icons/Icon";

interface Props {
  /** Опциональное уточнение: «чтобы увидеть медленные запросы», «чтобы построить heatmap» и т.п. */
  what?: string;
}

/**
 * Стандартный empty state для views, требующих загруженного архива.
 * Раньше во всех экранах был один-в-один захардкоженный текст «Загрузите архив»
 * — он не объяснял КУДА юзеру идти. Теперь — иконка, понятный заголовок и
 * подсказка про конкретные способы загрузки (кнопка в TopBar / drag-n-drop).
 */
export function EmptyArchiveHint({ what }: Props) {
  return (
    <div style={wrapStyle}>
      <div style={iconWrapStyle}>
        <Icon name="Database" size={28} color="var(--o-text-3)" />
      </div>
      <div style={titleStyle}>Архив с логами ТЖ не загружен</div>
      {what && <div style={whatStyle}>{what}</div>}
      <div style={hintStyle}>
        Откройте папку с лог-файлами через кнопку{" "}
        <span style={kbdStyle}>
          <Icon name="Database" size={11} color="var(--o-text-2)" />
          <span>Загрузить папку с логами…</span>
        </span>{" "}
        в верхней панели — или просто перетащите папку в окно.
      </div>
    </div>
  );
}

const wrapStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  textAlign: "center",
  padding: "48px 24px",
  gap: 10,
  color: "var(--o-text-2)",
};

const iconWrapStyle: CSSProperties = {
  width: 56,
  height: 56,
  borderRadius: "50%",
  background: "var(--o-subtle)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  marginBottom: 6,
};

const titleStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: "var(--o-text-1)",
};

const whatStyle: CSSProperties = {
  fontSize: 12,
  color: "var(--o-text-2)",
};

const hintStyle: CSSProperties = {
  fontSize: 12,
  color: "var(--o-text-3)",
  maxWidth: 520,
  lineHeight: 1.55,
};

const kbdStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  padding: "1px 6px",
  margin: "0 2px",
  border: "1px solid var(--o-border-2)",
  borderRadius: 3,
  background: "var(--o-bg)",
  color: "var(--o-text-1)",
  fontSize: 11,
  whiteSpace: "nowrap",
};
