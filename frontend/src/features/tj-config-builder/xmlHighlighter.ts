/**
 * XML syntax highlighter + formatter для XmlPreview.
 * Не требует внешних зависимостей — pure TypeScript.
 *
 * Цветовая схема (VS Code Dark+ стиль):
 *   xd  — <?xml …?> объявление             — серый
 *   xc  — <!-- комментарии -->              — зелёный
 *   xb  — < >  угловые скобки и /          — серый
 *   xt  — имя тега                          — оранжевый/янтарный
 *   xk  — имя атрибута                     — светло-голубой
 *   xv  — значение атрибута (с кавычками)  — персиковый
 */

/** HTML-экранирование строки */
function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function span(cls: string, content: string): string {
  return `<span class="${cls}">${content}</span>`;
}

/** Подсвечивает атрибуты внутри открывающего тега */
function colorizeAttrs(attrs: string): string {
  if (!attrs.trim()) return esc(attrs);
  return attrs.replace(
    /([a-zA-Z0-9:_.-]+)(\s*=\s*)("([^"]*)")/g,
    (_, key, eq, val) =>
      span("xk", esc(key)) + esc(eq) + span("xv", esc(val)),
  );
}

/**
 * Возвращает HTML-строку с тегами <span class="x*"> для CSS-подсветки.
 * Безопасен для dangerouslySetInnerHTML — входной XML проходит через esc().
 */
export function highlightXml(xml: string): string {
  const parts: string[] = [];
  let i = 0;

  while (i < xml.length) {
    if (xml[i] !== "<") {
      // Текст между тегами
      const end = xml.indexOf("<", i);
      const text = end === -1 ? xml.slice(i) : xml.slice(i, end);
      parts.push(esc(text));
      i = end === -1 ? xml.length : end;
      continue;
    }

    // Определяем тип токена
    if (xml.startsWith("<?", i)) {
      // XML-декларация <?xml … ?>
      const end = xml.indexOf("?>", i + 2);
      const token = end === -1 ? xml.slice(i) : xml.slice(i, end + 2);
      parts.push(span("xd", esc(token)));
      i = end === -1 ? xml.length : end + 2;
    } else if (xml.startsWith("<!--", i)) {
      // Комментарий
      const end = xml.indexOf("-->", i + 4);
      const token = end === -1 ? xml.slice(i) : xml.slice(i, end + 3);
      parts.push(span("xc", esc(token)));
      i = end === -1 ? xml.length : end + 3;
    } else if (xml.startsWith("</", i)) {
      // Закрывающий тег </tag>
      const end = xml.indexOf(">", i + 2);
      if (end === -1) { parts.push(esc(xml.slice(i))); break; }
      const name = xml.slice(i + 2, end).trim();
      parts.push(
        span("xb", "&lt;/") + span("xt", esc(name)) + span("xb", "&gt;"),
      );
      i = end + 1;
    } else {
      // Открывающий или самозакрывающийся тег
      const end = xml.indexOf(">", i + 1);
      if (end === -1) { parts.push(esc(xml.slice(i))); break; }
      const inner = xml.slice(i + 1, end);
      const selfClose = inner.endsWith("/");
      const content = selfClose ? inner.slice(0, -1) : inner;

      // Разбиваем имя тега и атрибуты
      const nameMatch = content.match(/^([a-zA-Z0-9:_.-]+)([\s\S]*)$/);
      if (!nameMatch) {
        parts.push(esc(xml.slice(i, end + 1)));
        i = end + 1;
        continue;
      }
      const [, tagName, rest] = nameMatch;
      parts.push(
        span("xb", "&lt;") +
          span("xt", esc(tagName)) +
          colorizeAttrs(rest) +
          (selfClose ? span("xb", "/&gt;") : span("xb", "&gt;")),
      );
      i = end + 1;
    }
  }

  return parts.join("");
}

/**
 * Форматирует (prettify) XML-строку с отступами 2 пробела.
 * Работает с well-formed XML. При ошибке возвращает исходник без изменений.
 */
export function prettifyXml(raw: string): string {
  try {
    const INDENT = "  ";
    const tokens = raw.match(
      /(<\?[^?]*\?>)|(<!--[\s\S]*?-->)|(<\/[^>]+>)|(<[^>]+\/>)|(<[^>]+>)|([^<]+)/g,
    );
    if (!tokens) return raw;

    let depth = 0;
    const lines: string[] = [];

    for (const tok of tokens) {
      const t = tok.trim();
      if (!t) continue;

      if (t.startsWith("</")) {
        // Закрывающий тег — уменьшаем отступ перед
        depth = Math.max(0, depth - 1);
        lines.push(INDENT.repeat(depth) + t);
      } else if (t.startsWith("<?") || t.startsWith("<!--")) {
        // Декларация / комментарий
        lines.push(INDENT.repeat(depth) + t);
      } else if (t.endsWith("/>")) {
        // Самозакрывающийся
        lines.push(INDENT.repeat(depth) + t);
      } else if (t.startsWith("<")) {
        // Открывающий тег
        lines.push(INDENT.repeat(depth) + t);
        depth++;
      } else {
        // Текст — добавляем к предыдущей строке (inline content)
        if (lines.length > 0) {
          lines[lines.length - 1] += t;
        }
      }
    }

    return lines.join("\n");
  } catch {
    return raw;
  }
}
