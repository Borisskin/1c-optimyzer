/**
 * Sprint 10 — xmlSerializer: LogcfgConfig → logcfg.xml строка.
 *
 * Не используем XML library — простой template builder.
 * Формат совместим с 1С:Предприятие 8.3.18+.
 */

import type { EventType, LogcfgConfig } from "./types";
import { EVENTS_WITH_DURATION } from "./types";

/**
 * Сериализует LogcfgConfig в строку XML для logcfg.xml.
 *
 * Структура:
 * <config>
 *   <log location="..." history="72">
 *     <event>
 *       <eq property="name" value="DBMSSQL"/>
 *       <gt property="duration" value="10"/>   <!-- если threshold > 0 -->
 *     </event>
 *     ...
 *     <property name="all"/>
 *     <property name="plansqltext"/>   <!-- если capture_plans -->
 *   </log>
 *   <plansql/>   <!-- если capture_plans -->
 * </config>
 */
export function serializeToXml(config: LogcfgConfig): string {
  const lines: string[] = [];

  lines.push('<?xml version="1.0" encoding="UTF-8"?>');
  lines.push('<config xmlns="http://v8.1c.ru/v8/tech-log">');
  lines.push(`  <log location="${escapeXml(config.log_directory)}" history="${config.history_hours}">`);

  // События — только enabled.
  const eventEntries = Object.entries(config.events) as [EventType, { enabled: boolean; threshold_cs?: number | null }][];
  for (const [eventType, settings] of eventEntries) {
    if (!settings?.enabled) continue;

    lines.push("    <event>");
    lines.push(`      <eq property="name" value="${eventType}"/>`);

    // Порог — только для событий с Duration и если threshold > 0.
    // ВАЖНО: 1C ТЖ измеряет Duration в сотнях микросекунд (1 unit = 100 мкс).
    // threshold_cs хранится в centiseconds (1 cs = 10 мс = 100 units).
    // Поэтому умножаем на 100: threshold_cs * 100 = значение в 1C-единицах.
    // Пример: threshold_cs=100 (1 сек) → value="10000" (10000 × 100мкс = 1 сек).
    if (
      EVENTS_WITH_DURATION.has(eventType) &&
      settings.threshold_cs != null &&
      settings.threshold_cs > 0
    ) {
      lines.push(`      <gt property="duration" value="${settings.threshold_cs * 100}"/>`);
    }

    lines.push("    </event>");
  }

  // Свойства — всегда собираем все.
  lines.push('    <property name="all"/>');

  if (config.capture_plans) {
    lines.push('    <property name="plansqltext"/>');
  }

  lines.push("  </log>");

  // Директива планов — на уровне config.
  if (config.capture_plans) {
    lines.push("  <plansql/>");
  }

  lines.push("</config>");

  return lines.join("\n");
}

/** Экранирует спецсимволы XML для атрибутов. */
export function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
