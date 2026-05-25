/**
 * Sprint 10 — XmlPreview: real-time предпросмотр logcfg.xml.
 * Обновляется при каждом изменении config. Кнопка «Копировать» для
 * быстрого копирования XML в буфер обмена.
 */
import { useMemo, useState, useCallback } from "react";
import type { LogcfgConfig } from "../types";
import { serializeToXml } from "../xmlSerializer";
import styles from "./XmlPreview.module.css";

interface Props {
  config: LogcfgConfig;
}

export function XmlPreview({ config }: Props) {
  const xml = useMemo(() => serializeToXml(config), [config]);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(xml);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard недоступен — ничего не делаем
    }
  }, [xml]);

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <span className={styles.title}>XML-предпросмотр</span>
        <button
          className={[
            styles.copy_btn,
            copied ? styles.copy_btn_copied : "",
          ].join(" ")}
          onClick={handleCopy}
          title="Скопировать XML в буфер обмена"
        >
          {copied ? "Скопировано" : "Копировать"}
        </button>
      </div>
      <pre className={styles.code}>{xml}</pre>
    </div>
  );
}
