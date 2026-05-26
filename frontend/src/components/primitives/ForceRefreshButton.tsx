/**
 * Sprint 11 Phase D — Force Refresh button для AI cards.
 *
 * UX (по memory rule «скрывать имплементационные детали от юзера»):
 * - Маленькая icon-only кнопка обновления
 * - Allowed: tooltip «Обновить ответ AI»
 * - Disabled (cooldown): tooltip «Доступно через X:XX», без упоминания «кэш»
 * - Не показывает badges типа «⚡ из кэша» — юзер не должен знать про caching
 *
 * Polling: status проверяется только когда видна кнопка (после первого ответа).
 * Interval 5 сек — countdown обновляется в реальном времени.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { cloud } from "@/api/cloud";
import type { ForceRefreshStatus } from "@/api/cloud";
import styles from "./ForceRefreshButton.module.css";

interface Props {
  /** Cache key из последнего AI response. Если null — кнопка не показывается. */
  cacheKey: string | null | undefined;
  /** Callback который инициирует force_refresh AI запрос. */
  onRefresh: () => Promise<void> | void;
  /** True пока внешний AI запрос в полёте — кнопка должна показывать spinner. */
  refreshing?: boolean;
}

function formatCountdown(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function ForceRefreshButton({ cacheKey, onRefresh, refreshing }: Props) {
  const [status, setStatus] = useState<ForceRefreshStatus | null>(null);
  const pollingRef = useRef<number | null>(null);

  // Polling status каждые 5 сек пока есть cacheKey.
  // Stops at unmount или когда cacheKey очищается.
  useEffect(() => {
    if (!cacheKey) {
      setStatus(null);
      return;
    }

    let cancelled = false;
    const fetchStatus = async () => {
      try {
        const result = await cloud.aiForceRefreshStatus(cacheKey);
        if (!cancelled) setStatus(result);
      } catch {
        // Не критично — UI продолжит работать в локальном режиме
      }
    };

    fetchStatus();
    pollingRef.current = window.setInterval(fetchStatus, 5000);

    return () => {
      cancelled = true;
      if (pollingRef.current !== null) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [cacheKey]);

  const handleClick = useCallback(async () => {
    if (refreshing) return;
    if (status && !status.allowed) return;
    await onRefresh();
    // Force re-fetch status сразу после refresh
    if (cacheKey) {
      try {
        const fresh = await cloud.aiForceRefreshStatus(cacheKey);
        setStatus(fresh);
      } catch {
        /* ignore */
      }
    }
  }, [refreshing, status, onRefresh, cacheKey]);

  if (!cacheKey) return null;

  const disabled = refreshing || (status !== null && !status.allowed);
  let tooltip: string;
  if (refreshing) {
    tooltip = "Обновление…";
  } else if (status && !status.allowed) {
    const remaining =
      status.per_item_remaining_seconds > 0
        ? status.per_item_remaining_seconds
        : status.per_session_remaining_seconds;
    tooltip = `Доступно через ${formatCountdown(remaining)}`;
  } else {
    tooltip = "Обновить ответ AI";
  }

  return (
    <button
      type="button"
      className={[
        styles.btn,
        disabled ? styles.btn_disabled : "",
        refreshing ? styles.btn_spinning : "",
      ].join(" ")}
      onClick={handleClick}
      disabled={disabled}
      data-tooltip={tooltip}
      aria-label={tooltip}
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polyline points="23 4 23 10 17 10" />
        <polyline points="1 20 1 14 7 14" />
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
      </svg>
    </button>
  );
}
