/**
 * Sprint 10 — Actions: кнопки «Сбросить» и «Скачать logcfg.xml».
 * Download-only: никакого Apply locally — файл скачивается через Blob URL.
 */
import type { LogcfgConfig } from "../types";
import { serializeToXml } from "../xmlSerializer";
import styles from "./Actions.module.css";

interface Props {
  config: LogcfgConfig;
  onReset: () => void;
}

export function Actions({ config, onReset }: Props) {
  function handleDownload() {
    const xml = serializeToXml(config);
    const blob = new Blob([xml], { type: "application/xml; charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "logcfg.xml";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return (
    <div className={styles.root}>
      <button
        className={styles.btn_reset}
        onClick={onReset}
        title="Сбросить настройки к значениям по умолчанию"
      >
        Сбросить
      </button>
      <button className={styles.btn_download} onClick={handleDownload}>
        Скачать logcfg.xml
      </button>
    </div>
  );
}
