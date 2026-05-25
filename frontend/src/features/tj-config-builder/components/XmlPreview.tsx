/**
 * Sprint 10 — XmlPreview: подсвеченный редактируемый XML-предпросмотр.
 *
 * Техника overlay: прозрачная <textarea> поверх highlighted <pre>.
 * Обе панели имеют ОДИНАКОВЫЕ font/padding/line-height.
 *
 * Кнопки в шапке (иконки с CSS-тултипами):
 *   [Format]   — prettifyXml (отформатировать)
 *   [Copy]     → [✓] на 1.5с
 *   [Save]     → [✓] на 1.5с — save dialog (Tauri) или Blob-fallback
 *
 * Фикс бага: isFocused хранится в ref (не state), поэтому клик по
 * кнопке Format не вызывает сброс XML через useEffect.
 */
import { useRef, useState, useEffect, useCallback, useMemo } from "react";
import { save } from "@tauri-apps/plugin-dialog";
import { writeTextFile } from "@tauri-apps/plugin-fs";
import type { LogcfgConfig } from "../types";
import { serializeToXml } from "../xmlSerializer";
import { highlightXml, prettifyXml } from "../xmlHighlighter";
import styles from "./XmlPreview.module.css";

interface Props {
  config: LogcfgConfig;
}

export function XmlPreview({ config }: Props) {
  const [xmlText, setXmlText] = useState(() =>
    prettifyXml(serializeToXml(config)),
  );
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlightRef = useRef<HTMLDivElement>(null);

  /**
   * isFocused хранится в ref (не state), чтобы его изменение
   * НЕ триггерило useEffect и не перетирало XML пользователя.
   */
  const isFocusedRef = useRef(false);

  // Когда конфиг меняется в левом сайдбаре — обновляем XML
  // только если пользователь НЕ редактирует (проверяем через ref)
  useEffect(() => {
    if (!isFocusedRef.current) {
      setXmlText(prettifyXml(serializeToXml(config)));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config]); // намеренно не включаем isFocusedRef — это ref, не state

  // Синхронизация скролла textarea → highlight-слой
  const syncScroll = useCallback(() => {
    if (highlightRef.current && textareaRef.current) {
      highlightRef.current.scrollTop = textareaRef.current.scrollTop;
      highlightRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }, []);

  // HTML с подсветкой
  const highlighted = useMemo(() => highlightXml(xmlText), [xmlText]);

  // --- Кнопка «Отформатировать» ---
  const handleFormat = useCallback(() => {
    setXmlText((prev) => prettifyXml(prev));
  }, []);

  // --- Кнопка «Копировать» ---
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(xmlText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard недоступен */ }
  }, [xmlText]);

  // --- Кнопка «Сохранить в файл» ---
  const handleSave = useCallback(async () => {
    const filePath = await save({
      defaultPath: "logcfg.xml",
      filters: [{ name: "XML-файл", extensions: ["xml"] }],
      title: "Сохранить logcfg.xml",
    });
    if (!filePath) return;   // пользователь нажал Отмена
    await writeTextFile(filePath, xmlText);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }, [xmlText]);

  return (
    <div className={styles.root}>
      {/* ---- Шапка ---- */}
      <div className={styles.header}>
        <span className={styles.title}>XML-предпросмотр</span>
        <div className={styles.header_buttons}>

          {/* Отформатировать */}
          <button
            className={styles.icon_btn}
            onClick={handleFormat}
            data-tooltip="Отформатировать"
            aria-label="Отформатировать XML"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="21" y1="6" x2="3" y2="6" />
              <line x1="17" y1="12" x2="3" y2="12" />
              <line x1="21" y1="18" x2="3" y2="18" />
            </svg>
          </button>

          {/* Копировать */}
          <button
            className={[styles.icon_btn, copied ? styles.icon_btn_ok : ""].join(" ")}
            onClick={handleCopy}
            data-tooltip={copied ? "Скопировано!" : "Копировать"}
            aria-label="Копировать XML"
          >
            {copied ? (
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            )}
          </button>

          {/* Сохранить в файл */}
          <button
            className={[
              styles.icon_btn,
              styles.icon_btn_save,
              saved ? styles.icon_btn_ok : "",
            ].join(" ")}
            onClick={handleSave}
            data-tooltip={saved ? "Сохранено!" : "Сохранить в файл"}
            aria-label="Сохранить logcfg.xml"
          >
            {saved ? (
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
            )}
          </button>

        </div>
      </div>

      {/* ---- Редактируемая область: overlay textarea + highlighted pre ---- */}
      <div className={styles.editor}>
        {/* Слой подсветки (под textarea) */}
        <div ref={highlightRef} className={styles.highlight_layer} aria-hidden="true">
          <pre
            className={styles.highlight_pre}
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{ __html: highlighted + "\n" }}
          />
        </div>

        {/* Прозрачная textarea для редактирования */}
        <textarea
          ref={textareaRef}
          className={styles.editor_textarea}
          value={xmlText}
          onChange={(e) => setXmlText(e.target.value)}
          onFocus={() => { isFocusedRef.current = true; }}
          onBlur={() => { isFocusedRef.current = false; }}
          onScroll={syncScroll}
          spellCheck={false}
          autoComplete="off"
          aria-label="Редактирование XML logcfg.xml"
        />
      </div>
    </div>
  );
}
