/**
 * Sprint 7 Phase A — статистика по одному statement (cost / runtime / memory).
 */

import type { PlanStatement } from "@/api/backend";
import { t } from "@/i18n/ru";
import styles from "./PlanAnalyzer.module.css";

interface Props {
  statement: PlanStatement;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  if (n >= 100) return n.toFixed(0);
  if (n >= 1) return n.toFixed(2);
  return n.toFixed(4);
}

function formatMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)} с`;
  return `${ms} мс`;
}

function formatKb(kb: number | null | undefined): string {
  if (kb == null || kb === 0) return "—";
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} МБ`;
  return `${kb} КБ`;
}

export function PlanStats({ statement }: Props) {
  const mg = statement.memory_grant;
  const qt = statement.query_time;
  return (
    <div className={styles.statsGrid}>
      <div className={styles.statCell}>
        <div className={styles.statLabel}>{t.planAnalyzer.stats.cost}</div>
        <div className={styles.statValue}>{statement.estimated_cost.toFixed(3)}</div>
      </div>
      <div className={styles.statCell}>
        <div className={styles.statLabel}>{t.planAnalyzer.stats.rows}</div>
        <div className={styles.statValue}>{formatNumber(statement.estimated_rows)}</div>
      </div>
      <div className={styles.statCell}>
        <div className={styles.statLabel}>{t.planAnalyzer.stats.compile}</div>
        <div className={styles.statValue}>{formatMs(statement.compile_time_ms)}</div>
      </div>
      <div className={styles.statCell}>
        <div className={styles.statLabel}>{t.planAnalyzer.stats.cachedPlan}</div>
        <div className={styles.statValue}>{formatKb(statement.cached_plan_size_kb)}</div>
      </div>
      {statement.cardinality_estimation_model != null && statement.cardinality_estimation_model > 0 && (
        <div className={styles.statCell}>
          <div className={styles.statLabel}>{t.planAnalyzer.stats.cardModel}</div>
          <div className={styles.statValue}>v{statement.cardinality_estimation_model}</div>
        </div>
      )}
      {statement.degree_of_parallelism != null && statement.degree_of_parallelism > 0 && (
        <div className={styles.statCell}>
          <div className={styles.statLabel}>{t.planAnalyzer.stats.dop}</div>
          <div className={styles.statValue}>{statement.degree_of_parallelism}</div>
        </div>
      )}
      {qt && qt.elapsed_time_ms > 0 && (
        <>
          <div className={styles.statCell}>
            <div className={styles.statLabel}>{t.planAnalyzer.stats.cpuTime}</div>
            <div className={styles.statValue}>{formatMs(qt.cpu_time_ms)}</div>
          </div>
          <div className={styles.statCell}>
            <div className={styles.statLabel}>{t.planAnalyzer.stats.elapsedTime}</div>
            <div className={styles.statValue}>{formatMs(qt.elapsed_time_ms)}</div>
          </div>
        </>
      )}
      {mg && mg.granted_kb > 0 && (
        <>
          <div className={styles.statCell}>
            <div className={styles.statLabel}>{t.planAnalyzer.stats.memoryGranted}</div>
            <div className={styles.statValue}>{formatKb(mg.granted_kb)}</div>
          </div>
          <div className={styles.statCell}>
            <div className={styles.statLabel}>{t.planAnalyzer.stats.memoryUsed}</div>
            <div className={styles.statValue}>{formatKb(mg.max_used_kb)}</div>
          </div>
        </>
      )}
    </div>
  );
}
