import { useCallback, useEffect } from "react";
import { backend, type ConfigurationStatusResult } from "@/api/backend";
import { t, format } from "@/i18n/ru";
import { useAppStore } from "@/store/appStore";
import styles from "./ConfigurationBadge.module.css";

interface Props {
  /** Колбэк нажатия — обычно переход в Settings. Если не задан — badge не кликабельный. */
  onClick?: () => void;
}

/**
 * Badge в шапке QueryAnalyzer screen со статусом подключённой XML-выгрузки.
 * - Если не подключена → серый chip "Конфигурация не подключена".
 * - Если подключена → зелёный chip "Конфигурация: БП 3.0 ✓ · 1647 объектов".
 *
 * Состояние держится в useAppStore.configurationStatus и автоматически
 * обновляется при mount компонента (backend.configurationStatus()).
 */
export function ConfigurationBadge({ onClick }: Props) {
  const status = useAppStore((s) => s.configurationStatus);
  const setStatus = useAppStore((s) => s.setConfigurationStatus);

  const refresh = useCallback(async () => {
    try {
      const s = await backend.configurationStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    }
  }, [setStatus]);

  useEffect(() => {
    if (status === null) {
      refresh();
    }
  }, [status, refresh]);

  const connected = status?.connected ?? false;
  const synonym = status?.configuration?.synonym_ru ?? "";
  const name = status?.configuration?.name ?? "";
  const objectCount = status?.object_count ?? 0;
  const sourcePath = status?.source_path ?? "";

  const titleLine = synonym || name;
  const tooltip = connected
    ? [
        titleLine || "(без имени)",
        sourcePath ? `\n${sourcePath}` : "",
        status?.indexed_at ? `\n${status.indexed_at}` : "",
      ].join("")
    : t.configuration.notConnectedDescription;

  return (
    <button
      type="button"
      className={`${styles.badge} ${connected ? styles.badgeConnected : styles.badgeIdle}`}
      onClick={onClick}
      title={tooltip}
      disabled={!onClick}
    >
      <span className={styles.dot} aria-hidden />
      <span className={styles.text}>
        {connected ? (
          <>
            <span className={styles.title}>
              {t.configuration.badgeConnectedTitle}: {titleLine || "—"}
            </span>
            <span className={styles.subtitle}>
              {objectCount.toLocaleString("ru-RU")} {t.configuration.badgeObjectsSuffix}
            </span>
          </>
        ) : (
          <span className={styles.title}>{t.configuration.badgeNotConnected}</span>
        )}
      </span>
    </button>
  );
}

export type { ConfigurationStatusResult };
