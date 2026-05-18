import { useCallback, useEffect } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { TopBar } from "@/components/chrome/TopBar";
import { Sidebar } from "@/components/chrome/Sidebar";
import { StatusBar } from "@/components/chrome/StatusBar";
import { CommandPalette } from "@/components/overlays/CommandPalette";
import { DropZone } from "@/components/overlays/DropZone";
import { Toasts } from "@/components/overlays/Toasts";
import { ProgressCard } from "@/components/overlays/ProgressCard";
import { OQLConsoleScreen } from "@/components/screens/OQLConsole/OQLConsole";
import { backend, onProgress, type ProgressEvent } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t, format } from "@/i18n/ru";

export function App() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);
  const cmdOpen = useAppStore((s) => s.cmdOpen);
  const setCmdOpen = useAppStore((s) => s.setCmdOpen);
  const currentScreen = useAppStore((s) => s.currentScreen);
  const setArchive = useAppStore((s) => s.setArchive);
  const setStorageStats = useAppStore((s) => s.setStorageStats);
  const setIngest = useAppStore((s) => s.setIngest);
  const setLastResult = useAppStore((s) => s.setLastResult);
  const setProgressCardMinimized = useAppStore((s) => s.setProgressCardMinimized);
  const pushToast = useAppStore((s) => s.pushToast);

  const onActiveArchiveDeleted = useCallback(() => {
    setArchive(null);
    setStorageStats(null);
    setIngest(null);
    setLastResult(null);
    setProgressCardMinimized(false);
  }, [setArchive, setStorageStats, setIngest, setLastResult, setProgressCardMinimized]);

  // Cmd+K / Ctrl+K — открыть Command Palette. Escape — закрыть.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const meta = e.ctrlKey || e.metaKey;
      if (meta && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        setCmdOpen(!useAppStore.getState().cmdOpen);
      } else if (e.key === "Escape") {
        setCmdOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setCmdOpen]);

  // Подписка на push-notifications прогресса от backend.
  useEffect(() => {
    const unlisten = onProgress(async (event: ProgressEvent) => {
      setIngest(event);
      // Зеркало в archive state — чтобы остальной UI (TopBar/StatusBar) видел статус.
      const currentArchive = useAppStore.getState().archive;
      if (currentArchive && currentArchive.archive_id === event.archive_id) {
        setArchive({
          ...currentArchive,
          status: event.phase === "done" ? "ready" : event.phase,
          progress: event.bytes_total > 0 ? event.bytes_done / event.bytes_total : 0,
          events_parsed: event.events_inserted,
          file_count: event.files_total,
          size_bytes: event.bytes_total,
        });
      }
      if (event.phase === "done") {
        try {
          const stats = await backend.getStorageStats(event.archive_id);
          setStorageStats(stats);
          pushToast(
            format(t.progress.completedToast, {
              events: stats.events_count.toLocaleString("ru-RU"),
              time: formatElapsed(stats.archive_metadata.loaded_at),
            }),
            "ok",
          );
        } catch (e) {
          pushToast(format(t.errors.rpcError, { detail: String(e) }), "err");
        }
      } else if (event.phase === "error") {
        const detail = event.error_message ?? t.oql.archiveError.unknown;
        pushToast(format(t.errors.loadFailed, { detail }), "err");
      }
    });
    return unlisten;
  }, [pushToast, setArchive, setIngest, setStorageStats]);

  const loadDirectoryFromPath = useCallback(
    async (path: string) => {
      const name = path.split(/[\\/]/).pop() ?? path;
      pushToast(format(t.progress.loadingFromPath, { name }), "info");
      setProgressCardMinimized(false);
      try {
        const initial = await backend.loadDirectory(path);
        setArchive(initial);
      } catch (e) {
        pushToast(format(t.errors.rpcError, { detail: String(e) }), "err");
      }
    },
    [pushToast, setArchive, setProgressCardMinimized],
  );

  const onPickFolder = useCallback(async () => {
    try {
      const selected = await openDialog({
        multiple: false,
        directory: true,
      });
      if (typeof selected === "string") {
        await loadDirectoryFromPath(selected);
      }
    } catch (e) {
      pushToast(format(t.errors.dialogError, { detail: String(e) }), "err");
    }
  }, [loadDirectoryFromPath, pushToast]);

  return (
    <div className="app" data-sidebar={sidebarOpen ? "open" : "closed"}>
      <TopBar onOpenArchive={onPickFolder} onActiveArchiveDeleted={onActiveArchiveDeleted} />
      <Sidebar />
      <main className="app__main">
        {currentScreen === "oql" && <OQLConsoleScreen onLoadArchive={onPickFolder} />}
        {currentScreen !== "oql" && (
          <div style={{ padding: 32, color: "var(--o-text-3)" }}>
            {format(t.app.screenPlaceholder, { id: currentScreen })}
          </div>
        )}
      </main>
      <StatusBar />

      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onLoadArchive={onPickFolder} />
      <DropZone onPath={loadDirectoryFromPath} />
      <ProgressCard />
      <Toasts />
    </div>
  );
}

function formatElapsed(iso: string | null): string {
  if (!iso) return "—";
  return iso;
}
