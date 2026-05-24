/**
 * Sprint 6 Phase E — AI explanation card.
 *
 * Structured output от Claude Sonnet 4.5 поверх bsl-LS диагностик.
 * Premium feature (Pro/Business): объяснение проблем + suggested rewrite.
 */

import { useState } from "react";
import type { AiExplainResponse } from "@/api/cloud";
import styles from "./AiExplanationCard.module.css";

interface Props {
  response: AiExplainResponse | null;
  loading: boolean;
  error: string | null;
  onAcceptRewrite?: (sdbl: string) => void;
  /** Показать idle-state с кнопкой запроса (если нет response/loading/error). */
  showIdleButton?: boolean;
  onRequest?: () => void;
}

const SEV_LABEL = {
  Blocker: "БЛОКЕР",
  Critical: "КРИТИЧНО",
  Major: "ВАЖНО",
  Minor: "МИНОР",
  Info: "ИНФО",
} as const;

export function AiExplanationCard({
  response,
  loading,
  error,
  onAcceptRewrite,
  showIdleButton,
  onRequest,
}: Props) {
  // Sprint 7 post-Phase F — collapse toggle (default COLLAPSED).
  // Карточка занимает много места под редактором, юзеру удобнее видеть
  // компактный header «AI объяснение [Развернуть]» и раскрывать по запросу.
  // Симметрично AiPlanExplanationCard в PlanAnalyzer.
  const [collapsed, setCollapsed] = useState(true);

  // Skip render если совсем нечего показывать.
  const isIdle = showIdleButton && !response && !loading && !error;
  if (!isIdle && !loading && !error && !response) return null;

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.title}>AI объяснение</div>
        <button
          type="button"
          className={styles.collapseToggle}
          onClick={() => setCollapsed((v) => !v)}
          aria-expanded={!collapsed}
        >
          {collapsed ? "Развернуть" : "Свернуть"}
        </button>
      </div>

      {/* display:none сохраняет DOM (response state не теряется при свёртывании) */}
      <div className={collapsed ? styles.bodyCollapsed : styles.body}>
        {isIdle && (
          <div className={styles.idleBody}>
            <div className={styles.idleHint}>
              AI разберёт диагностики bsl-LS, объяснит каждую проблему и предложит
              переписать запрос. Один запрос = одна консультация (учитывается в квоте).
            </div>
            <button type="button" className={styles.idleButton} onClick={onRequest}>
              Получить AI-объяснение
            </button>
          </div>
        )}

        {loading && (
          <div className={styles.loading}>
            <div className={styles.spinner} />
            <div>AI анализирует запрос…</div>
          </div>
        )}

        {error && !loading && (
          <div className={styles.errorBox}>
            <div className={styles.errorTitle}>Не удалось получить AI explanation</div>
            <div className={styles.errorDetail}>{error}</div>
          </div>
        )}

        {response && !loading && !error && (
          <>
            <div className={styles.summary}>{response.explanation_summary}</div>

            {response.issues.length > 0 && (
              <div className={styles.issues}>
                {response.issues.map((issue, idx) => (
                  <IssueBlock key={idx} issue={issue} />
                ))}
              </div>
            )}

            {response.suggested_rewrite.available && response.suggested_rewrite.sdbl && (
              <RewriteBlock
                sdbl={response.suggested_rewrite.sdbl}
                reasoning={response.suggested_rewrite.reasoning ?? ""}
                onAccept={onAcceptRewrite}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

function IssueBlock({ issue }: { issue: AiExplainResponse["issues"][0] }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className={styles.issue}>
      <div
        className={styles.issueHeader}
        onClick={() => setExpanded((v) => !v)}
        style={{ cursor: "pointer" }}
      >
        <div className={`${styles.sevBadge} ${styles[`sev${issue.severity}`]}`}>
          {SEV_LABEL[issue.severity]}
        </div>
        <div className={styles.issueTitle}>{issue.title}</div>
        <div className={styles.expandIcon}>{expanded ? "−" : "+"}</div>
      </div>

      {expanded && (
        <div className={styles.issueBody}>
          <div className={styles.field}>
            <div className={styles.fieldLabel}>Что происходит</div>
            <div className={styles.fieldText}>{issue.what}</div>
          </div>
          <div className={styles.field}>
            <div className={styles.fieldLabel}>Почему это плохо</div>
            <div className={styles.fieldText}>{issue.why}</div>
          </div>
          <div className={styles.field}>
            <div className={styles.fieldLabel}>Что делать</div>
            <div className={styles.fieldText}>{issue.what_to_do}</div>
          </div>
          {issue.linked_diagnostic_codes.length > 0 && (
            <div className={styles.linkedCodes}>
              {issue.linked_diagnostic_codes.map((c) => (
                <code key={c} className={styles.linkedChip}>
                  {c}
                </code>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RewriteBlock({
  sdbl,
  reasoning,
  onAccept,
}: {
  sdbl: string;
  reasoning: string;
  onAccept?: (sdbl: string) => void;
}) {
  return (
    <div className={styles.rewrite}>
      <div className={styles.rewriteHeader}>
        <div className={styles.rewriteTitle}>Предложенное переписывание</div>
        {onAccept && (
          <button
            type="button"
            className={styles.acceptBtn}
            onClick={() => onAccept(sdbl)}
          >
            Принять
          </button>
        )}
      </div>
      <pre className={styles.rewriteCode}>
        <code>{sdbl}</code>
      </pre>
      {reasoning && (
        <div className={styles.rewriteReasoning}>
          <strong>Изменения:</strong> {reasoning}
        </div>
      )}
    </div>
  );
}
