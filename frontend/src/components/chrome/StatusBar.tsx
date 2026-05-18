import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import { useAnimatedCounter } from "@/hooks/useAnimatedCounter";
import styles from "./StatusBar.module.css";

export function StatusBar() {
  const archive = useAppStore((s) => s.archive);
  const stats = useAppStore((s) => s.storageStats);
  const ingest = useAppStore((s) => s.ingest);

  const isActive = Boolean(ingest && ingest.phase !== "done" && ingest.phase !== "error");
  const animatedEvents = useAnimatedCounter(ingest?.events_inserted ?? 0, isActive);
  const animatedBytes = useAnimatedCounter(ingest?.bytes_done ?? 0, isActive);

  const statusLabels: Record<string, string> = {
    ready: t.statusbar.ready,
    parsing: t.statusbar.parsing,
    discovering: t.statusbar.discovering,
    indexing: t.statusbar.indexing,
    extracting: t.statusbar.extracting,
    error: t.statusbar.error,
  };

  const stateLabel = archive ? statusLabels[archive.status] ?? archive.status : t.statusbar.idle;
  const dotClass = archive?.status === "ready" ? styles.dot_ok : styles.dot_warn;

  const archName = archive ? archive.path.split(/[\\/]/).pop() : t.statusbar.noArchive;
  const eventsCount = stats?.events_count ?? archive?.events_parsed ?? 0;
  const dbSize = stats ? formatBytes(stats.db_size_bytes) : "—";
  const parseTime = archive?.parsing_time_sec
    ? `${t.statusbar.parsedIn} ${formatSeconds(archive.parsing_time_sec)}`
    : "—";

  const percent =
    isActive && ingest && ingest.bytes_total > 0
      ? Math.min(100, (animatedBytes / ingest.bytes_total) * 100)
      : 0;

  return (
    <div className={styles.statusbar}>
      <span className={styles.cell}>
        <span className={`${styles.dot} ${dotClass}`} />
        <span>
          {stateLabel} · {archName}
        </span>
      </span>
      {isActive && ingest ? (
        <>
          <span className={styles.divider} />
          <span className={styles.cell}>
            {ingest.current_file ?? "—"} · {formatBytes(animatedBytes)}/{formatBytes(ingest.bytes_total)} ·{" "}
            {percent.toFixed(1)}% · {formatNumber(Math.floor(animatedEvents))} {t.statusbar.events}
          </span>
        </>
      ) : (
        <>
          <span className={styles.divider} />
          <span className={styles.cell}>
            {t.statusbar.duckdb}: {formatNumber(eventsCount)} {t.statusbar.events} · {dbSize}
          </span>
        </>
      )}

      <span className={styles.right}>
        <span>{parseTime}</span>
        <span className={styles.divider} />
        <span>
          {t.app.version}-{t.statusbar.devBuild}
        </span>
      </span>
    </div>
  );
}

function formatBytes(b: number): string {
  if (b < 1024) return `${b} Б`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} КБ`;
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} МБ`;
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} ГБ`;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} млн`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)} тыс`;
  return String(n);
}

function formatSeconds(sec: number): string {
  if (sec < 60) return `${sec.toFixed(1)} с`;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m} мин ${s} с`;
}
