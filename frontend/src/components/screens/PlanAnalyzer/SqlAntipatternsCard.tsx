/**
 * Sprint 8 Phase C — Карточка обнаруженных SQL antipatterns.
 *
 * Показывается рядом с AI plan explanation в PlanAnalyzer. Findings
 * приходят от backend sql_antipatterns.detect RPC (быстро — локальный
 * sqlglot parser, не cloud). AI explanation запускается параллельно.
 *
 * UX:
 *   - Severity badges (Critical красный / Warning жёлтый / Info серый)
 *   - Engine badge (MSSQL / PostgreSQL)
 *   - 1С context indicator (если is_1c_context = true)
 *   - Каждая находка — collapsed card с title + severity, expand для rationale
 *     + recommendation
 */

import { useState } from "react";
import type {
  PlanEngine,
  SqlAntipatternFinding,
  SqlAntipatternSeverity,
} from "@/api/backend";
import styles from "./SqlAntipatternsCard.module.css";

interface Props {
  findings: SqlAntipatternFinding[] | null;
  loading: boolean;
  error: string | null;
  engine: PlanEngine | null;
  is1cContext: boolean;
}

const SEV_LABEL: Record<SqlAntipatternSeverity, string> = {
  Critical: "КРИТИЧНО",
  Warning: "ПРЕДУПРЕЖДЕНИЕ",
  Info: "ИНФО",
  Blocker: "БЛОКЕР",
  Major: "ВАЖНО",
  Minor: "СТИЛЬ",
};

const SEV_CLASS: Record<SqlAntipatternSeverity, string> = {
  Critical: styles.sevCritical,
  Warning: styles.sevWarning,
  Info: styles.sevInfo,
  Blocker: styles.sevCritical,
  Major: styles.sevWarning,
  Minor: styles.sevInfo,
};

const ENGINE_LABEL: Record<PlanEngine, string> = {
  mssql: "MS SQL",
  postgres: "PostgreSQL",
};

const ENGINE_CLASS: Record<PlanEngine, string> = {
  mssql: styles.engMssql,
  postgres: styles.engPg,
};

function FindingRow({ finding }: { finding: SqlAntipatternFinding }) {
  const [open, setOpen] = useState(false);
  const sevClass = SEV_CLASS[finding.severity] ?? styles.sevInfo;
  const sevLabel = SEV_LABEL[finding.severity] ?? finding.severity;
  return (
    <div className={styles.finding}>
      <div
        className={styles.findingHead}
        onClick={() => setOpen((v) => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((v) => !v);
          }
        }}
      >
        <span className={`${styles.sevBadge} ${sevClass}`}>{sevLabel}</span>
        <span className={styles.title}>{finding.title}</span>
        {finding.is_1c_context_only && (
          <span className={styles.ctx1c}>1С</span>
        )}
      </div>
      {open && (
        <div className={styles.findingBody}>
          <div className={styles.section}>
            <div className={styles.sectionLabel}>Что произошло</div>
            <div className={styles.sectionText}>{finding.description}</div>
          </div>
          {finding.rationale && (
            <div className={styles.section}>
              <div className={styles.sectionLabel}>Почему это проблема</div>
              <div className={styles.sectionText}>{finding.rationale}</div>
            </div>
          )}
          {finding.recommendation && (
            <div className={styles.section}>
              <div className={styles.sectionLabel}>Что сделать</div>
              <div className={styles.sectionText}>{finding.recommendation}</div>
            </div>
          )}
          {finding.snippet && (
            <pre className={styles.snippet}>{finding.snippet}</pre>
          )}
        </div>
      )}
    </div>
  );
}

export function SqlAntipatternsCard({
  findings,
  loading,
  error,
  engine,
  is1cContext,
}: Props) {
  if (loading) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <h3 className={styles.cardTitle}>Антипаттерны SQL</h3>
        </div>
        <div className={styles.loading}>Анализ запроса…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <h3 className={styles.cardTitle}>Антипаттерны SQL</h3>
        </div>
        <div className={styles.error}>Ошибка анализа: {error}</div>
      </div>
    );
  }

  if (findings === null) {
    return null; // ничего не запрашивали
  }

  if (findings.length === 0) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <h3 className={styles.cardTitle}>Антипаттерны SQL</h3>
          {engine && (
            <span className={`${styles.engBadge} ${ENGINE_CLASS[engine]}`}>
              {ENGINE_LABEL[engine]}
            </span>
          )}
          {is1cContext && <span className={styles.ctx1c}>1С-контекст</span>}
        </div>
        <div className={styles.empty}>
          Антипаттернов не обнаружено — запрос чистый.
        </div>
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.cardTitle}>
          Антипаттерны SQL ({findings.length})
        </h3>
        {engine && (
          <span className={`${styles.engBadge} ${ENGINE_CLASS[engine]}`}>
            {ENGINE_LABEL[engine]}
          </span>
        )}
        {is1cContext && <span className={styles.ctx1c}>1С-контекст</span>}
      </div>
      <div className={styles.findings}>
        {findings.map((f, i) => (
          <FindingRow key={`${f.code}-${i}`} finding={f} />
        ))}
      </div>
    </div>
  );
}
