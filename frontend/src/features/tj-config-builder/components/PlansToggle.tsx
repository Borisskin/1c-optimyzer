/**
 * Sprint 10 — PlansToggle: переключатель сбора планов запросов (plansqltext).
 */
import type { LogcfgConfig } from "../types";
import styles from "./PlansToggle.module.css";

interface Props {
  config: LogcfgConfig;
  onChange: (value: boolean) => void;
}

export function PlansToggle({ config, onChange }: Props) {
  return (
    <label className={styles.root}>
      <input
        type="checkbox"
        className={styles.checkbox}
        checked={config.capture_plans}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className={styles.content}>
        <span className={styles.label}>Собирать планы запросов</span>
        <span className={styles.hint}>
          Включает plansqltext для событий DBMSSQL / DBPOSTGRS.
          Увеличивает объём логов в 3–4 раза.
        </span>
      </span>
    </label>
  );
}
