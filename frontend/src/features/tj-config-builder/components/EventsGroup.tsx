/**
 * Sprint 10 — EventsGroup: список событий ТЖ с разворачиваемыми доп. событиями.
 * Без disclosure-треугольников — только cursor:pointer и текстовая кнопка.
 */
import { useState } from "react";
import type { EventType, LogcfgConfig } from "../types";
import { ALL_EVENT_TYPES } from "../types";
import { EventRow } from "./EventRow";
import styles from "./EventsGroup.module.css";

// Основные события (всегда видны — самые востребованные)
const PRIMARY_EVENTS: EventType[] = [
  "EXCP",
  "EXCPCNTX",
  "TDEADLOCK",
  "TTIMEOUT",
  "CALL",
  "SDBL",
  "DBMSSQL",
  "DBPOSTGRS",
];

// Дополнительные события (по умолчанию скрыты)
const SECONDARY_EVENTS: EventType[] = ALL_EVENT_TYPES.filter(
  (e) => !PRIMARY_EVENTS.includes(e),
);

interface Props {
  config: LogcfgConfig;
  onToggle: (type: EventType) => void;
  onThresholdChange: (type: EventType, value: number | null) => void;
}

export function EventsGroup({ config, onToggle, onThresholdChange }: Props) {
  const [showMore, setShowMore] = useState(false);

  return (
    <div className={styles.root}>
      <div className={styles.section_title}>События</div>
      <div className={styles.events_list}>
        {PRIMARY_EVENTS.map((et) => (
          <EventRow
            key={et}
            eventType={et}
            config={config}
            onToggle={onToggle}
            onThresholdChange={onThresholdChange}
          />
        ))}
      </div>

      {showMore && (
        <div className={styles.events_list}>
          {SECONDARY_EVENTS.map((et) => (
            <EventRow
              key={et}
              eventType={et}
              config={config}
              onToggle={onToggle}
              onThresholdChange={onThresholdChange}
            />
          ))}
        </div>
      )}

      {SECONDARY_EVENTS.length > 0 && (
        <button
          className={styles.more_btn}
          onClick={() => setShowMore((v) => !v)}
        >
          {showMore
            ? "Скрыть дополнительные события"
            : `Ещё ${SECONDARY_EVENTS.length} события`}
        </button>
      )}
    </div>
  );
}
