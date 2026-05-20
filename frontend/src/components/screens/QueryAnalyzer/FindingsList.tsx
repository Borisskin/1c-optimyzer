import type { QAFinding } from "@/api/backend";
import { t, format } from "@/i18n/ru";
import styles from "./FindingsList.module.css";

interface Props {
  findings: QAFinding[];
  selectedRuleId: string | null;
  onSelect: (f: QAFinding) => void;
}

export function FindingsList({ findings, selectedRuleId, onSelect }: Props) {
  if (findings.length === 0) {
    return <div className={styles.empty}>{t.queryAnalyzer.noFindings}</div>;
  }
  return (
    <div className={styles.list}>
      {findings.map((f, i) => {
        const isSelected = f.rule_id === selectedRuleId;
        const lineLabel =
          f.line_start === f.line_end
            ? `${t.queryAnalyzer.line} ${f.line_start}`
            : `${t.queryAnalyzer.lines} ${f.line_start}–${f.line_end}`;
        return (
          <button
            key={`${f.rule_id}-${i}-${f.line_start}-${f.col_start}`}
            className={`${styles.item} ${isSelected ? styles.itemSelected : ""}`}
            onClick={() => onSelect(f)}
          >
            <div className={styles.itemHead}>
              <span className={`${styles.sev} ${styles[`sev_${f.severity}`]}`}>
                {t.queryAnalyzer.severity[f.severity]}
              </span>
              <span className={styles.cat}>· {t.queryAnalyzer.category[f.category]}</span>
              <span className={styles.line}>{lineLabel}</span>
            </div>
            <div className={styles.itemTitle}>{f.message}</div>
            <div className={styles.itemBody}>
              <pre className={styles.bodyPre}>{firstParagraph(f.explanation_md)}</pre>
            </div>
            {f.tags.length > 0 && (
              <div className={styles.tags}>
                {f.tags.map((tag) => (
                  <span key={tag} className={styles.tag}>{tag}</span>
                ))}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}

function firstParagraph(md: string): string {
  // Берём первый параграф markdown тела (после заголовка). Заголовок начинается
  // с `# Title` — пропускаем. Затем берём текст до следующего `## ` или конца.
  const lines = md.split("\n");
  const out: string[] = [];
  let inBody = false;
  for (const line of lines) {
    if (!inBody) {
      if (line.startsWith("# ")) {
        inBody = true;
        continue;
      }
      continue;
    }
    if (line.startsWith("## ")) break;
    out.push(line);
    if (out.join("\n").trim().length > 200) break;
  }
  const text = out.join("\n").trim();
  return text.slice(0, 300) + (text.length > 300 ? "…" : "");
}
