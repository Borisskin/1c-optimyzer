/**
 * Sprint 10 — VolumePreview: карточка с heuristic-оценкой объёма логов
 * (тихая / типичная / пиковая нагрузка + предупреждение при >1 ГБ/ч).
 */
import { useMemo } from "react";
import type { LogcfgConfig } from "../types";
import { estimateVolume, formatVolume } from "../volumeEstimator";
import styles from "./VolumePreview.module.css";

interface Props {
  config: LogcfgConfig;
}

export function VolumePreview({ config }: Props) {
  const est = useMemo(() => estimateVolume(config), [config]);

  return (
    <div className={styles.card}>
      <div className={styles.title}>Объём логов</div>
      <div className={styles.rows}>
        <div className={styles.row}>
          <span className={styles.row_label}>Тихая нагрузка</span>
          <span className={styles.row_value}>{formatVolume(est.quiet)}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.row_label}>Типичная</span>
          <span className={styles.row_value}>{formatVolume(est.typical)}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.row_label}>Пиковая</span>
          <span className={styles.row_value}>{formatVolume(est.busy)}</span>
        </div>
      </div>
      {est.warning_if_too_large && (
        <div className={styles.warning}>
          ⚠&nbsp;Большой объём логов. Убедитесь, что на диске достаточно свободного места.
        </div>
      )}
      <div className={styles.disclaimer}>
        Оценка приблизительная — зависит от реальной нагрузки на базу и числа пользователей.
      </div>
    </div>
  );
}
