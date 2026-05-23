/**
 * Детектор «непрозрачных» SQL-обёрток — когда платформа 1С пишет в ТЖ
 * `{call sp_executesql(?, ?, ?)}` или `exec sp_executesql ?, ?` без
 * реальных значений параметров.
 *
 * Это типично для JDBC PreparedStatement: значения биндятся отдельно через
 * setObject() и в логах ТЖ не появляются. Можно починить только настройкой
 * `logcfg.xml` — см. landing/docs/technical/configuring-tj.html.
 *
 * Логика: после удаления служебных токенов (sp_executesql, {call, exec, etc),
 * пробелов, скобок, запятых и собственно `?` — не должно остаться ни одной
 * буквы / цифры. Если остаётся — значит в SQL есть полезный текст (имя
 * таблицы, имя колонки, и т.п.), это не opaque.
 */

const NOISE_TOKENS = /\b(sp_executesql|exec|execute|call|EXEC|EXECUTE|CALL|sp_prepare|sp_unprepare)\b/gi;

export function isOpaqueSql(sql: string | null | undefined): boolean {
  if (!sql) return false;
  const stripped = sql
    .replace(NOISE_TOKENS, " ")
    .replace(/[?{}()[\],;@]/g, " ")
    .replace(/\s+/g, "")
    .trim();
  // Если после очистки осталась хотя бы одна буква/цифра — значит в SQL
  // присутствовал реальный фрагмент (имя таблицы, оператор SELECT, и т.п.).
  return stripped.length === 0;
}
