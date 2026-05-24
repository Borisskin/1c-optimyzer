/**
 * Sprint 7 Phase C — AI structured explanation для execution plan.
 *
 * Структура response от server /v1/ai/explain_plan:
 *   - summary (1-2 предложения)
 *   - overall_severity (Critical | Warning | Info)
 *   - hotspots: проблемные операторы с what/why/what_to_do
 *   - recommendations: actionable рекомендации (rewrite, index, config, stats)
 *   - suggested_indexes: CREATE INDEX с rationale
 *
 * UX: expandable sections, severity-color-coded badges, click на hotspot
 * с operator_node_id может (Phase B+) подсвечивать оператор в visualization.
 */

import { useState } from "react";
import type {
  AiExplainPlanResponse,
  AiPlanHotspot,
  AiPlanRecommendation,
  AiPlanSuggestedIndex,
  PlanSeverity,
} from "@/api/cloud";
import styles from "./AiPlanExplanationCard.module.css";

interface Props {
  response: AiExplainPlanResponse | null;
  loading: boolean;
  error: string | null;
  /** Показать idle-state с кнопкой запроса (если ни response/loading/error). */
  showIdleButton?: boolean;
  /** Колбек на клик «Получить AI-объяснение» — родитель вызывает analyze. */
  onRequest?: () => void;
}

const SEV_LABEL: Record<PlanSeverity, string> = {
  Critical: "КРИТИЧНО",
  Warning: "ПРЕДУПРЕЖДЕНИЕ",
  Info: "ИНФО",
};

const SEV_CLASS: Record<PlanSeverity, string> = {
  Critical: styles.sevCritical,
  Warning: styles.sevWarning,
  Info: styles.sevInfo,
};

const CATEGORY_LABEL: Record<AiPlanRecommendation["category"], string> = {
  index: "Индекс",
  query_rewrite: "Переписать запрос",
  config: "Конфигурация SQL",
  stats: "Статистика",
};

const IMPACT_CLASS: Record<AiPlanRecommendation["impact_estimate"], string> = {
  Critical: styles.impactCritical,
  High: styles.impactHigh,
  Medium: styles.impactMedium,
  Low: styles.impactLow,
};

export function AiPlanExplanationCard({
  response,
  loading,
  error,
  showIdleButton,
  onRequest,
}: Props) {
  // Idle: ни response/loading/error и родитель просит показать кнопку.
  if (showIdleButton && !response && !loading && !error) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.title}>AI-объяснение плана</div>
        </div>
        <div className={styles.idleBody}>
          <div className={styles.idleHint}>
            AI разберёт план, выделит проблемные операторы и предложит индексы.
            Один запрос = одна консультация (учитывается в квоте).
          </div>
          <button type="button" className={styles.idleButton} onClick={onRequest}>
            Получить AI-объяснение
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.title}>AI-объяснение плана</div>
        </div>
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <div>AI анализирует план запроса…</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.title}>AI-объяснение плана</div>
        </div>
        <div className={styles.errorBox}>
          <div className={styles.errorTitle}>Не удалось получить AI explanation</div>
          <div className={styles.errorDetail}>{error}</div>
        </div>
      </div>
    );
  }

  if (!response) return null;

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.title}>AI-объяснение плана</div>
        <div className={styles.meta}>
          <span className={`${styles.severityBadge} ${SEV_CLASS[response.overall_severity]}`}>
            {SEV_LABEL[response.overall_severity]}
          </span>
        </div>
      </div>

      {response.plan_truncated && (
        <div className={styles.truncatedBanner}>
          Plan XML был обрезан до 50&nbsp;000 символов для AI — объяснение может быть неполным.
        </div>
      )}

      <div className={styles.summary}>{response.summary}</div>

      {response.hotspots.length > 0 && (
        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>
            Проблемные операторы ({response.hotspots.length})
          </h3>
          {response.hotspots.map((h, idx) => (
            <HotspotBlock key={idx} hotspot={h} />
          ))}
        </section>
      )}

      {response.recommendations.length > 0 && (
        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>
            Рекомендации ({response.recommendations.length})
          </h3>
          {response.recommendations.map((r, idx) => (
            <RecommendationBlock key={idx} rec={r} />
          ))}
        </section>
      )}

      {response.suggested_indexes.length > 0 && (
        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>
            Предложенные индексы ({response.suggested_indexes.length})
          </h3>
          {response.suggested_indexes.map((idx, i) => (
            <SuggestedIndexBlock key={i} index={idx} />
          ))}
        </section>
      )}
    </div>
  );
}

function HotspotBlock({ hotspot }: { hotspot: AiPlanHotspot }) {
  const [expanded, setExpanded] = useState(false);
  const sevClass = SEV_CLASS[hotspot.severity];
  return (
    <div className={`${styles.hotspot} ${sevClass}`}>
      <div
        className={styles.hotspotHeader}
        onClick={() => setExpanded((v) => !v)}
        style={{ cursor: "pointer" }}
      >
        <span className={`${styles.severityBadge} ${sevClass}`}>
          {SEV_LABEL[hotspot.severity]}
        </span>
        <span className={styles.hotspotTitle}>
          {hotspot.operator_type}
          {hotspot.operator_node_id != null ? ` #${hotspot.operator_node_id}` : ""}
        </span>
        <span className={styles.expandIcon}>{expanded ? "−" : "+"}</span>
      </div>
      {expanded && (
        <div className={styles.hotspotBody}>
          <Field label="Что происходит" text={hotspot.what} />
          <Field label="Почему это плохо" text={hotspot.why} />
          <Field label="Что делать" text={hotspot.what_to_do} />
        </div>
      )}
    </div>
  );
}

function RecommendationBlock({ rec }: { rec: AiPlanRecommendation }) {
  return (
    <div className={styles.recommendation}>
      <div className={styles.recHeader}>
        <span className={styles.recCategoryChip}>{CATEGORY_LABEL[rec.category]}</span>
        <span className={styles.recTitle}>{rec.title}</span>
        <span className={`${styles.impactBadge} ${IMPACT_CLASS[rec.impact_estimate]}`}>
          {rec.impact_estimate}
        </span>
      </div>
      <div className={styles.recDescription}>{rec.description}</div>
    </div>
  );
}

function SuggestedIndexBlock({ index }: { index: AiPlanSuggestedIndex }) {
  const createStmt = buildCreateIndexStatement(index);
  return (
    <div className={styles.indexCard}>
      <div className={styles.indexHead}>
        <span className={styles.indexTable}>{index.table}</span>
        <span className={`${styles.impactBadge} ${IMPACT_CLASS[index.impact_estimate]}`}>
          {index.impact_estimate}
        </span>
      </div>
      {index.columns.length > 0 && (
        <div className={styles.indexCols}>
          Ключевые колонки: {index.columns.join(", ")}
          {index.include.length > 0 && ` · INCLUDE: ${index.include.join(", ")}`}
        </div>
      )}
      {index.rationale && <div className={styles.indexRationale}>{index.rationale}</div>}
      {createStmt && <pre className={styles.indexSql}>{createStmt}</pre>}
    </div>
  );
}

function Field({ label, text }: { label: string; text: string }) {
  return (
    <div className={styles.field}>
      <div className={styles.fieldLabel}>{label}</div>
      <div className={styles.fieldText}>{text}</div>
    </div>
  );
}

function buildCreateIndexStatement(idx: AiPlanSuggestedIndex): string {
  if (idx.columns.length === 0) return "";
  const cols = idx.columns.map((c) => `[${c}]`).join(", ");
  const incl =
    idx.include.length > 0
      ? `\n  INCLUDE (${idx.include.map((c) => `[${c}]`).join(", ")})`
      : "";
  const idxName = `IX_${idx.table.replace(/\W+/g, "")}_${idx.columns.join("_")}`.slice(0, 120);
  return `CREATE NONCLUSTERED INDEX [${idxName}]\n  ON [${idx.table}] (${cols})${incl};`;
}
