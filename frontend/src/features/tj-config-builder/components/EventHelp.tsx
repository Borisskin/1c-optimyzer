/**
 * Sprint 10 — EventHelp: иконка «?» с CSS hover-тултипом по событию ТЖ.
 */
import styles from "./EventHelp.module.css";

interface EventInfo {
  description: string;
  hint: string;
}

const EVENT_INFO: Record<string, EventInfo> = {
  CALL: {
    description: "Вызовы методов бизнес-логики: запись, проведение, расчёт итогов.",
    hint: "Самое «шумное» событие. Рекомендуемый порог: 1000–5000 cs.",
  },
  SCALL: {
    description: "Серверные вызовы в клиент-серверной архитектуре (client → server RPC).",
    hint: "Для диагностики лагов интерфейса. Порог 1000–3000 cs.",
  },
  SDBL: {
    description: "Запросы на языке 1С (SDBL) до трансляции в SQL.",
    hint: "Анализ медленных запросов 1С. Порог 500–2000 cs.",
  },
  DBMSSQL: {
    description: "SQL-запросы к MS SQL Server на уровне СУБД.",
    hint: "Детальный анализ SQL. Порог 500–2000 cs. Генерирует много данных.",
  },
  DBPOSTGRS: {
    description: "SQL-запросы к PostgreSQL на уровне СУБД.",
    hint: "Детальный анализ SQL для PostgreSQL. Порог 500–2000 cs.",
  },
  TDEADLOCK: {
    description: "Взаимоблокировки (deadlocks) управляемых блокировок 1С.",
    hint: "Включайте без порога — событий мало, но каждое важно.",
  },
  TLOCK: {
    description: "Ожидания управляемых блокировок 1С (lock waits).",
    hint: "Анализ конкурентного доступа. Порог 1000–5000 cs.",
  },
  EXCP: {
    description: "Исключения (ошибки) в 1С — необработанные и перехваченные.",
    hint: "Включайте всегда при диагностике.",
  },
  EXCPCNTX: {
    description: "Контекст исключения — стек вызовов в момент ошибки.",
    hint: "Дополняет EXCP точным стеком. Включайте вместе с EXCP.",
  },
  ADMIN: {
    description: "Административные события: сеансы, аутентификация, изменения ИБ.",
    hint: "Аудит безопасности и проблем с сеансами.",
  },
  MEM: {
    description: "Использование памяти рабочими процессами 1С.",
    hint: "Только при подозрении на утечку памяти.",
  },
  ATTN: {
    description: "Принудительное завершение соединений с СУБД (ATTENTION).",
    hint: "Диагностика обрывов соединений и таймаутов СУБД.",
  },
  TTIMEOUT: {
    description: "Таймауты ожидания управляемых блокировок 1С.",
    hint: "Анализ конфликтов блокировок. Включайте вместе с TLOCK.",
  },
};

interface Props {
  eventType: string;
}

export function EventHelp({ eventType }: Props) {
  const info = EVENT_INFO[eventType];
  if (!info) return null;

  return (
    <span className={styles.root}>
      <span className={styles.icon} aria-label="Справка по событию">?</span>
      <span className={styles.tooltip} role="tooltip">
        <span className={styles.tooltip_text}>{info.description}</span>
        <span className={styles.tooltip_hint}>{info.hint}</span>
      </span>
    </span>
  );
}
