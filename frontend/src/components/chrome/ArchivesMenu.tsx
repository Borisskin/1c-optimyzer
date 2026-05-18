import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { backend, type StoredArchive } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t, format } from "@/i18n/ru";
import styles from "./ArchivesMenu.module.css";

interface Props {
  onClose: () => void;
  onLoadNew: () => void;
  onActiveArchiveDeleted: () => void;
}

export function ArchivesMenu({ onClose, onLoadNew, onActiveArchiveDeleted }: Props) {
  const [archives, setArchives] = useState<StoredArchive[]>([]);
  const [totalSize, setTotalSize] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [busyAll, setBusyAll] = useState(false);
  const currentArchive = useAppStore((s) => s.archive);
  const pushToast = useAppStore((s) => s.pushToast);
  const rootRef = useRef<HTMLDivElement>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await backend.listStoredArchives();
      setArchives(resp.archives);
      setTotalSize(resp.total_db_size_bytes);
    } catch (e) {
      pushToast(format(t.errors.rpcError, { detail: String(e) }), "err");
    } finally {
      setLoading(false);
    }
  }, [pushToast]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, [onClose]);

  const handleDelete = async (archive: StoredArchive) => {
    const folderName = folderBasename(archive.path);
    const msg = format(t.archives.confirmDelete, {
      name: folderName,
      size: formatBytes(archive.db_size_bytes),
    });
    if (!window.confirm(msg)) return;
    setBusyId(archive.archive_id);
    const wasActive = currentArchive?.archive_id === archive.archive_id;
    try {
      await backend.deleteArchive(archive.archive_id);
      pushToast(
        format(t.archives.deletedToast, { size: formatBytes(archive.db_size_bytes) }),
        "ok",
      );
      if (wasActive) onActiveArchiveDeleted();
      await refresh();
    } catch (e) {
      pushToast(`${t.archives.deleteFailedToast}: ${String(e)}`, "err");
    } finally {
      setBusyId(null);
    }
  };

  const handleDeleteAll = async () => {
    if (archives.length === 0) return;
    const msg = format(t.archives.confirmDeleteAll, {
      count: String(archives.length),
      size: formatBytes(totalSize),
    });
    if (!window.confirm(msg)) return;
    setBusyAll(true);
    const hadActive = currentArchive !== null;
    try {
      const result = await backend.deleteAllArchives();
      pushToast(
        format(t.archives.deletedAllToast, {
          count: String(result.files_deleted),
          size: formatBytes(totalSize),
        }),
        "ok",
      );
      if (hadActive) onActiveArchiveDeleted();
      await refresh();
    } catch (e) {
      pushToast(`${t.archives.deleteFailedToast}: ${String(e)}`, "err");
    } finally {
      setBusyAll(false);
    }
  };

  return (
    <div className={styles.menu} ref={rootRef} role="menu" aria-label="Archives menu">
      <button
        className={styles.action_row}
        onClick={() => {
          onClose();
          onLoadNew();
        }}
      >
        <Icon name="Plus" size={14} />
        <span>{t.archives.menuLoadNew}</span>
      </button>

      <div className={styles.section_label}>{t.archives.sectionRecent}</div>

      {loading ? (
        <div className={styles.empty}>…</div>
      ) : archives.length === 0 ? (
        <div className={styles.empty}>{t.archives.empty}</div>
      ) : (
        <div className={styles.list}>
          {archives.map((a) => {
            const isCurrent = currentArchive?.archive_id === a.archive_id;
            const isBusy = busyId === a.archive_id;
            return (
              <div
                key={a.archive_id}
                className={`${styles.item} ${isCurrent ? styles.item_current : ""} ${a.is_orphan ? styles.item_orphan : ""}`}
              >
                <div className={styles.item_main}>
                  <div className={styles.item_title}>
                    <span className={styles.item_name} title={a.path}>
                      {folderBasename(a.path)}
                    </span>
                    {isCurrent && (
                      <span className={styles.badge_current}>{t.archives.currentBadge}</span>
                    )}
                    {a.is_orphan && (
                      <span className={styles.badge_orphan}>{t.archives.orphanBadge}</span>
                    )}
                  </div>
                  <div className={styles.item_meta}>
                    <span>{formatBytes(a.db_size_bytes)}</span>
                    <span className={styles.meta_sep}>·</span>
                    <span>
                      {formatNumber(a.events_count)} {t.archives.eventsLabel}
                    </span>
                    <span className={styles.meta_sep}>·</span>
                    <span>{formatDate(a.loaded_at)}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className={styles.delete_btn}
                  title={t.archives.deleteTooltip}
                  disabled={isBusy || busyAll}
                  onClick={() => handleDelete(a)}
                >
                  <Icon name="X" size={13} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      <div className={styles.footer}>
        <span className={styles.footer_total}>
          {t.archives.storageTotal} <strong>{formatBytes(totalSize)}</strong>
        </span>
        <button
          type="button"
          className={styles.danger_btn}
          disabled={archives.length === 0 || busyAll}
          onClick={handleDeleteAll}
        >
          {t.archives.deleteAll}
        </button>
      </div>
    </div>
  );
}

function folderBasename(p: string): string {
  return p.split(/[\\/]/).filter(Boolean).pop() ?? p;
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

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
  } catch {
    return iso;
  }
}
