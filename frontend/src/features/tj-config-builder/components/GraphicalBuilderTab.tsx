/**
 * Sprint 10 — GraphicalBuilderTab: двухколоночный конструктор logcfg.xml.
 * Левая колонка: события + планы + хранилище + действия.
 * Правая колонка (sticky): оценка объёма логов.
 */
import { useCallback } from "react";
import type { EventType, LogcfgConfig } from "../types";
import { DEFAULT_LOGCFG_CONFIG } from "../types";
import { EventsGroup } from "./EventsGroup";
import { PlansToggle } from "./PlansToggle";
import { StorageSettings } from "./StorageSettings";
import { Actions } from "./Actions";
import { VolumePreview } from "./VolumePreview";
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

  const handleMaxSizeChange = useCallback(
    (value: number) => {
      onChange({ ...config, max_size_gb: value });
    },
    [config, onChange],
  );

  const handleReset = useCallback(() => {
    onChange({ ...DEFAULT_LOGCFG_CONFIG });
  }, [onChange]);

  return (
    <div className={styles.root}>
      {/* Левая колонка */}
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
          onMaxSizeChange={handleMaxSizeChange}
        />
        <hr className={styles.divider} />
        <Actions config={config} onReset={handleReset} />
      </div>

      {/* Правая колонка: оценка объёма + XML-предпросмотр */}
      <div className={styles.right}>
        <VolumePreview config={config} />
        <XmlPreview config={config} />
      </div>
    </div>
  );
}
