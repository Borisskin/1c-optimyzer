/**
 * Sprint 10 — XmlPreview: подсвеченный редактируемый XML-предпросмотр.
 *
 * Техника: transparent textarea overlay поверх highlighted <pre>.
 * Обе панели имеют одинаковые font/padding/line-height — текст совпадает пиксельно.
 * Пользователь редактирует через textarea, подсветка обновляется в реальном времени.
 * При изменении config снаружи (пока не в фокусе) — XML перерисовывается.
 */
import { useRef, useState, useEffect, useCallback, useMemo } from "react";
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
  const [isFocused, setIsFocused] = useState(false);
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlightRef = useRef<HTMLDivElement>(null);

  // Когда config меняется снаружи — обновляем XML (только если не в фокусе)
  useEffect(() => {
    if (!isFocused) {
      setXmlText(prettifyXml(serializeToXml(config)));
    }
  }, [config, isFocused]);

  // Синхронизация скролла textarea → highlight-слой
  const syncScroll = useCallback(() => {
    if (highlightRef.current && textareaRef.current) {
      highlightRef.current.scrollTop = textareaRef.current.scrollTop;
      highlightRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }, []);

  // HTML с подсветкой — пересчитывается только при изменении текста
  const highlighted = useMemo(() => highlightXml(xmlText), [xmlText]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(xmlText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard недоступен */
    }
  }, [xmlText]);

  const handleFormat = useCallback(() => {
    setXmlText(prettifyXml(xmlText));
  }, [xmlText]);

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <span className={styles.title}>XML-предпросмотр</span>
        <div className={styles.header_buttons}>
          {/* Кнопка «Отформатировать XML» */}
          <button
            className={styles.icon_btn}
            onClick={handleFormat}
            title="Отформатировать XML"
            aria-label="Отформатировать XML"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="21" y1="6" x2="3" y2="6" />
              <line x1="17" y1="12" x2="3" y2="12" />
              <line x1="21" y1="18" x2="3" y2="18" />
            </svg>
          </button>

          {/* Кнопка «Копировать» с тултипом */}
          <button
            className={[styles.icon_btn, copied ? styles.icon_btn_ok : ""].join(" ")}
            onClick={handleCopy}
            title={copied ? "Скопировано!" : "Копировать XML"}
            aria-label="Копировать XML"
          >
            {copied ? (
              /* Галочка */
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              /* Иконка копирования */
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Редактируемая область: overlay textarea поверх highlighted pre */}
      <div className={styles.editor}>
        {/* Слой подсветки (под textarea) */}
        <div
          ref={highlightRef}
          className={styles.highlight_layer}
          aria-hidden="true"
        >
          <pre
            className={styles.highlight_pre}
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{ __html: highlighted + "\n" }}
          />
        </div>

        {/* Прозрачная textarea для редактирования (поверх) */}
        <textarea
          ref={textareaRef}
          className={styles.editor_textarea}
          value={xmlText}
          onChange={(e) => setXmlText(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onScroll={syncScroll}
          spellCheck={false}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          aria-label="XML logcfg.xml"
        />
      </div>
    </div>
  );
}
