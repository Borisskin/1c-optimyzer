import { useCallback, useEffect, useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import {
  backend,
  type ConfigurationStatusResult,
  type ConfigurationConnectResult,
} from "@/api/backend";
import { t, format } from "@/i18n/ru";
import { useAppStore } from "@/store/appStore";
import styles from "./ConfigurationDialog.module.css";

interface Props {
  open: boolean;
  onClose: () => void;
}

/**
 * Модал настройки подключения XML-выгрузки конфигурации 1С.
 * Содержит:
 * - Empty state с кнопкой "Указать папку выгрузки..." (Tauri folder picker)
 * - Connected state с метаданными + кнопками "Переиндексировать" / "Отключить"
 *
 * Все side-effects идут через backend RPC + обновляют configurationStatus в AppStore.
 */
export function ConfigurationDialog({ open, onClose }: Props) {
  const status = useAppStore((s) => s.configurationStatus);
  const setStatus = useAppStore((s) => s.setConfigurationStatus);
  const pushToast = useAppStore((s) => s.pushToast);
  const [busy, setBusy] = useState<"connect" | "reindex" | "disconnect" | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await backend.configurationStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    }
  }, [setStatus]);

  // При открытии — рефреш чтобы видеть актуальное состояние
  useEffect(() => {
    if (open) {
      refreshStatus();
    }
  }, [open, refreshStatus]);

  // Escape — закрыть
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  const onPickFolder = useCallback(async () => {
    try {
      const selected = await openDialog({
        directory: true,
        multiple: false,
        title: t.configuration.pickFolder,
      });
      if (typeof selected !== "string") return;
      setBusy("connect");
      pushToast(t.configuration.connectingToast, "info");
      try {
        const result: ConfigurationConnectResult = await backend.configurationConnect(selected);
        if (!result.ok) {
          pushToast(
            format(t.configuration.connectFailedToast, { detail: result.error || "—" }),
            "err",
          );
          return;
        }
        const objectsStr = (result.object_count || 0).toLocaleString("ru-RU");
        const toastTmpl =
          result.status === "already_indexed"
            ? t.configuration.alreadyIndexedToast
            : t.configuration.connectedToast;
        pushToast(format(toastTmpl, { objects: objectsStr }), "ok");
        await refreshStatus();
      } catch (e) {
        pushToast(
          format(t.configuration.connectFailedToast, { detail: String(e) }),
          "err",
        );
      } finally {
        setBusy(null);
      }
    } catch (e) {
      pushToast(format(t.errors.dialogError, { detail: String(e) }), "err");
    }
  }, [pushToast, refreshStatus]);

  const onReindex = useCallback(async () => {
    setBusy("reindex");
    try {
      const result = await backend.configurationReindex();
      if (!result.ok) {
        pushToast(
          format(t.configuration.connectFailedToast, { detail: result.error || "—" }),
          "err",
        );
        return;
      }
      const objectsStr = (result.object_count || 0).toLocaleString("ru-RU");
      pushToast(format(t.configuration.reindexedToast, { objects: objectsStr }), "ok");
      await refreshStatus();
    } catch (e) {
      pushToast(format(t.configuration.connectFailedToast, { detail: String(e) }), "err");
    } finally {
      setBusy(null);
    }
  }, [pushToast, refreshStatus]);

  const onDisconnect = useCallback(async () => {
    if (!window.confirm(t.configuration.confirmDisconnect)) return;
    setBusy("disconnect");
    try {
      await backend.configurationDisconnect();
      pushToast(t.configuration.disconnectedToast, "info");
      await refreshStatus();
    } catch (e) {
      pushToast(format(t.errors.rpcError, { detail: String(e) }), "err");
    } finally {
      setBusy(null);
    }
  }, [pushToast, refreshStatus]);

  if (!open) return null;

  const connected = status?.connected ?? false;

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.head}>
          <h2 className={styles.title}>{t.configuration.sectionTitle}</h2>
          <button className={styles.closeBtn} onClick={onClose} title="ESC">
            ×
          </button>
        </div>

        <div className={styles.body}>
          {!connected && <EmptyState onPickFolder={onPickFolder} busy={busy === "connect"} />}
          {connected && status && (
            <ConnectedState
              status={status}
              onReindex={onReindex}
              onDisconnect={onDisconnect}
              busy={busy}
            />
          )}
        </div>
      </div>
    </div>
  );
}


function EmptyState({
  onPickFolder,
  busy,
}: {
  onPickFolder: () => void;
  busy: boolean;
}) {
  return (
    <div className={styles.empty}>
      <div className={styles.emptyIcon} aria-hidden>
        ◇
      </div>
      <div className={styles.emptyTitle}>{t.configuration.notConnected}</div>
      <p className={styles.emptyDescription}>{t.configuration.notConnectedDescription}</p>
      <div className={styles.actions}>
        <button className={styles.btnPrimary} onClick={onPickFolder} disabled={busy}>
          {busy ? t.configuration.connectingToast : t.configuration.pickFolder}
        </button>
      </div>
    </div>
  );
}


function ConnectedState({
  status,
  onReindex,
  onDisconnect,
  busy,
}: {
  status: ConfigurationStatusResult;
  onReindex: () => void;
  onDisconnect: () => void;
  busy: "connect" | "reindex" | "disconnect" | null;
}) {
  const cfg = status.configuration;
  const titleLine = cfg?.synonym_ru || cfg?.name || "—";
  const objectCount = status.object_count ?? 0;
  const byKind = status.by_kind ?? {};
  const topKinds = Object.entries(byKind)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  return (
    <div className={styles.connected}>
      <div className={styles.statusLine}>
        <span className={styles.statusDot} aria-hidden />
        <span className={styles.statusText}>{t.configuration.connectedTitle}</span>
      </div>

      <dl className={styles.meta}>
        <dt>{t.configuration.nameLabel}</dt>
        <dd>{titleLine}</dd>
        {cfg?.version && (
          <>
            <dt>Версия:</dt>
            <dd>{cfg.version}</dd>
          </>
        )}
        {cfg?.vendor && (
          <>
            <dt>Поставщик:</dt>
            <dd>{cfg.vendor}</dd>
          </>
        )}
        <dt>{t.configuration.pathLabel}</dt>
        <dd className={styles.pathValue}>{status.source_path || "—"}</dd>
        <dt>{t.configuration.objectsLabel}</dt>
        <dd>
          {objectCount.toLocaleString("ru-RU")} {t.configuration.objectsCountWord}
          {topKinds.length > 0 && (
            <span className={styles.byKind}>
              {" ("}
              {topKinds.map(([kind, count], i) => (
                <span key={kind}>
                  {i > 0 && ", "}
                  {count} {kind.toLowerCase()}
                </span>
              ))}
              {byKind && Object.keys(byKind).length > 6 && ", …"}
              {")"}
            </span>
          )}
        </dd>
        {status.indexed_at && (
          <>
            <dt>{t.configuration.indexedAtLabel}</dt>
            <dd className={styles.timeValue}>{status.indexed_at}</dd>
          </>
        )}
      </dl>

      <div className={styles.actions}>
        <button
          className={styles.btnSecondary}
          onClick={onReindex}
          disabled={busy !== null}
        >
          {busy === "reindex" ? "…" : t.configuration.reindexButton}
        </button>
        <button
          className={styles.btnDanger}
          onClick={onDisconnect}
          disabled={busy !== null}
        >
          {busy === "disconnect" ? "…" : t.configuration.disconnectButton}
        </button>
      </div>
    </div>
  );
}
