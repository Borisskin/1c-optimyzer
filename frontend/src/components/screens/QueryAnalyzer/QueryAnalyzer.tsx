import { useCallback, useEffect, useRef, useState } from "react";
import { backend, type QAAnalyzeResult, type QAFinding, type QARewriteResult, type QAStatus } from "@/api/backend";
import { t, format } from "@/i18n/ru";
import { QueryEditor } from "./QueryEditor";
import { FindingsList } from "./FindingsList";
import { RewriteDiff } from "./RewriteDiff";
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

  useEffect(() => {
    backend.queryAnalyzerStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  const onAnalyze = useCallback(async () => {
    if (!text.trim()) return;
    setError(null);
    setRewriteResult(null);
    setSelectedFinding(null);
    setAnalyzing(true);
    try {
      const r = await backend.queryAnalyzerAnalyze(text);
      setResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setAnalyzing(false);
    }
  }, [text]);

  const onClear = useCallback(() => {
    setText("");
    setResult(null);
    setRewriteResult(null);
    setError(null);
    setSelectedFinding(null);
  }, []);

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

      {/* BSL LS pivot banner — рассказываем юзеру что Sprint 4 native-only */}
      <div className={styles.banner}>{t.queryAnalyzer.bslLsBanner}</div>

      <div className={styles.body}>
        <div className={styles.editorCol}>
          <QueryEditor
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
          <div className={styles.findingsHead}>{t.queryAnalyzer.findingsTitle}</div>
          {result && (
            <FindingsList
              findings={findings}
              selectedRuleId={selectedFinding?.rule_id ?? null}
              onSelect={setSelectedFinding}
            />
          )}
          {!result && <div className={styles.findingsEmpty}>—</div>}
        </div>
      </div>

      {rewriteResult && (
        <RewriteDiff
          original={text}
          result={rewriteResult}
          onClose={() => setRewriteResult(null)}
        />
      )}
    </div>
  );
}
