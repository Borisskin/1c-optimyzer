/**
 * Sprint 7 Phase A — главный экран Plan Analyzer.
 *
 * Flow:
 *   1. PlanImport → юзер выбирает .sqlplan файл или вставляет XML
 *   2. backend.planAnalyzerAnalyzeFile/Xml → PerformanceStudio CLI
 *   3. Render: PlanStats + PlanWarnings + MissingIndexes per statement
 *
 * Phase B добавит PlanVisualization (html-query-plan SSMS-style).
 * Phase C добавит AiPlanExplanationCard поверх warnings (Claude Sonnet 4.5).
 */

import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  backend,
  type PlanAnalysisResult,
  type PlanAnalyzeResponse,
  type PlanAnalyzerStatus,
} from "@/api/backend";
import { t, format } from "@/i18n/ru";
import { Icon } from "@/components/icons/Icon";
import { useAppStore } from "@/store/appStore";
import { PlanImport } from "./PlanImport";
import { PlanWarnings } from "./PlanWarnings";
import { MissingIndexes } from "./MissingIndexes";
import { PlanStats } from "./PlanStats";
import { PlanVisualization } from "./PlanVisualization";
import styles from "./PlanAnalyzer.module.css";

export function PlanAnalyzerScreen() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlanAnalysisResult | null>(null);
  const [sourceLabel, setSourceLabel] = useState<string | null>(null);
  const [status, setStatus] = useState<PlanAnalyzerStatus | null>(null);
  const [planXmlForViz, setPlanXmlForViz] = useState<string | null>(null);
  const pushToast = useAppStore((s) => s.pushToast);

  // Status check — на mount узнаём доступен ли planview.exe.
  useEffect(() => {
    backend
      .planAnalyzerStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  const handleResponse = useCallback(
    (resp: PlanAnalyzeResponse, source: string, sourceXml: string | null) => {
      if (!resp.ok || !resp.result) {
        const msg = resp.details ?? resp.error ?? "unknown error";
        setError(format(t.planAnalyzer.analysisFailed, { detail: msg }));
        setResult(null);
        return;
      }
      setError(null);
      setResult(resp.result);
      setSourceLabel(source);
      setPlanXmlForViz(sourceXml);
    },
    [],
  );

  const onPickFile = useCallback(
    async (filePath: string) => {
      setBusy(true);
      setError(null);
      try {
        // Параллельно: backend analyze + tauri read file.
        // analyze идёт через PerformanceStudio (warnings + missing_indexes),
        // raw XML нужен для html-query-plan visualization (Phase B).
        // read_plan_text_file — custom Tauri command в main.rs (Phase B).
        const [resp, rawXml] = await Promise.all([
          backend.planAnalyzerAnalyzeFile(filePath),
          invoke<string>("read_plan_text_file", { path: filePath }).catch(() => null),
        ]);
        const name = filePath.split(/[\\/]/).pop() ?? filePath;
        handleResponse(resp, name, rawXml);
        pushToast(format(t.planAnalyzer.fileImportToast, { name }), "info");
      } catch (e) {
        setError(format(t.planAnalyzer.analysisFailed, { detail: String(e) }));
      } finally {
        setBusy(false);
      }
    },
    [handleResponse, pushToast],
  );

  const onPasteXml = useCallback(
    async (xml: string) => {
      setBusy(true);
      setError(null);
      try {
        const resp = await backend.planAnalyzerAnalyzeXml(xml);
        handleResponse(resp, "pasted XML", xml);
        pushToast(format(t.planAnalyzer.pasteImportToast, { size: xml.length }), "info");
      } catch (e) {
        setError(format(t.planAnalyzer.analysisFailed, { detail: String(e) }));
      } finally {
        setBusy(false);
      }
    },
    [handleResponse, pushToast],
  );

  const summary = result?.summary;
  const binaryUnavailable = status !== null && !status.available;

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <div className={styles.titleBlock}>
          <h1 className={styles.title}>{t.planAnalyzer.pageTitle}</h1>
          <div className={styles.subtitle}>{t.planAnalyzer.description}</div>
        </div>
        {status && (
          <div className={styles.statusBlock}>
            <div>
              <span
                className={
                  status.available ? styles.statusAvailable : styles.statusUnavailable
                }
              >
                {status.available ? "● PerformanceStudio готов" : "○ planview.exe нет"}
              </span>
            </div>
            <div>{status.rules_count} правил · v1.11.2</div>
          </div>
        )}
      </div>

      {binaryUnavailable && (
        <div className={styles.binaryMissingBanner}>
          <div className={styles.binaryMissingTitle}>
            {t.planAnalyzer.binaryMissingTitle}
          </div>
          <div>{t.planAnalyzer.binaryMissingDetail}</div>
        </div>
      )}

      <div className={styles.body}>
        <PlanImport onPickFile={onPickFile} onPasteXml={onPasteXml} busy={busy} />

        {error && <div className={styles.error}>{error}</div>}

        {result && summary && (
          <div className={styles.resultArea}>
            {/* Phase B: SSMS-style visualization (html-query-plan) */}
            {planXmlForViz && <PlanVisualization planXml={planXmlForViz} />}

            <div className={styles.resultHeader}>
              <div className={styles.resultMeta}>
                <div className={styles.resultMetaLabel}>{t.planAnalyzer.sourceLabel}</div>
                <div className={styles.resultMetaValue}>
                  {sourceLabel ?? result.plan_source}
                </div>
              </div>
              {result.sql_server_version && (
                <div className={styles.resultMeta}>
                  <div className={styles.resultMetaLabel}>
                    {t.planAnalyzer.sqlServerVersionLabel}
                  </div>
                  <div className={styles.resultMetaValue}>
                    v{result.sql_server_version}
                    {result.sql_server_build ? ` build ${result.sql_server_build}` : ""}
                  </div>
                </div>
              )}
              <div className={styles.resultMeta}>
                <div className={styles.resultMetaLabel}>
                  {t.planAnalyzer.statementsLabel}
                </div>
                <div className={styles.resultMetaValue}>{summary.total_statements}</div>
              </div>
              <div className={styles.resultMeta}>
                <div className={styles.resultMetaLabel}>Сводка</div>
                <div className={styles.sevSummary}>
                  {summary.critical_warnings > 0 && (
                    <span className={`${styles.sevChip} ${styles.sevChipCritical}`}>
                      {summary.critical_warnings} критичных
                    </span>
                  )}
                  {summary.total_warnings - summary.critical_warnings > 0 && (
                    <span className={`${styles.sevChip} ${styles.sevChipWarning}`}>
                      {summary.total_warnings - summary.critical_warnings} предупр.
                    </span>
                  )}
                  {summary.missing_indexes > 0 && (
                    <span className={`${styles.sevChip} ${styles.sevChipInfo}`}>
                      {summary.missing_indexes} индексов
                    </span>
                  )}
                  {summary.total_warnings === 0 && summary.missing_indexes === 0 && (
                    <span className={`${styles.sevChip} ${styles.sevChipOK}`}>
                      Без проблем
                    </span>
                  )}
                </div>
              </div>
            </div>

            {result.statements.map((stmt, idx) => (
              <div key={idx} className={styles.statementCard}>
                <div className={styles.statementHeader}>
                  <span className={styles.statementLabel}>
                    {t.planAnalyzer.statementCardLabel} #{idx + 1} · {stmt.statement_type}
                  </span>
                </div>
                <pre className={styles.statementTextBlock}>{stmt.statement_text}</pre>
                <PlanStats statement={stmt} />
                <PlanWarnings warnings={stmt.warnings} />
                <MissingIndexes indexes={stmt.missing_indexes} />
              </div>
            ))}
          </div>
        )}

        {!result && !error && !busy && (
          <div className={styles.empty}>
            <div className={styles.emptyIcon}>
              <Icon name="FileBarChart" size={28} color="var(--o-text-mute)" />
            </div>
            <div className={styles.emptyTitle}>Импортируйте план запроса</div>
            <div className={styles.emptyHint}>
              .sqlplan файл из SSMS или XML вставкой → получите анализ за секунды
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
