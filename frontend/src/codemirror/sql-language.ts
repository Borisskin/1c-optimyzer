// CodeMirror SQL extension (Sprint 2 Phase B).
// Wrapper над @codemirror/lang-sql с DuckDB-ориентированным dialect и
// schema-based autocomplete (имена таблиц и колонок из бэкенда).
//
// `sqlEditorTheme` повторяет Sprint 1 OQL theme — главное правило
// `"&": { height: "100%" }` зажимает CM editor к высоте родителя,
// без него CM грозит расти по content и толкать layout наружу.

import { EditorView } from "@codemirror/view";
import { sql, SQLDialect } from "@codemirror/lang-sql";
import type { Extension } from "@codemirror/state";

const duckdbDialect = SQLDialect.define({
  keywords:
    "select from where group by having order limit offset join inner left right outer cross on as and or not in like between is null asc desc distinct count sum avg min max with case when then else end union all explain analyze except intersect over partition window unbounded preceding following current row rows range exists",
  builtin:
    "now today date_trunc extract strftime epoch_ms timestamp_diff date_diff length lower upper trim coalesce nullif if greatest least round floor ceil sqrt abs json_extract json_extract_string",
  operatorChars: "+-*/<>!=~|&^%",
  specialVar: "?",
});

export const sqlEditorTheme = EditorView.theme({
  "&": {
    height: "100%",
    fontSize: "13px",
    fontFamily: "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace",
    background: "#FBFBFA",
    color: "#1F2937",
  },
  ".cm-scroller": {
    overflow: "auto",
  },
  ".cm-content": {
    padding: "12px 16px",
    caretColor: "#0F766E",
  },
  ".cm-line": {
    padding: "0 2px",
    lineHeight: "1.6",
  },
  "&.cm-focused": {
    outline: "none",
  },
  ".cm-gutters": {
    background: "#FBFBFA",
    color: "#A3A3A3",
    border: "none",
    borderRight: "1px solid #E5E5E5",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: "12px",
  },
  ".cm-activeLineGutter": {
    color: "#0F766E",
    background: "transparent",
  },
  ".cm-activeLine": {
    background: "rgba(15, 118, 110, 0.04)",
  },
  ".cm-selectionBackground, ::selection": {
    background: "#A7F3D0 !important",
  },
  ".cm-tooltip": {
    background: "#FFFFFF",
    border: "1px solid #E5E5E5",
    borderRadius: "8px",
    fontSize: "12px",
    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
  },
  ".cm-tooltip-autocomplete > ul > li": {
    padding: "4px 10px",
  },
});

export type SchemaShape = Record<string, Array<{ name: string; type: string }>>;

export function makeSqlExtension(schema: SchemaShape = {}): Extension {
  const schemaForCm: Record<string, string[]> = {};
  for (const [table, cols] of Object.entries(schema)) {
    schemaForCm[table] = cols.map((c) => c.name);
  }
  return [
    sql({
      dialect: duckdbDialect,
      schema: schemaForCm,
      upperCaseKeywords: true,
    }),
    sqlEditorTheme,
  ];
}
