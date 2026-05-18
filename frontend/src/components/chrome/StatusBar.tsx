import { useAppStore } from "@/store/appStore";
import styles from "./StatusBar.module.css";

export function StatusBar() {
  const archive = useAppStore((s) => s.archive);
  const stats = useAppStore((s) => s.storageStats);

  const stateLabel = archive
    ? archive.status === "ready"
      ? "ready"
      : archive.status
    : "idle";
  const dotClass = stateLabel === "ready" ? styles.dot_ok : styles.dot_warn;

  const archName = archive ? archive.path.split(/[\\/]/).pop() : "no archive loaded";
  const eventsCount = stats?.events_count ?? archive?.events_parsed ?? 0;
  const dbSize = stats ? formatBytes(stats.db_size_bytes) : "—";
  const parseTime = archive?.parsing_time_sec
    ? `parsed in ${formatSeconds(archive.parsing_time_sec)}`
    : "—";

  return (
    <div className={styles.statusbar}>
      <span className={styles.cell}>
        <span className={`${styles.dot} ${dotClass}`} />
        <span>{stateLabel} · {archName}</span>
      </span>
      <span className={styles.divider} />
      <span className={styles.cell}>
        DuckDB: {formatNumber(eventsCount)} events · {dbSize}
      </span>

      <span className={styles.right}>
        <span>{parseTime}</span>
        <span className={styles.divider} />
        <span>v0.1.0-dev</span>
      </span>
    </div>
  );
}

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} МБ`;
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} ГБ`;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

function formatSeconds(sec: number): string {
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}m ${s}s`;
}
