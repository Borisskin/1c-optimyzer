/**
 * OpaqueSqlHint — маленький pill «параметры скрыты» рядом с SQL запросом,
 * который платформа 1С записала в ТЖ как непрозрачную обёртку
 * (`{call sp_executesql(?, ?, ?)}` без значений). Клик → docs про logcfg.xml.
 */

import type { CSSProperties } from "react";

const DOCS_URL = "https://optimyzer.pro/docs/technical/configuring-tj.html";

export function OpaqueSqlHint() {
  return (
    <a
      href={DOCS_URL}
      target="_blank"
      rel="noreferrer noopener"
      title="Параметры запроса не записаны в ТЖ платформой 1С (JDBC PreparedStatement). Кликни — как настроить logcfg.xml."
      style={pillStyle}
      onClick={(e) => e.stopPropagation()}
    >
      <span style={dotStyle} />
      параметры скрыты
    </a>
  );
}

const pillStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  marginLeft: 8,
  padding: "1px 7px 1px 5px",
  fontSize: 10.5,
  fontWeight: 500,
  background: "#fef3c7",
  color: "#92400e",
  border: "1px solid #fde68a",
  borderRadius: 999,
  textDecoration: "none",
  whiteSpace: "nowrap",
  cursor: "help",
  verticalAlign: "middle",
};

const dotStyle: CSSProperties = {
  display: "inline-block",
  width: 5,
  height: 5,
  borderRadius: "50%",
  background: "#d97706",
};
