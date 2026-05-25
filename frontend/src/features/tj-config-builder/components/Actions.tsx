/**
 * Sprint 10 — Actions: кнопки «Сбросить» и «Скачать logcfg.xml».
 * Использует Tauri plugin-dialog save() + plugin-fs writeTextFile() чтобы
 * пользователь сам выбрал путь сохранения. Fallback на Blob URL если
 * Tauri API недоступен (например, в dev-browser режиме).
 * После сохранения показывается inline-banner «Что делать дальше».
 */
import { useState } from "react";
import { save } from "@tauri-apps/plugin-dialog";
import { writeTextFile } from "@tauri-apps/plugin-fs";
import type { LogcfgConfig } from "../types";
import { serializeToXml } from "../xmlSerializer";
import styles from "./Actions.module.css";

interface Props {
  config: LogcfgConfig;
  onReset: () => void;
}

export function Actions({ config, onReset }: Props) {
  const [downloaded, setDownloaded] = useState(false);

  async function handleDownload() {
    const xml = serializeToXml(config);
    try {
      // Tauri save dialog — пользователь выбирает куда сохранить
      const filePath = await save({
        defaultPath: "logcfg.xml",
        filters: [{ name: "XML-файл", extensions: ["xml"] }],
        title: "Сохранить logcfg.xml",
      });
      if (!filePath) return; // пользователь нажал «Отмена»
      await writeTextFile(filePath, xml);
      setDownloaded(true);
    } catch {
      // Fallback на Blob download (dev-browser / WebView без plugin-dialog)
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
