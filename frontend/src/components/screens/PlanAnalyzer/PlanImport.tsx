/**
 * Sprint 7 Phase A+D — импорт .sqlplan файла, paste plan XML, или импорт
 * текстового плана из загруженного архива ТЖ (DBMSSQL.planSQLText).
 *
 * UI: три режима через tabs.
 *   1. "Файл" — Tauri dialog picker (XML format → PerformanceStudio CLI + viz)
 *   2. "XML" — textarea для paste plan XML напрямую (XML format → same)
 *   3. "Из архива ТЖ" — список DBMSSQL событий из загруженного архива с plan_text
 *      (text format → пропускаем CLI, только text view + AI explanation)
 */

import { useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { Icon } from "@/components/icons/Icon";
import { t } from "@/i18n/ru";
import styles from "./PlanAnalyzer.module.css";
import { PlanTjImport } from "./PlanTjImport";

type Tab = "file" | "paste" | "tj";

interface TjPlanPayload {
  event_id: number;
  sql_text: string;
  plan_text: string;
  ts: string | null;
  duration_us: number | null;
  context: string | null;
}

interface Props {
  onPickFile: (filePath: string) => void;
  onPasteXml: (xml: string) => void;
  onPickTjPlan: (payload: TjPlanPayload) => void;
  onTabChange?: (tab: "file" | "paste" | "tj") => void;
  busy: boolean;
}

export function PlanImport({ onPickFile, onPasteXml, onPickTjPlan, onTabChange, busy }: Props) {
  const [tab, setTab] = useState<Tab>("file");

  const switchTab = (t: Tab) => {
    setTab(t);
    onTabChange?.(t);
  };
  const [pasteText, setPasteText] = useState("");
  const [pickError, setPickError] = useState<string | null>(null);

  const onPick = async () => {
    setPickError(null);
    try {
      const selected = await openDialog({
        multiple: false,
        directory: false,
        filters: [{ name: "SQL Server Plan", extensions: ["sqlplan", "xml"] }],
      });
      if (typeof selected === "string" && selected) {
        onPickFile(selected);
      }
    } catch (e) {
      setPickError(String(e));
    }
  };

  const onPasteAnalyze = () => {
    const xml = pasteText.trim();
    if (!xml) return;
    onPasteXml(xml);
  };

  return (
    <div className={styles.importCard}>
      <div className={styles.tabs}>
        <button
          type="button"
          className={`${styles.tab} ${tab === "file" ? styles.tabActive : ""}`}
          onClick={() => switchTab("file")}
        >
          {t.planAnalyzer.importTabFile}
        </button>
        <button
          type="button"
          className={`${styles.tab} ${tab === "paste" ? styles.tabActive : ""}`}
          onClick={() => switchTab("paste")}
        >
          {t.planAnalyzer.importTabPaste}
        </button>
        <button
          type="button"
          className={`${styles.tab} ${tab === "tj" ? styles.tabActive : ""}`}
          onClick={() => switchTab("tj")}
        >
          Из архива ТЖ
        </button>
      </div>

      {tab === "file" && (
        <div className={styles.fileTab}>
          <button
            type="button"
            className={styles.pickButton}
            onClick={onPick}
            disabled={busy}
            title={t.planAnalyzer.pickFileFromDialog}
          >
            <Icon name="Upload" size={14} />
            {t.planAnalyzer.pickFileButton}
          </button>
          <div className={styles.pickHint}>{t.planAnalyzer.pickFileHint}</div>
          {pickError && <div className={styles.error}>{pickError}</div>}
        </div>
      )}

      {tab === "paste" && (
        <div className={styles.pasteTab}>
          <textarea
            className={styles.pasteArea}
            placeholder={t.planAnalyzer.pasteAreaPlaceholder}
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            disabled={busy}
            spellCheck={false}
          />
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.btnPrimary}
              onClick={onPasteAnalyze}
              disabled={busy || pasteText.trim().length === 0}
            >
              {busy ? t.planAnalyzer.analyzing : t.planAnalyzer.analyze}
            </button>
            <button
              type="button"
              className={styles.btnSecondary}
              onClick={() => setPasteText("")}
              disabled={busy || pasteText.length === 0}
            >
              {t.planAnalyzer.clear}
            </button>
          </div>
        </div>
      )}

      {tab === "tj" && <PlanTjImport onPick={onPickTjPlan} busy={busy} />}
    </div>
  );
}
