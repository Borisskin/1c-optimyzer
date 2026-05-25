/**
 * Sprint 10 — EventRow: строка события ТЖ (чекбокс + имя + порог + help).
 */
import type { EventType, LogcfgConfig } from "../types";
import { EVENTS_WITH_DURATION } from "../types";
import { EventHelp } from "./EventHelp";
import styles from "./EventRow.module.css";

interface Props {
  eventType: EventType;
  config: LogcfgConfig;
  onToggle: (type: EventType) => void;
  onThresholdChange: (type: EventType, value: number | null) => void;
}

export function EventRow({ eventType, config, onToggle, onThresholdChange }: Props) {
  const cfg = config.events[eventType];
  const enabled = cfg?.enabled ?? false;
  const hasThreshold = EVENTS_WITH_DURATION.has(eventType);
  const threshold = cfg?.threshold_cs ?? null;

  return (
    <label
      className={[styles.row, enabled ? styles.row_enabled : ""].join(" ")}
    >
      <input
        type="checkbox"
        className={styles.checkbox}
        checked={enabled}
        onChange={() => onToggle(eventType)}
      />
      <span className={styles.name}>{eventType}</span>
      {hasThreshold && enabled && (
        <span className={styles.threshold}>
          <input
            type="number"
            className={styles.threshold_input}
            value={threshold ?? ""}
            placeholder="∞"
            min={0}
            step={100}
            onChange={(e) =>
              onThresholdChange(
                eventType,
                e.target.value === ""
                  ? null
                  : Math.max(0, parseInt(e.target.value, 10) || 0),
              )
            }
            onClick={(e) => e.stopPropagation()}
          />
          <span className={styles.threshold_unit}>cs</span>
        </span>
      )}
      <EventHelp eventType={eventType} />
    </label>
  );
}
