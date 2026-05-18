import { Icon } from "@/components/icons/Icon";
import { Badge, KBD } from "@/components/primitives/Primitives";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import styles from "./TopBar.module.css";

export function TopBar({ onOpenArchive }: { onOpenArchive: () => void }) {
  const archive = useAppStore((s) => s.archive);
  const setCmdOpen = useAppStore((s) => s.setCmdOpen);
  const storageStats = useAppStore((s) => s.storageStats);

  const archiveLabel = archive ? truncateName(archive.path) : t.topbar.loadFolder;
  const archiveSize = archive ? formatBytes(archive.size_bytes) : null;

  const statusToLabel: Record<string, string> = {
    extracting: t.topbar.healthExtracting,
    discovering: t.topbar.healthDiscovering,
    parsing: t.topbar.healthParsing,
    indexing: t.topbar.healthIndexing,
  };

  let healthLabel = `● ${t.topbar.healthIdle}`;
  let healthTone: "ok" | "warn" | "info" = "info";
  if (archive) {
    if (archive.status === "ready") {
      healthLabel = `● ${t.topbar.healthReady} · ${formatNumber(
        storageStats?.events_count ?? archive.events_parsed,
      )} ${t.topbar.eventsSuffix}`;
      healthTone = "ok";
    } else if (archive.status === "error") {
      healthLabel = `● ${t.topbar.healthError}`;
      healthTone = "warn";
    } else {
      const verb = statusToLabel[archive.status] ?? archive.status;
      healthLabel = `● ${verb}… ${Math.round(archive.progress * 100)}%`;
      healthTone = "warn";
    }
  }

  return (
    <div className={styles.topbar}>
      <div className={styles.brand}>
        <div className={styles.brand_box}>1C</div>
        <div className={styles.brand_text}>
          <div className={styles.brand_name}>{t.app.name}</div>
          <div className={styles.brand_ver}>
            {t.app.version} · {t.app.edition}
          </div>
        </div>
      </div>

      <button className={styles.archive_btn} onClick={onOpenArchive}>
        <Icon name="Database" size={13} color="var(--o-text-3)" />
        <span className={styles.archive_label}>{archiveLabel}</span>
        {archiveSize && <span className={styles.archive_size}>{archiveSize}</span>}
        <Icon name="ChevronDown" size={12} color="var(--o-text-3)" />
      </button>

      <button className={styles.search_btn} onClick={() => setCmdOpen(true)}>
        <Icon name="Search" size={13} color="var(--o-text-3)" />
        <span className={styles.search_placeholder}>{t.topbar.searchPlaceholder}</span>
        <span className={styles.search_shortcut}>
          <KBD>Ctrl</KBD> <KBD>K</KBD>
        </span>
      </button>

      <div className={styles.right}>
        <div className={styles.health}>
          <Badge tone={healthTone}>{healthLabel}</Badge>
        </div>
        <button className={styles.icon_btn} title={t.topbar.alertsTooltip} disabled>
          <Icon name="Bell" size={15} />
        </button>
        <button className={styles.ai_btn} title={t.topbar.aiHelperTooltip} disabled>
          <Icon name="Sparkles" size={13} />
          <span className={styles.ai_label}>{t.topbar.aiBadge}</span>
          <Badge tone="mute">{t.topbar.aiBadgePro}</Badge>
        </button>
        <div className="div-v" style={{ height: 20, margin: "0 4px" }} />
        <button className={styles.settings_btn} title={t.topbar.settingsTooltip}>
          <Icon name="Settings" size={14} />
        </button>
      </div>
    </div>
  );
}

function truncateName(path: string): string {
  const name = path.split(/[\\/]/).pop() || path;
  if (name.length <= 36) return name;
  return name.slice(0, 18) + "…" + name.slice(-15);
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
