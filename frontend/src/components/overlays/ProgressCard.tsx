import { useEffect } from "react";
import { Icon } from "@/components/icons/Icon";
import { useAppStore } from "@/store/appStore";
import type { ProgressEvent } from "@/api/backend";
import { t, format } from "@/i18n/ru";
import styles from "./ProgressCard.module.css";

const AUTO_DISMISS_MS = 5000;

export function ProgressCard() {
  const ingest = useAppStore((s) => s.ingest);
  const minimized = useAppStore((s) => s.progressCardMinimized);
  const setMinimized = useAppStore((s) => s.setProgressCardMinimized);
  const setIngest = useAppStore((s) => s.setIngest);

  useEffect(() => {
    if (!ingest) return;
    if (ingest.phase !== "done") return;
    const timer = window.setTimeout(() => {
      setIngest(null);
      setMinimized(false);
    }, AUTO_DISMISS_MS);
    return () => window.clearTimeout(timer);
  }, [ingest, setIngest, setMinimized]);

  if (!ingest || minimized) return null;

  const titleMap: Record<ProgressEvent["phase"], string> = {
    discovering: t.progress.discovering,
    parsing: t.progress.parsing,
    indexing: t.progress.indexing,
    done: t.progress.done,
    error: t.toast.error,
  };

  const title = titleMap[ingest.phase];
  const isDone = ingest.phase === "done";
  const isError = ingest.phase === "error";

  const percent = ingest.bytes_total > 0 ? Math.min(100, (ingest.bytes_done / ingest.bytes_total) * 100) : 0;

  const dotClass = isDone ? styles.dot_done : isError ? styles.dot_error : styles.dot;
  const fillClass = isDone
    ? `${styles.bar_fill} ${styles.bar_fill_done}`
    : isError
    ? `${styles.bar_fill} ${styles.bar_fill_error}`
    : styles.bar_fill;

  return (
    <div className={styles.card} role="status" aria-live="polite">
      <div className={styles.header}>
        <div className={styles.title}>
          <span className={dotClass} />
          <span>{title}</span>
        </div>
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.icon_btn}
            disabled={isDone || isError || ingest.phase === "indexing"}
            title={t.progress.cancelTooltip}
          >
            {t.progress.cancel}
          </button>
          <button
            type="button"
            className={styles.icon_btn}
            onClick={() => setMinimized(true)}
            title={t.progress.minimize}
          >
            <Icon name="ChevronDown" size={12} />
          </button>
        </div>
      </div>

      <div className={styles.bar}>
        <div className={fillClass} style={{ width: `${isDone ? 100 : percent}%` }} />
      </div>

      <div className={styles.counters}>
        <span>
          {formatBytes(ingest.bytes_done)} / {formatBytes(ingest.bytes_total)} · {percent.toFixed(0)}%
        </span>
        <span>
          {ingest.files_done}/{ingest.files_total} {t.progress.files}
        </span>
      </div>

      {ingest.current_file && !isDone && (
        <div className={styles.file_line}>{ingest.current_file}</div>
      )}

      <div className={styles.events_line}>
        {ingest.events_inserted.toLocaleString("ru-RU")} {t.progress.eventsInserted}
      </div>

      {isError && ingest.error_message && (
        <div className={styles.error_line}>
          {format(t.progress.errorToast, { message: ingest.error_message })}
        </div>
      )}
    </div>
  );
}

function formatBytes(b: number): string {
  if (b < 1024) return `${b} Б`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} КБ`;
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} МБ`;
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} ГБ`;
}
