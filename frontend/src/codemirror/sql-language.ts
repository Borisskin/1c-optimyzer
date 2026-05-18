// CodeMirror SQL extension (Sprint 2 Phase B).
// Wrapper над @codemirror/lang-sql с DuckDB-ориентированным dialect и
// schema-based autocomplete (имена таблиц и колонок из бэкенда).

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

export type SchemaShape = Record<string, Array<{ name: string; type: string }>>;

export function makeSqlExtension(schema: SchemaShape = {}): Extension {
  const schemaForCm: Record<string, string[]> = {};
  for (const [table, cols] of Object.entries(schema)) {
    schemaForCm[table] = cols.map((c) => c.name);
  }
  return sql({
    dialect: duckdbDialect,
    schema: schemaForCm,
    upperCaseKeywords: true,
  });
}
