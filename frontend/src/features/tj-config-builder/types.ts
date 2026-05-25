/**
 * Sprint 10 — TJ Config Builder: типы данных.
 *
 * LogcfgConfig — структурированная модель logcfg.xml (не raw XML).
 * XML генерируется из неё через xmlSerializer.ts.
 */

export type EventType =
  | "CALL"
  | "SCALL"
  | "SDBL"
  | "DBMSSQL"
  | "DBPOSTGRS"
  | "TDEADLOCK"
  | "TLOCK"
  | "EXCP"
  | "EXCPCNTX"
  | "ADMIN"
  | "MEM"
  | "ATTN"
  | "TTIMEOUT";

/** Все типы событий — для итерации и валидации. */
export const ALL_EVENT_TYPES: EventType[] = [
  "CALL", "SCALL", "SDBL", "DBMSSQL", "DBPOSTGRS",
  "TDEADLOCK", "TLOCK", "EXCP", "EXCPCNTX",
  "ADMIN", "MEM", "ATTN", "TTIMEOUT",
];

/** События у которых есть порог длительности (Duration threshold). */
export const EVENTS_WITH_DURATION: Set<EventType> = new Set([
  "CALL", "SCALL", "SDBL", "DBMSSQL", "DBPOSTGRS", "TLOCK",
]);

export type EventConfig = {
  enabled: boolean;
  /** Порог в centiseconds (1 cs = 10 мс). undefined / null = нет фильтра. */
  threshold_cs?: number | null;
};

/** Полная конфигурация logcfg.xml в структурированном виде. */
export type LogcfgConfig = {
  platform_version?: string;
  events: Partial<Record<EventType, EventConfig>>;
  /** Собирать планы запросов (plansqltext). Увеличивает объём в 3-4×. */
  capture_plans: boolean;
  /** Путь к папке хранения логов ТЖ. */
  log_directory: string;
  /** Период хранения логов в часах (атрибут history в logcfg.xml). */
  history_hours: number;
};

/** Значения по умолчанию для новой конфигурации. */
export const DEFAULT_LOGCFG_CONFIG: LogcfgConfig = {
  events: {},
  capture_plans: false,
  log_directory: "C:\\1C-TechLog",
  history_hours: 72,
};

/** Один встроенный шаблон. */
export type Template = {
  id: string;
  name: string;
  description: string;
  /** Оценочный уровень объёма логов. */
  estimated_volume: "low" | "medium" | "high" | "very_high";
  /** Подсказка об объёме для tooltip. */
  volume_hint: string;
  config: LogcfgConfig;
};

/** Оценка объёма логов по трём уровням нагрузки. */
export type VolumeEstimate = {
  /** МБ/час при тихой базе (~10 user, минимальная нагрузка). */
  quiet: number;
  /** МБ/час при обычной нагрузке (~50 user). */
  typical: number;
  /** МБ/час при активной нагрузке (200+ user, пики). */
  busy: number;
  /** True если typical > 1000 МБ/час — требуется предупреждение. */
  warning_if_too_large: boolean;
};

/** Ответ от AI endpoint (соответствует серверной схеме). */
export type AiLogcfgResponse = {
  config: LogcfgConfig;
  explanation: string;
  events_rationale: Array<{
    event: string;
    threshold: string;
    why: string;
  }>;
  estimated_use_duration: string;
  warnings: string[];
  model_used: string;
  duration_ms: number;
};
