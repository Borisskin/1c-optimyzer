import { useCallback, useEffect, useRef, useState } from "react";
import {
  backend,
  type BslLsAnalyzeResult,
  type QAAnalyzeResult,
  type QAFinding,
  type QARewriteResult,
  type QAStatus,
} from "@/api/backend";
import { cloud, type AiExplainResponse } from "@/api/cloud";
import { t, format } from "@/i18n/ru";
import { useAppStore } from "@/store/appStore";
import { QueryEditor, type QueryEditorHandle } from "./QueryEditor";
import { FindingsList } from "./FindingsList";
import { RewriteDiff } from "./RewriteDiff";
import { ConfigurationBadge } from "./ConfigurationBadge";
import { ConfigurationDialog } from "./ConfigurationDialog";
import { BslLsFindings } from "./BslLsFindings";
import { AiExplanationCard } from "./AiExplanationCard";
import styles from "./QueryAnalyzer.module.css";

export function QueryAnalyzerScreen() {
  const [text, setText] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [result, setResult] = useState<QAAnalyzeResult | null>(null);
  const [rewriteResult, setRewriteResult] = useState<QARewriteResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<QAFinding | null>(null);
  const [status, setStatus] = useState<QAStatus | null>(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const editorRef = useRef<QueryEditorHandle | null>(null);
  const configStatus = useAppStore((s) => s.configurationStatus);

  // Sprint 6 — bsl-language-server + cloud AI state.
  const [bslLsResult, setBslLsResult] = useState<BslLsAnalyzeResult | null>(null);
  const [aiResult, setAiResult] = useState<AiExplainResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const refreshAnalyzerStatus = useCallback(() => {
    backend.queryAnalyzerStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    refreshAnalyzerStatus();
  }, [refreshAnalyzerStatus]);

  // Перезагружаем status анализатора когда меняется подключение конфигурации
  // (configuration_connected живёт в QAStatus, нужен для display).
  useEffect(() => {
    refreshAnalyzerStatus();
  }, [configStatus, refreshAnalyzerStatus]);

  const onFindingSelect = useCallback((f: QAFinding) => {
    setSelectedFinding(f);
    editorRef.current?.scrollToRange(f.line_start, f.col_start, f.line_end, f.col_end);
  }, []);

  const onAnalyze = useCallback(async () => {
    if (!text.trim()) return;
    setError(null);
    setRewriteResult(null);
    setSelectedFinding(null);
    setAnalyzing(true);
    setBslLsResult(null);
    setAiResult(null);
    setAiError(null);
    try {
      // Sprint 6: запускаем legacy regex-валидатор + bsl-LS параллельно.
      const [legacy, bslLs] = await Promise.allSettled([
        backend.queryAnalyzerAnalyze(text),
        backend.bslLsAnalyze(text),
      ]);
      if (legacy.status === "fulfilled") {
        setResult(legacy.value);
      } else {
        setError(String(legacy.reason));
      }
      if (bslLs.status === "fulfilled") {
        setBslLsResult(bslLs.value);
        // Sprint 6: автоматический AI explain если есть grouped diagnostics.
        if (bslLs.value.ok && bslLs.value.grouped && bslLs.value.grouped.length > 0) {
          void requestAiExplanation(text, bslLs.value);
        }
      } else {
        setBslLsResult({ ok: false, error: "bsl_ls_unavailable", details: String(bslLs.reason) });
      }
    } finally {
      setAnalyzing(false);
    }
  }, [text]);

  const requestAiExplanation = useCallback(
    async (sdbl: string, bsl: BslLsAnalyzeResult) => {
      if (!bsl.diagnostics) return;
      setAiLoading(true);
      setAiError(null);
      try {
        const ai = await cloud.aiExplain({
          query_sdbl: sdbl,
          diagnostics: bsl.diagnostics.map((d) => ({
            code: d.code,
            message: d.message,
            severity: d.severity,
            range_start_line: d.range.start.line,
            range_start_char: d.range.start.character,
            range_end_line: d.range.end.line,
            range_end_char: d.range.end.character,
            snippet: d.snippet ?? "",
          })),
          configuration_context: undefined,
        });
        setAiResult(ai);
      } catch (e) {
        setAiError(String(e));
      } finally {
        setAiLoading(false);
      }
    },
    [],
  );

  const onClear = useCallback(() => {
    setText("");
    setResult(null);
    setRewriteResult(null);
    setError(null);
    setSelectedFinding(null);
    setBslLsResult(null);
    setAiResult(null);
    setAiError(null);
  }, []);

  const onAcceptRewrite = useCallback(
    (sdbl: string) => {
      setText(sdbl);
      // Clear previous results — new query needs fresh analysis.
      setResult(null);
      setBslLsResult(null);
      setAiResult(null);
    },
    [],
  );

  const onJumpToRange = useCallback(
    (startLine: number, startChar: number, endLine: number, endChar: number) => {
      editorRef.current?.scrollToRange(startLine, startChar, endLine, endChar);
    },
    [],
  );

  const onRewrite = useCallback(async () => {
    if (!result || !text.trim()) return;
    setRewriting(true);
    setError(null);
    try {
      const r = await backend.queryAnalyzerRewrite(text, result.findings);
      if (!r.ok) {
        setError(r.error || "AI rewriter failed");
        return;
      }
      setRewriteResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setRewriting(false);
    }
  }, [text, result]);

  const findings = result?.findings ?? [];
  const summary = result?.summary;
  const aiEnabled = status?.ai_enabled ?? false;
  const canRewrite = aiEnabled && result !== null && text.trim().length > 0;

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>{t.queryAnalyzer.pageTitle}</h1>
          <div className={styles.subtitle}>{t.queryAnalyzer.description}</div>
        </div>
        <div className={styles.headerRight}>
          <ConfigurationBadge onClick={() => setConfigDialogOpen(true)} />
          {status && (
            <div className={styles.statusBlock}>
              <div className={styles.statusLine}>
                {format(t.queryAnalyzer.rulesLoaded, { count: status.native_rules_count })}
              </div>
              {!aiEnabled && (
                <div className={styles.statusWarn}>
                  {t.queryAnalyzer.rewriteAiNotConfigured}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className={styles.body}>
        <div className={styles.editorCol}>
          <QueryEditor
            ref={editorRef}
            value={text}
            onChange={setText}
            findings={findings}
            placeholder={t.queryAnalyzer.placeholder}
          />
          <div className={styles.actions}>
            <button
              className={styles.btnPrimary}
              onClick={onAnalyze}
              disabled={!text.trim() || analyzing}
            >
              {analyzing ? t.queryAnalyzer.analyzing : t.queryAnalyzer.analyze}
            </button>
            <button
              className={styles.btnSecondary}
              onClick={onClear}
              disabled={analyzing || !text}
            >
              {t.queryAnalyzer.clear}
            </button>
            <button
              className={styles.btnAi}
              onClick={onRewrite}
              disabled={!canRewrite || rewriting}
              title={!aiEnabled ? t.queryAnalyzer.rewriteAiNotConfigured : undefined}
            >
              {rewriting ? t.queryAnalyzer.rewriting : t.queryAnalyzer.rewriteAi}
            </button>
            {summary && (
              <span className={styles.summaryText}>
                {format(t.queryAnalyzer.summary, summary)}
              </span>
            )}
          </div>
          {error && <div className={styles.error}>{format(t.queryAnalyzer.error, { detail: error })}</div>}
        </div>

        <div className={styles.findingsCol}>
          {/* Sprint 6: bsl-language-server findings (главный premium-feature) */}
          {(bslLsResult || analyzing) && (
            <BslLsFindings
              result={bslLsResult}
              loading={analyzing}
              onSelectRange={onJumpToRange}
            />
          )}

          {/* Sprint 6: AI structured explanation от Claude Sonnet */}
          {(aiResult || aiLoading || aiError) && (
            <div className={styles.aiSlot}>
              <AiExplanationCard
                response={aiResult}
                loading={aiLoading}
                error={aiError}
                onAcceptRewrite={onAcceptRewrite}
              />
            </div>
          )}

          {/* Sprint 4 legacy regex findings (secondary, для backwards compat) */}
          {result && findings.length > 0 && (
            <details className={styles.legacyFindings}>
              <summary>{t.queryAnalyzer.findingsTitle} (regex-валидатор)</summary>
              <FindingsList
                findings={findings}
                selectedRuleId={selectedFinding?.rule_id ?? null}
                onSelect={onFindingSelect}
              />
            </details>
          )}

          {!result && !bslLsResult && !analyzing && (
            <div className={styles.findingsEmpty}>
              Вставьте SDBL запрос и нажмите «Анализировать»
            </div>
          )}
        </div>
      </div>

      {rewriteResult && (
        <RewriteDiff
          original={text}
          result={rewriteResult}
          onClose={() => setRewriteResult(null)}
        />
      )}

      <ConfigurationDialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
      />
    </div>
  );
}
