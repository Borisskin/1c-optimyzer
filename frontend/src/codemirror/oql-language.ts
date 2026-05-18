import { StreamLanguage, type StreamParser, LanguageSupport, HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { tags as t } from "@lezer/highlight";

const KEYWORDS = new Set([
  "where",
  "project",
  "order",
  "by",
  "summarize",
  "timerange",
  "last",
  "limit",
  "take",
  "render",
  "and",
  "or",
  "not",
  "in",
  "asc",
  "desc",
  "startswith",
  "endswith",
  "contains",
  "matches",
]);

const RENDER_TYPES = new Set(["table", "bar", "line", "histogram", "timeline", "scatter"]);
const AGG_FUNCS = new Set(["sum", "avg", "min", "max", "count", "countd"]);
const SOURCES = new Set(["events"]);
const DURATION_UNITS = new Set(["us", "ms", "s", "m", "h", "d"]);

interface State {
  inString: boolean;
  stringQuote: string;
}

const oqlParser: StreamParser<State> = {
  startState: () => ({ inString: false, stringQuote: '"' }),
  token(stream, state): string | null {
    if (state.inString) {
      while (!stream.eol()) {
        const ch = stream.next();
        if (ch === "\\" && !stream.eol()) {
          stream.next();
          continue;
        }
        if (ch === state.stringQuote) {
          state.inString = false;
          return "string";
        }
      }
      return "string";
    }

    if (stream.match("//")) {
      stream.skipToEnd();
      return "comment";
    }

    if (stream.eatSpace()) return null;

    const ch = stream.peek();
    if (ch === '"' || ch === "'") {
      state.inString = true;
      state.stringQuote = ch!;
      stream.next();
      return "string";
    }

    if (stream.match(/^-?\d+(\.\d+)?/)) {
      // duration suffix
      const restMatch = stream.match(/^[a-zA-Zµ]+/, false) as RegExpMatchArray | null;
      if (restMatch && DURATION_UNITS.has(restMatch[0])) {
        stream.match(/^[a-zA-Zµ]+/);
        return "number";
      }
      return "number";
    }

    if (stream.match(/^\|/)) return "operator";
    if (stream.match(/^(==|!=|<=|>=|<|>)/)) return "operator";
    if (stream.match(/^=/)) return "operator";

    const wordMatch = stream.match(/^[A-Za-zА-Яа-яёЁ_][A-Za-z0-9А-Яа-яёЁ_:]*/) as RegExpMatchArray | null;
    if (wordMatch) {
      const word = wordMatch[0].toLowerCase();
      if (KEYWORDS.has(word)) return "keyword";
      if (RENDER_TYPES.has(word)) return "atom";
      if (AGG_FUNCS.has(word)) return "function";
      if (SOURCES.has(word)) return "typeName";
      return "variable";
    }

    stream.next();
    return null;
  },
  languageData: {
    commentTokens: { line: "//" },
  },
};

export const oqlStreamLanguage = StreamLanguage.define(oqlParser);

// Цветовая схема ровно по дизайну optimyzerql.jsx.
export const oqlHighlightStyle = HighlightStyle.define([
  { tag: t.comment, color: "#737373" },
  { tag: t.keyword, color: "#0F766E", fontWeight: "bold" },
  { tag: t.typeName, color: "#0F766E", fontWeight: "bold" },
  { tag: t.atom, color: "#A855F7" },
  { tag: t.function(t.variableName), color: "#2563EB" },
  { tag: t.string, color: "#16A34A" },
  { tag: t.number, color: "#D97706" },
  { tag: t.operator, color: "#A3A3A3" },
  { tag: t.variableName, color: "#1F2937" },
]);

export const oqlLanguage = new LanguageSupport(oqlStreamLanguage, [syntaxHighlighting(oqlHighlightStyle)]);
