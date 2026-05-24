/**
 * Sprint 7 Phase A — импорт .sqlplan файла или paste plan XML.
 *
 * UI: два режима через tabs.
 *   1. "Файл" — Tauri dialog picker (frontend/src-tauri/dragDrop тоже работает,
 *      обрабатывается через listen('tauri://drag-drop') на уровне screen).
 *   2. "XML" — textarea для paste plan XML напрямую.
 */

import { useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { Icon } from "@/components/icons/Icon";
import { t } from "@/i18n/ru";
import styles from "./PlanAnalyzer.module.css";

type Tab = "file" | "paste";

interface Props {
  onPickFile: (filePath: string) => void;
  onPasteXml: (xml: string) => void;
  busy: boolean;
}

export function PlanImport({ onPickFile, onPasteXml, busy }: Props) {
  const [tab, setTab] = useState<Tab>("file");
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
          onClick={() => setTab("file")}
        >
          {t.planAnalyzer.importTabFile}
        </button>
        <button
          type="button"
          className={`${styles.tab} ${tab === "paste" ? styles.tabActive : ""}`}
          onClick={() => setTab("paste")}
        >
          {t.planAnalyzer.importTabPaste}
        </button>
      </div>

      {tab === "file" ? (
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
      ) : (
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
    </div>
  );
}
