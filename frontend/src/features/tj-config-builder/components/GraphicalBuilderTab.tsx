/**
 * Sprint 10 — GraphicalBuilderTab: сайдбар настроек + доминирующий XML-предпросмотр.
 *
 * Layout:
 *   Левая колонка (300px, overflow-y: auto): все настройки + объём + кнопки
 *   Правая область (flex: 1): XML-предпросмотр на весь оставшийся экран
 */
import { useCallback } from "react";
import type { EventType, LogcfgConfig } from "../types";
import { DEFAULT_LOGCFG_CONFIG } from "../types";
import { EventsGroup } from "./EventsGroup";
import { PlansToggle } from "./PlansToggle";
import { StorageSettings } from "./StorageSettings";
import { VolumePreview } from "./VolumePreview";
import { Actions } from "./Actions";
import { XmlPreview } from "./XmlPreview";
import styles from "./GraphicalBuilderTab.module.css";

interface Props {
  config: LogcfgConfig;
  onChange: (config: LogcfgConfig) => void;
}

export function GraphicalBuilderTab({ config, onChange }: Props) {
  const handleToggle = useCallback(
    (type: EventType) => {
      const prev = config.events[type];
      onChange({
        ...config,
        events: {
          ...config.events,
          [type]: {
            enabled: !(prev?.enabled ?? false),
            threshold_cs: prev?.threshold_cs ?? null,
          },
        },
      });
    },
    [config, onChange],
  );

  const handleThresholdChange = useCallback(
    (type: EventType, value: number | null) => {
      onChange({
        ...config,
        events: {
          ...config.events,
          [type]: {
            ...(config.events[type] ?? { enabled: true }),
            threshold_cs: value,
          },
        },
      });
    },
    [config, onChange],
  );

  const handlePlansChange = useCallback(
    (value: boolean) => {
      onChange({ ...config, capture_plans: value });
    },
    [config, onChange],
  );

  const handleDirectoryChange = useCallback(
    (value: string) => {
      onChange({ ...config, log_directory: value });
    },
    [config, onChange],
  );

  const handleHistoryChange = useCallback(
    (value: number) => {
      onChange({ ...config, history_hours: value });
    },
    [config, onChange],
  );

  const handleReset = useCallback(() => {
    onChange({ ...DEFAULT_LOGCFG_CONFIG });
  }, [onChange]);

  return (
    <div className={styles.root}>
      {/* Левый сайдбар: все настройки */}
      <div className={styles.left}>
        <EventsGroup
          config={config}
          onToggle={handleToggle}
          onThresholdChange={handleThresholdChange}
        />
        <hr className={styles.divider} />
        <PlansToggle config={config} onChange={handlePlansChange} />
        <hr className={styles.divider} />
        <StorageSettings
          config={config}
          onDirectoryChange={handleDirectoryChange}
          onHistoryChange={handleHistoryChange}
        />
        <hr className={styles.divider} />
        <VolumePreview config={config} />
        <hr className={styles.divider} />
        <Actions onReset={handleReset} />
      </div>

      {/* Правая область: XML-предпросмотр занимает весь экран */}
      <div className={styles.right}>
        <XmlPreview config={config} />
      </div>
    </div>
  );
}
