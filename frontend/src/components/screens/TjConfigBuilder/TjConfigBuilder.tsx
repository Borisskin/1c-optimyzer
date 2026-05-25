/**
 * Sprint 10 — TjConfigBuilder: экран «Конструктор logcfg.xml».
 *
 * Структура:
 *   • Шапка с заголовком + badge версии платформы 1С
 *   • TemplatesSelector — горизонтальные chips 6 встроенных шаблонов
 *   • Два таба: Графический конструктор / AI-мастер
 *   • Каждый таб работает с единым state `config: LogcfgConfig`
 */
import { useState, useEffect, useCallback } from "react";
import type { LogcfgConfig, Template } from "@/features/tj-config-builder/types";
import { DEFAULT_LOGCFG_CONFIG } from "@/features/tj-config-builder/types";
import { BUILTIN_TEMPLATES } from "@/features/tj-config-builder/templates";
import { TemplatesSelector } from "@/features/tj-config-builder/components/TemplatesSelector";
import { GraphicalBuilderTab } from "@/features/tj-config-builder/components/GraphicalBuilderTab";
import { AiWizardTab } from "@/features/tj-config-builder/components/AiWizardTab";
import { backend } from "@/api/backend";
import styles from "./TjConfigBuilder.module.css";

type ActiveTab = "builder" | "ai";

export function TjConfigBuilderScreen() {
  const [config, setConfig] = useState<LogcfgConfig>({ ...DEFAULT_LOGCFG_CONFIG });
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("ai");

  // Определяем версию платформы при монтировании (best-effort, не блокирует UI)
  const [platformVersion, setPlatformVersion] = useState<string | null>(null);
  const [platformConfidence, setPlatformConfidence] = useState<
    "high" | "medium" | "low" | null
  >(null);

  useEffect(() => {
    backend
      .logcfgDetectPlatform()
      .then(({ version, confidence }) => {
        setPlatformVersion(version);
        setPlatformConfidence(confidence);
      })
      .catch(() => {
        // Best-effort — не показываем ошибку, просто не показываем badge
      });
  }, []);

  // Выбор шаблона — загружаем его конфиг
  const handleSelectTemplate = useCallback((template: Template) => {
    setActiveTemplateId(template.id);
    setConfig({ ...template.config });
  }, []);

  // Изменение конфига из GraphicalBuilderTab — сбрасываем привязку к шаблону
  const handleConfigChange = useCallback((newConfig: LogcfgConfig) => {
    setConfig(newConfig);
    setActiveTemplateId(null); // пользователь ушёл от шаблона
  }, []);

  // AI Wizard применил конфиг → переключаемся на builder таб
  const handleAiApply = useCallback((aiConfig: LogcfgConfig) => {
    setConfig(aiConfig);
    setActiveTemplateId(null);
    setActiveTab("builder");
  }, []);

  return (
    <div className={styles.root}>
      {/* Шапка */}
      <div className={styles.header}>
        <div className={styles.title}>Конструктор logcfg.xml</div>
        <div className={styles.subtitle}>
          Настройте технологический журнал 1С и скачайте готовый logcfg.xml
        </div>
        {platformVersion && (
          <div className={styles.platform_badge}>
            <span
              className={[
                styles.platform_dot,
                platformConfidence === "low" ? styles.platform_dot_low : "",
              ].join(" ")}
            />
            1С:Предприятие {platformVersion}
            {platformConfidence === "low" && " (предположительно)"}
          </div>
        )}
      </div>

      {/* Шаблоны */}
      <TemplatesSelector
        templates={BUILTIN_TEMPLATES}
        activeId={activeTemplateId}
        onSelect={handleSelectTemplate}
      />

      <hr className={styles.divider} />

      {/* Табы */}
      <div className={styles.tabs}>
        <button
          className={[
            styles.tab,
            activeTab === "ai" ? styles.tab_active : "",
          ].join(" ")}
          onClick={() => setActiveTab("ai")}
        >
          AI-мастер
        </button>
        <button
          className={[
            styles.tab,
            activeTab === "builder" ? styles.tab_active : "",
          ].join(" ")}
          onClick={() => setActiveTab("builder")}
        >
          Графический конструктор
        </button>
      </div>

      {/* Контент таба */}
      <div className={styles.content}>
        {activeTab === "builder" && (
          <GraphicalBuilderTab config={config} onChange={handleConfigChange} />
        )}
        {activeTab === "ai" && (
          <AiWizardTab
            platformVersion={platformVersion}
            onApply={handleAiApply}
          />
        )}
      </div>
    </div>
  );
}
