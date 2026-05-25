/**
 * Sprint 10 — Actions: кнопки «Сбросить» и «Скачать logcfg.xml».
 * Download-only: никакого Apply locally — файл скачивается через Blob URL.
 * После скачивания показывается inline-banner «Что делать дальше».
 */
import { useState } from "react";
import type { LogcfgConfig } from "../types";
import { serializeToXml } from "../xmlSerializer";
import styles from "./Actions.module.css";

interface Props {
  config: LogcfgConfig;
  onReset: () => void;
}

export function Actions({ config, onReset }: Props) {
  const [downloaded, setDownloaded] = useState(false);

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
    setDownloaded(true);
  }

  return (
    <div className={styles.root}>
      <div className={styles.buttons}>
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

      {downloaded && (
        <div className={styles.next_steps}>
          <div className={styles.next_steps_title}>Скачано logcfg.xml</div>
          <ol className={styles.steps_list}>
            <li>Скопируйте файл в папку conf\ на сервере 1С (рядом с ragent.exe)</li>
            <li>Перезапустите службу «1C:Enterprise Server Agent»</li>
            <li>Проведите тестовый сценарий с проблемой (10–30 минут)</li>
            <li>Остановите сбор — удалите logcfg.xml и снова перезапустите агент</li>
            <li>Загрузите папку с логами в Optimyzer для анализа</li>
          </ol>
        </div>
      )}
    </div>
  );
}
