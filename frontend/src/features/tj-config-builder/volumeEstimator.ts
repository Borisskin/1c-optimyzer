/**
 * Sprint 10 — volumeEstimator: приближённая оценка объёма логов ТЖ.
 *
 * Расчёт ПРИБЛИЖЁННЫЙ. Реальный объём зависит от нагрузки и может
 * отличаться в 2-5 раз. Это явно указывается юзеру в UI.
 *
 * Базовые данные калиброваны по реальным архивам ТЖ из Sprint 9 research.
 */

import type { EventType, LogcfgConfig, VolumeEstimate } from "./types";

/** Базовое количество событий в минуту на типовой базе 50 user. */
const EVENTS_PER_MINUTE: Record<EventType, number> = {
  CALL: 600,       // ~10/сек на 50 user
  SCALL: 200,      // серверные вызовы — реже
  SDBL: 800,       // SDBL компиляция — часто
  DBMSSQL: 1000,   // SQL запросы — высокая частота
  DBPOSTGRS: 1000,
  TDEADLOCK: 0.5,  // дедлоки — редко (< 1 в минуту норма)
  TLOCK: 50,       // управляемые блокировки
  EXCP: 5,         // ошибки
  EXCPCNTX: 5,
  ADMIN: 10,
  MEM: 30,
  ATTN: 2,
  TTIMEOUT: 1,
};

/** Средний размер одной записи события в байтах. */
const AVG_SIZE_BYTES: Record<EventType, number> = {
  CALL: 800,
  SCALL: 600,
  SDBL: 1500,
  DBMSSQL: 3000,    // SQL + context (без плана)
  DBPOSTGRS: 3000,
  TDEADLOCK: 5000,  // граф блокировок — большой
  TLOCK: 1200,
  EXCP: 2000,
  EXCPCNTX: 1500,
  ADMIN: 400,
  MEM: 500,
  ATTN: 300,
  TTIMEOUT: 600,
};

/**
 * Множитель по threshold — какую долю событий поймает порог.
 * Основан на типичном распределении длительностей запросов.
 */
function thresholdMultiplier(thresholdCs: number | null | undefined): number {
  if (thresholdCs == null || thresholdCs <= 0) return 1.0;  // все события
  if (thresholdCs <= 10) return 0.5;   // 100мс — половина событий
  if (thresholdCs <= 100) return 0.2;  // 1с — 20% событий
  if (thresholdCs <= 1000) return 0.05; // 10с — 5% событий
  return 0.01;
}

/**
 * Множитель объёма для планов запросов.
 * DBMSSQL/DBPOSTGRS с планами — в 3-4 раза больше.
 */
function planSizeMultiplier(capturePlans: boolean, eventType: EventType): number {
  if (!capturePlans) return 1;
  if (eventType === "DBMSSQL" || eventType === "DBPOSTGRS") return 4;
  return 1;
}

/**
 * Рассчитывает оценку объёма логов для заданного config.
 *
 * @returns VolumeEstimate с тремя уровнями нагрузки (МБ/час)
 */
export function estimateVolume(config: LogcfgConfig): VolumeEstimate {
  let totalBytesPerMin = 0;

  for (const [eventTypeStr, settings] of Object.entries(config.events)) {
    const eventType = eventTypeStr as EventType;
    if (!settings?.enabled) continue;

    const baseEventsPerMin = EVENTS_PER_MINUTE[eventType] ?? 10;
    const avgSize = AVG_SIZE_BYTES[eventType] ?? 500;
    const planMult = planSizeMultiplier(config.capture_plans, eventType);
    const threshold = settings.threshold_cs;
    const threshMult = thresholdMultiplier(threshold);

    totalBytesPerMin += baseEventsPerMin * avgSize * planMult * threshMult;
  }

  // МБ/час для типовой базы (50 user).
  const mbPerHour = (totalBytesPerMin * 60) / 1_000_000;

  return {
    quiet: mbPerHour * 0.3,   // 10 user, низкая активность
    typical: mbPerHour,        // 50 user, средняя нагрузка
    busy: mbPerHour * 3,       // 200+ user, пиковая нагрузка
    warning_if_too_large: mbPerHour > 1000,  // > 1 ГБ/час
  };
}

/** Форматирует число МБ/час в читаемую строку. */
export function formatVolume(mbPerHour: number): string {
  if (mbPerHour < 1) return "< 1 МБ/ч";
  if (mbPerHour < 1024) return `~${Math.round(mbPerHour)} МБ/ч`;
  return `~${(mbPerHour / 1024).toFixed(1)} ГБ/ч`;
}
