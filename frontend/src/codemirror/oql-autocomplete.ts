import type { Completion, CompletionContext, CompletionResult } from "@codemirror/autocomplete";

const SOURCES: Completion[] = [
  { label: "events", type: "type", detail: "Источник: события ТЖ" },
];

const PIPE_KEYWORDS: Completion[] = [
  { label: "where", type: "keyword" },
  { label: "project", type: "keyword" },
  { label: "order by", type: "keyword" },
  { label: "summarize", type: "keyword" },
  { label: "timerange last", type: "keyword" },
  { label: "limit", type: "keyword" },
  { label: "take", type: "keyword" },
  { label: "render", type: "keyword" },
];

const LOGICAL_KEYWORDS: Completion[] = [
  { label: "and", type: "keyword" },
  { label: "or", type: "keyword" },
  { label: "not", type: "keyword" },
  { label: "in", type: "keyword" },
  { label: "asc", type: "keyword" },
  { label: "desc", type: "keyword" },
  { label: "startswith", type: "keyword" },
  { label: "endswith", type: "keyword" },
  { label: "contains", type: "keyword" },
  { label: "matches", type: "keyword" },
];

const RENDER_TYPES: Completion[] = [
  { label: "table", type: "constant" },
  { label: "bar", type: "constant" },
  { label: "line", type: "constant" },
  { label: "histogram", type: "constant" },
  { label: "timeline", type: "constant" },
  { label: "scatter", type: "constant" },
];

const AGG_FUNCS: Completion[] = [
  { label: "sum(", type: "function", detail: "Сумма" },
  { label: "avg(", type: "function", detail: "Среднее" },
  { label: "min(", type: "function", detail: "Минимум" },
  { label: "max(", type: "function", detail: "Максимум" },
  { label: "count(", type: "function", detail: "Количество" },
  { label: "countd(", type: "function", detail: "Уникальных" },
];

const COLUMNS: Completion[] = [
  { label: "ts", type: "property", detail: "Метка времени" },
  { label: "event_type", type: "property", detail: "Тип события" },
  { label: "level", type: "property", detail: "Уровень" },
  { label: "duration_us", type: "property", detail: "Длительность (мкс)" },
  { label: "duration_ms", type: "property", detail: "Длительность (мс)" },
  { label: "duration", type: "property", detail: "Алиас → duration_us" },
  { label: "session_id", type: "property", detail: "ID сессии" },
  { label: "sid", type: "property", detail: "Алиас → session_id" },
  { label: "user_name", type: "property", detail: "Пользователь" },
  { label: "user", type: "property", detail: "Алиас → user_name" },
  { label: "context", type: "property", detail: "Контекст" },
  { label: "process", type: "property", detail: "Процесс (из event)" },
  { label: "process_role", type: "property", detail: "Роль процесса" },
  { label: "role", type: "property", detail: "Алиас → process_role" },
  { label: "process_pid", type: "property", detail: "PID процесса" },
  { label: "pid", type: "property", detail: "Алиас → process_pid" },
  { label: "sql_text", type: "property", detail: "SQL запрос" },
  { label: "sql", type: "property", detail: "Алиас → sql_text" },
  { label: "sql_text_normalized", type: "property", detail: "Нормализованный SQL" },
  { label: "sql_text_hash", type: "property", detail: "Хэш SQL" },
  { label: "rows_read", type: "property", detail: "Прочитано строк" },
  { label: "rows_modified", type: "property", detail: "Изменено строк" },
];

const ALL_COMPLETIONS: Completion[] = [
  ...SOURCES,
  ...PIPE_KEYWORDS,
  ...LOGICAL_KEYWORDS,
  ...RENDER_TYPES,
  ...AGG_FUNCS,
  ...COLUMNS,
];

const KEYWORD_RE = /[a-zA-Z_][a-zA-Z0-9_]*$/;

export function oqlCompletions(context: CompletionContext): CompletionResult | null {
  const word = context.matchBefore(KEYWORD_RE);
  if (!word || (word.from === word.to && !context.explicit)) return null;

  const before = context.state.doc.sliceString(0, word.from).trimEnd();
  const lastPipe = before.lastIndexOf("|");
  const tailAfterPipe = before.slice(lastPipe + 1).trim().toLowerCase();
  const tokens = tailAfterPipe.split(/\s+/).filter(Boolean);
  const firstAfterPipe = tokens[0] ?? "";

  let options: Completion[] = ALL_COMPLETIONS;

  if (before === "" || before.endsWith("|")) {
    // Start of query или после pipe — приоритет sources/keywords
    options = lastPipe < 0 ? SOURCES : PIPE_KEYWORDS;
  } else if (firstAfterPipe === "where") {
    options = [...COLUMNS, ...LOGICAL_KEYWORDS];
  } else if (firstAfterPipe === "project" || firstAfterPipe === "order") {
    options = COLUMNS;
  } else if (firstAfterPipe === "summarize") {
    options = [...AGG_FUNCS, ...COLUMNS];
  } else if (firstAfterPipe === "render") {
    options = RENDER_TYPES;
  } else {
    options = ALL_COMPLETIONS;
  }

  return {
    from: word.from,
    options,
    validFor: KEYWORD_RE,
  };
}
