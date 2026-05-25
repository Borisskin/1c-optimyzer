/**
 * Sprint 10 — StorageSettings: папка логов + лимит на диске.
 */
import type { LogcfgConfig } from "../types";
import styles from "./StorageSettings.module.css";

interface Props {
  config: LogcfgConfig;
  onDirectoryChange: (value: string) => void;
  onHistoryChange: (value: number) => void;
}

export function StorageSettings({
  config,
  onDirectoryChange,
  onHistoryChange,
}: Props) {
  return (
    <div className={styles.root}>
      <div className={styles.title}>Хранилище</div>
      <div className={styles.fields}>
        <div className={styles.field}>
          <label className={styles.field_label} htmlFor="tj-log-dir">
            Папка логов
          </label>
          <input
            id="tj-log-dir"
            type="text"
            className={styles.input}
            value={config.log_directory}
            onChange={(e) => onDirectoryChange(e.target.value)}
            spellCheck={false}
            autoComplete="off"
          />
        </div>
        <div className={styles.field}>
          <label className={styles.field_label} htmlFor="tj-history">
            Хранить логи
          </label>
          <div className={styles.field_row}>
            <input
              id="tj-history"
              type="number"
              className={[styles.input, styles.input_size].join(" ")}
              value={config.history_hours}
              min={1}
              max={720}
              step={1}
              onChange={(e) =>
                onHistoryChange(
                  Math.max(1, parseInt(e.target.value, 10) || 1),
                )
              }
            />
            <span className={styles.unit}>ч</span>
          </div>
        </div>
      </div>
      <div className={styles.hint}>
        Старые файлы удаляются автоматически по истечении срока хранения.
      </div>
    </div>
  );
}
