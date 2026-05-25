/**
 * Sprint 10 — 6 встроенных шаблонов logcfg.xml.
 *
 * Шаблоны хранятся как TypeScript constants — не из сети, не opensource.
 * Только curated наборы от разработчика продукта.
 */

import type { Template } from "./types";

export const BUILTIN_TEMPLATES: Template[] = [
  {
    id: "minimal",
    name: "Минимальный",
    description: "Только ошибки и дедлоки. Минимальный объём. Подходит для постоянного сбора в проде.",
    estimated_volume: "low",
    volume_hint: "до 10 МБ/час на обычной нагрузке",
    config: {
      events: {
        EXCP: { enabled: true },
        TDEADLOCK: { enabled: true },
      },
      capture_plans: false,
      log_directory: "C:\\1C-TechLog",
      history_hours: 168,
    },
  },
  {
    id: "slow_operations",
    name: "Медленные операции",
    description: "CALL + SQL + ошибки. Стандартный набор для расследования торможений. Безопасен по объёму.",
    estimated_volume: "medium",
    volume_hint: "50–200 МБ/час на обычной нагрузке",
    config: {
      events: {
        CALL: { enabled: true, threshold_cs: 100 },
        DBMSSQL: { enabled: true, threshold_cs: 10 },
        DBPOSTGRS: { enabled: true, threshold_cs: 10 },
        EXCP: { enabled: true },
        EXCPCNTX: { enabled: true },
      },
      capture_plans: false,
      log_directory: "C:\\1C-TechLog",
      history_hours: 72,
    },
  },
  {
    id: "full_diagnostic",
    name: "Полная диагностика",
    description: "Все ключевые события + блокировки + планы запросов. Для глубокого расследования. Осторожно с объёмом.",
    estimated_volume: "very_high",
    volume_hint: "500 МБ – 2 ГБ/час. Собирать не более 30–60 минут",
    config: {
      events: {
        CALL: { enabled: true, threshold_cs: 100 },
        SCALL: { enabled: true, threshold_cs: 100 },
        SDBL: { enabled: true, threshold_cs: 10 },
        DBMSSQL: { enabled: true, threshold_cs: 10 },
        DBPOSTGRS: { enabled: true, threshold_cs: 10 },
        TDEADLOCK: { enabled: true },
        TLOCK: { enabled: true, threshold_cs: 100 },
        EXCP: { enabled: true },
        EXCPCNTX: { enabled: true },
      },
      capture_plans: true,
      log_directory: "C:\\1C-TechLog",
      history_hours: 4,
    },
  },
  {
    id: "deadlocks_only",
    name: "Только блокировки",
    description: "Дедлоки + управляемые блокировки + SQL. Для расследования конфликтов при параллельной работе.",
    estimated_volume: "medium",
    volume_hint: "100–300 МБ/час на активной нагрузке",
    config: {
      events: {
        TDEADLOCK: { enabled: true },
        TLOCK: { enabled: true, threshold_cs: 100 },
        DBMSSQL: { enabled: true, threshold_cs: 50 },
        DBPOSTGRS: { enabled: true, threshold_cs: 50 },
        EXCP: { enabled: true },
      },
      capture_plans: false,
      log_directory: "C:\\1C-TechLog",
      history_hours: 72,
    },
  },
  {
    id: "expert_audit",
    name: "Аудит (1С:Эксперт)",
    description: "Канонический набор из курса 1С:Эксперт по производительности. Для профессионального аудита системы.",
    estimated_volume: "high",
    volume_hint: "300–700 МБ/час. Собирать 60–120 минут с рабочей нагрузкой",
    config: {
      events: {
        CALL: { enabled: true, threshold_cs: 100 },
        SCALL: { enabled: true, threshold_cs: 100 },
        DBMSSQL: { enabled: true, threshold_cs: 10 },
        DBPOSTGRS: { enabled: true, threshold_cs: 10 },
        SDBL: { enabled: true, threshold_cs: 10 },
        TDEADLOCK: { enabled: true },
        TLOCK: { enabled: true, threshold_cs: 100 },
        EXCP: { enabled: true },
        EXCPCNTX: { enabled: true },
        MEM: { enabled: true },
      },
      capture_plans: false,
      log_directory: "C:\\1C-TechLog",
      history_hours: 24,
    },
  },
  {
    id: "pre_release_baseline",
    name: "Baseline перед релизом",
    description: "Лёгкий набор для сравнения «до и после» обновления. Минимум влияния на производительность.",
    estimated_volume: "low",
    volume_hint: "30–100 МБ/час на обычной нагрузке",
    config: {
      events: {
        CALL: { enabled: true, threshold_cs: 200 },
        DBMSSQL: { enabled: true, threshold_cs: 100 },
        DBPOSTGRS: { enabled: true, threshold_cs: 100 },
        EXCP: { enabled: true },
        TDEADLOCK: { enabled: true },
      },
      capture_plans: false,
      log_directory: "C:\\1C-TechLog",
      history_hours: 168,
    },
  },
];

/** Возвращает шаблон по id. Undefined если не найден. */
export function getTemplateById(id: string): Template | undefined {
  return BUILTIN_TEMPLATES.find((t) => t.id === id);
}
