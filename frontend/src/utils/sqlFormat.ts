// Простой read-only SQL-форматтер для отображения длинных нормализованных
// T-SQL запросов (Top SQL / Slow Queries). Не парсер — задача только
// разбить простыню на читаемые строки. Применяется к нормализованным
// запросам (с ? вместо литералов), поэтому строковых литералов с пробелами
// внутри не бывает — это упрощает regex.
//
// Правила (порядок важен — длинные ключевые слова матчатся раньше коротких):
// - WITH / SELECT / FROM / WHERE / GROUP BY / HAVING / ORDER BY / LIMIT /
//   UNION (ALL) / INSERT INTO / VALUES / UPDATE / SET / DELETE FROM —
//   перенос на новую строку, отступ = глубина вложенности скобок.
// - JOIN (всех видов) — перенос, отступ + 1.
// - AND / OR — перенос, отступ + 1 (под WHERE / ON).
// - Скобки не разворачиваются автоматически; глубина считается по
//   накопительному количеству "(" минус ")" к началу строки.

const TOP_KEYWORDS = [
  "WITH",
  "SELECT",
  "FROM",
  "WHERE",
  "GROUP BY",
  "HAVING",
  "ORDER BY",
  "LIMIT",
  "OFFSET",
  "UNION ALL",
  "UNION",
  "INSERT INTO",
  "VALUES",
  "UPDATE",
  "SET",
  "DELETE FROM",
];

const JOIN_KEYWORDS = [
  "INNER JOIN",
  "LEFT OUTER JOIN",
  "LEFT JOIN",
  "RIGHT OUTER JOIN",
  "RIGHT JOIN",
  "FULL OUTER JOIN",
  "FULL JOIN",
  "CROSS JOIN",
  "JOIN",
];

const COND_KEYWORDS = ["AND", "OR"];

const INDENT = "  ";

function escapeForRegex(kw: string): string {
  // Все ключевые слова — обычные ASCII буквы и пробелы. Делаем пробел
  // гибким (\s+), чтобы матчить "GROUP  BY" в случае случайных двойных
  // пробелов до нормализации.
  return kw.replace(/ /g, "\\s+");
}

export function formatSql(sql: string): string {
  if (!sql || sql.length === 0) return sql;

  // 1. Нормализуем whitespace в единичные пробелы (нормализованный SQL
  //    уже без переносов, но trim тоже не помешает).
  let s = sql.trim().replace(/\s+/g, " ");

  // 2. Вставляем переносы перед ключевыми словами. Сортировка по длине
  //    убывания — критично: "UNION ALL" должна заматчиться раньше "UNION".
  const topSorted = [...TOP_KEYWORDS].sort((a, b) => b.length - a.length);
  const joinSorted = [...JOIN_KEYWORDS].sort((a, b) => b.length - a.length);
  const condSorted = [...COND_KEYWORDS].sort((a, b) => b.length - a.length);

  for (const kw of topSorted) {
    const re = new RegExp(`\\b${escapeForRegex(kw)}\\b`, "gi");
    s = s.replace(re, `\n${kw}`);
  }
  for (const kw of joinSorted) {
    const re = new RegExp(`\\b${escapeForRegex(kw)}\\b`, "gi");
    // Если уже стоит перенос (после TOP-replacement, например, если JOIN
    // сразу после SELECT) — не дублируем.
    s = s.replace(re, `\n${INDENT}${kw}`);
  }
  for (const kw of condSorted) {
    const re = new RegExp(`\\b${escapeForRegex(kw)}\\b`, "gi");
    s = s.replace(re, `\n${INDENT}${kw}`);
  }

  // 3. Чистим случай когда мы добавили \n в самом начале (для SELECT
  //    например), даём чистую первую строку.
  s = s.replace(/^\s*\n/, "").trimEnd();

  // 4. Считаем глубину скобок построчно и применяем отступ. Дополнительный
  //    отступ для COND/JOIN мы уже добавили выше (INDENT перед KW), поэтому
  //    тут просто прибавляем `depth * INDENT` к началу строки.
  const lines = s.split("\n");
  const out: string[] = [];
  let depth = 0;

  for (const rawLine of lines) {
    const line = rawLine.replace(/\s+$/, "");
    if (line.trim().length === 0) continue;

    // Если строка начинается с ")", уменьшаем depth ДО вычисления отступа
    // — закрывающая скобка должна быть на уровне родителя.
    let lineDepth = depth;
    if (line.trimStart().startsWith(")")) {
      lineDepth = Math.max(0, depth - 1);
    }

    out.push(INDENT.repeat(lineDepth) + line.trimStart());

    // Обновляем общий depth по балансу скобок в этой строке.
    for (const ch of line) {
      if (ch === "(") depth += 1;
      else if (ch === ")") depth = Math.max(0, depth - 1);
    }
  }

  return out.join("\n");
}
