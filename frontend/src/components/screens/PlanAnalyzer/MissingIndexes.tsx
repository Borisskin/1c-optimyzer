/**
 * Sprint 7 Phase A — рекомендации индексов от SQL Server optimizer.
 *
 * Эти данные приходят напрямую из <MissingIndexes> элементов в plan XML
 * (рекомендации SQL Server engine, не custom от PerformanceStudio).
 */

import type { PlanMissingIndex } from "@/api/backend";
import { t } from "@/i18n/ru";
import styles from "./PlanAnalyzer.module.css";

interface Props {
  indexes: PlanMissingIndex[];
}

export function MissingIndexes({ indexes }: Props) {
  if (indexes.length === 0) {
    return (
      <div className={styles.indexesSection}>
        <h3 className={styles.warningsTitle}>{t.planAnalyzer.missingIndexesTitle}</h3>
        <div className={styles.empty}>
          <div className={styles.emptyTitle}>{t.planAnalyzer.missingIndexesEmpty}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.indexesSection}>
      <h3 className={styles.warningsTitle}>
        {t.planAnalyzer.missingIndexesTitle} ({indexes.length})
      </h3>
      {indexes.map((idx, i) => (
        <IndexCard key={i} index={idx} />
      ))}
    </div>
  );
}

function IndexCard({ index }: { index: PlanMissingIndex }) {
  const allColumns = [
    ...index.equality_columns,
    ...index.inequality_columns.map((c) => `${c} (≠)`),
  ];
  return (
    <div className={styles.indexCard}>
      <div className={styles.indexHead}>
        <span className={styles.indexTable}>{index.table}</span>
        <span className={styles.indexImpact}>
          {t.planAnalyzer.stats.indexImpact}: {index.impact.toFixed(1)}%
        </span>
      </div>
      {allColumns.length > 0 && (
        <div className={styles.indexColumns}>
          <span className={styles.indexColumnsLabel}>Колонки:</span>
          {allColumns.join(", ")}
          {index.include_columns.length > 0 && (
            <> · INCLUDE: {index.include_columns.join(", ")}</>
          )}
        </div>
      )}
      {index.create_statement && (
        <pre className={styles.indexCreateBlock}>{index.create_statement}</pre>
      )}
    </div>
  );
}
