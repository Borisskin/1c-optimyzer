import { useState } from "react";
import type { QARewriteResult } from "@/api/backend";
import { t } from "@/i18n/ru";
import styles from "./RewriteDiff.module.css";

interface Props {
  original: string;
  result: QARewriteResult;
  onClose: () => void;
}

export function RewriteDiff({ original, result, onClose }: Props) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    if (!result.rewritten_query) return;
    try {
      await navigator.clipboard.writeText(result.rewritten_query);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard может быть недоступен — игнорируем
    }
  }

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.head}>
          <h2 className={styles.title}>{t.queryAnalyzer.rewriteAi}</h2>
          {result.from_cache && (
            <span className={styles.cacheBadge}>{t.queryAnalyzer.rewriteFromCache}</span>
          )}
          <button className={styles.closeBtn} onClick={onClose}>
            ×
          </button>
        </div>

        <div className={styles.cols}>
          <div className={styles.col}>
            <div className={styles.colHead}>{t.queryAnalyzer.rewriteOriginal}</div>
            <pre className={styles.code}>{original}</pre>
          </div>
          <div className={styles.col}>
            <div className={styles.colHead}>
              {t.queryAnalyzer.rewriteRewritten}
              <button className={styles.copyBtn} onClick={copy}>
                {copied ? t.queryAnalyzer.rewriteCopied : t.queryAnalyzer.rewriteCopy}
              </button>
            </div>
            <pre className={styles.code}>{result.rewritten_query || ""}</pre>
          </div>
        </div>

        {(result.changes?.length ?? 0) > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionHead}>{t.queryAnalyzer.rewriteChanges}</div>
            <ul className={styles.changes}>
              {result.changes!.map((c, i) => (
                <li key={i} className={styles.changeItem}>
                  <div className={styles.changeWhat}>{c.what}</div>
                  <div className={styles.changeWhy}>{c.why}</div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {result.estimated_improvement && (
          <div className={styles.section}>
            <div className={styles.sectionHead}>{t.queryAnalyzer.rewriteEstimated}</div>
            <div className={styles.sectionBody}>{result.estimated_improvement}</div>
          </div>
        )}

        {result.notes_for_developer && (
          <div className={styles.section}>
            <div className={styles.sectionHead}>{t.queryAnalyzer.rewriteNotes}</div>
            <div className={styles.sectionBody}>{result.notes_for_developer}</div>
          </div>
        )}

        <div className={styles.foot}>
          <button className={styles.btnSecondary} onClick={onClose}>
            {t.queryAnalyzer.rewriteClose}
          </button>
        </div>
      </div>
    </div>
  );
}
