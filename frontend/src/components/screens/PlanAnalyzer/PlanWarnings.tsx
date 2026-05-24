/**
 * Sprint 7 Phase A — список warnings от PerformanceStudio CLI.
 *
 * Severity scheme: Info | Warning | Critical — отдельная от bsl-LS scheme
 * (Blocker/Critical/Major/Minor/Info). У каждого экрана своя номенклатура
 * для разных доменов анализа (ADR-040 Sprint 7).
 */

import { useMemo } from "react";
import type { PlanWarning } from "@/api/backend";
import { t } from "@/i18n/ru";
import styles from "./PlanAnalyzer.module.css";

interface Props {
  warnings: PlanWarning[];
}

const SEV_CARD: Record<string, string> = {
  Critical: styles.warningCardCritical,
  Warning: styles.warningCardWarning,
  Info: styles.warningCardInfo,
};

const SEV_LABEL: Record<string, string> = {
  Critical: t.planAnalyzer.severity.Critical,
  Warning: t.planAnalyzer.severity.Warning,
  Info: t.planAnalyzer.severity.Info,
};

export function PlanWarnings({ warnings }: Props) {
  const sorted = useMemo(() => {
    const order: Record<string, number> = { Critical: 0, Warning: 1, Info: 2 };
    return [...warnings].sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9));
  }, [warnings]);

  if (sorted.length === 0) {
    return (
      <div className={styles.warningsSection}>
        <h3 className={styles.warningsTitle}>{t.planAnalyzer.warningsTitle}</h3>
        <div className={styles.empty}>
          <div className={styles.emptyTitle}>{t.planAnalyzer.warningsEmpty}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.warningsSection}>
      <h3 className={styles.warningsTitle}>
        {t.planAnalyzer.warningsTitle} ({sorted.length})
      </h3>
      {sorted.map((w, idx) => (
        <WarningCard key={idx} warning={w} />
      ))}
    </div>
  );
}

function WarningCard({ warning }: { warning: PlanWarning }) {
  const severityClass = SEV_CARD[warning.severity] ?? styles.warningCardInfo;
  const severityLabel = SEV_LABEL[warning.severity] ?? warning.severity;
  return (
    <div className={`${styles.warningCard} ${severityClass}`}>
      <div className={styles.warningHead}>
        <span className={styles.warningType}>{warning.type || severityLabel}</span>
        {warning.operator && (
          <span className={styles.warningOperator}>
            {warning.operator}
            {warning.node_id != null ? ` #${warning.node_id}` : ""}
          </span>
        )}
        {typeof warning.max_benefit_percent === "number" && (
          <span className={styles.warningBenefit}>
            benefit ≈ {warning.max_benefit_percent.toFixed(0)}%
          </span>
        )}
      </div>
      <div className={styles.warningMessage}>{warning.message}</div>
      {warning.actionable_fix && (
        <div className={styles.warningFix}>
          <span className={styles.warningFixLabel}>Что делать:</span>
          {warning.actionable_fix}
        </div>
      )}
    </div>
  );
}
