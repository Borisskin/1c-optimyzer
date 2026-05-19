import { useCallback, useEffect } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { TopBar } from "@/components/chrome/TopBar";
import { Sidebar } from "@/components/chrome/Sidebar";
import { StatusBar } from "@/components/chrome/StatusBar";
import { CommandPalette } from "@/components/overlays/CommandPalette";
import { DropZone } from "@/components/overlays/DropZone";
import { Toasts } from "@/components/overlays/Toasts";
import { ProgressCard } from "@/components/overlays/ProgressCard";
import { SQLConsoleScreen } from "@/components/screens/SQLConsole/SQLConsole";
import { SlowQueriesScreen } from "@/components/screens/SlowQueries/SlowQueries";
import { LocksTimelineScreen } from "@/components/screens/LocksTimeline/LocksTimeline";
import { ProcessRolesScreen } from "@/components/screens/ProcessRoles/ProcessRoles";
import { DurationHistogramScreen } from "@/components/screens/DurationHistogram/DurationHistogram";
import { ErrorsFeedScreen } from "@/components/screens/ErrorsFeed/ErrorsFeed";
import { ActivityHeatmapScreen } from "@/components/screens/ActivityHeatmap/ActivityHeatmap";
import { ArchiveComparisonScreen } from "@/components/screens/ArchiveComparison/ArchiveComparison";
import { backend, onProgress, type ProgressEvent } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t, format } from "@/i18n/ru";

export function App() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);
  const cmdOpen = useAppStore((s) => s.cmdOpen);
  const setCmdOpen = useAppStore((s) => s.setCmdOpen);
  const currentScreen = useAppStore((s) => s.currentScreen);
  const archive = useAppStore((s) => s.archive);
  const archiveReady = archive?.status === "ready" ? archive : null;
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
  // Ctrl+1..8 — switch активный экран (Sprint 2 Phase J).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const meta = e.ctrlKey || e.metaKey;
      if (meta && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        setCmdOpen(!useAppStore.getState().cmdOpen);
        return;
      }
      if (e.key === "Escape") {
        setCmdOpen(false);
        return;
      }
      // Ctrl+1..8 — quick screen switch.
      if (meta && /^[1-8]$/.test(e.key)) {
        const screensInOrder: import("@/store/appStore").ScreenId[] = [
          "sql",
          "slow-queries",
          "locks",
          "process-roles",
          "duration",
          "errors",
          "activity",
          "comparison",
        ];
        const idx = Number(e.key) - 1;
        const target = screensInOrder[idx];
        if (target) {
          e.preventDefault();
          useAppStore.getState().setScreen(target);
        }
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
      if (event.phase === "cancelled") {
        // Архив удалён бэкендом; убираем зеркало из UI.
        if (currentArchive && currentArchive.archive_id === event.archive_id) {
          setArchive(null);
        }
      } else if (currentArchive && currentArchive.archive_id === event.archive_id) {
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
        const detail = event.error_message ?? t.sql.archiveError.unknown;
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
        {renderScreen({
          screen: currentScreen,
          archiveId: archiveReady?.archive_id ?? null,
          onLoadArchive: onPickFolder,
        })}
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

function renderScreen({
  screen,
  archiveId,
  onLoadArchive,
}: {
  screen: import("@/store/appStore").ScreenId;
  archiveId: string | null;
  onLoadArchive: () => void;
}) {
  switch (screen) {
    case "sql":
      return <SQLConsoleScreen onLoadArchive={onLoadArchive} />;
    case "slow-queries":
      return <SlowQueriesScreen archiveId={archiveId} />;
    case "locks":
      return <LocksTimelineScreen archiveId={archiveId} />;
    case "process-roles":
      return <ProcessRolesScreen archiveId={archiveId} />;
    case "duration":
      return <DurationHistogramScreen archiveId={archiveId} />;
    case "errors":
      return <ErrorsFeedScreen archiveId={archiveId} />;
    case "activity":
      return <ActivityHeatmapScreen archiveId={archiveId} />;
    case "comparison":
      return <ArchiveComparisonScreen />;
    default:
      return (
        <div style={{ padding: 32, color: "var(--o-text-3)" }}>
          {format(t.app.screenPlaceholder, { id: screen })}
        </div>
      );
  }
}
