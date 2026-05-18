import { useCallback, useEffect } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { TopBar } from "@/components/chrome/TopBar";
import { Sidebar } from "@/components/chrome/Sidebar";
import { StatusBar } from "@/components/chrome/StatusBar";
import { CommandPalette } from "@/components/overlays/CommandPalette";
import { DropZone } from "@/components/overlays/DropZone";
import { Toasts } from "@/components/overlays/Toasts";
import { OQLConsoleScreen } from "@/components/screens/OQLConsole/OQLConsole";
import { backend } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t, format } from "@/i18n/ru";

export function App() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);
  const cmdOpen = useAppStore((s) => s.cmdOpen);
  const setCmdOpen = useAppStore((s) => s.setCmdOpen);
  const currentScreen = useAppStore((s) => s.currentScreen);
  const setArchive = useAppStore((s) => s.setArchive);
  const setStorageStats = useAppStore((s) => s.setStorageStats);
  const pushToast = useAppStore((s) => s.pushToast);

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

  const loadArchiveFromPath = useCallback(
    async (path: string) => {
      const name = path.split(/[\\/]/).pop() ?? path;
      pushToast(format(t.progress.loadingFromPath, { name }), "info");
      try {
        const state = await backend.loadArchive(path);
        setArchive(state);
        if (state.status === "ready") {
          const stats = await backend.getStorageStats(state.archive_id);
          setStorageStats(stats);
          pushToast(
            format(t.progress.completedToast, {
              events: stats.events_count.toLocaleString("ru-RU"),
              time: "—",
            }),
            "ok",
          );
        } else if (state.status === "error") {
          pushToast(format(t.errors.loadFailed, { detail: state.errors[0] || t.oql.archiveError.unknown }), "err");
        }
      } catch (e) {
        pushToast(format(t.errors.rpcError, { detail: String(e) }), "err");
      }
    },
    [pushToast, setArchive, setStorageStats],
  );

  const onPickArchive = useCallback(async () => {
    try {
      const selected = await openDialog({
        multiple: false,
        directory: false,
        filters: [{ name: "TJ archive", extensions: ["zip"] }],
      });
      if (typeof selected === "string") {
        await loadArchiveFromPath(selected);
      }
    } catch (e) {
      pushToast(format(t.errors.dialogError, { detail: String(e) }), "err");
    }
  }, [loadArchiveFromPath, pushToast]);

  return (
    <div className="app" data-sidebar={sidebarOpen ? "open" : "closed"}>
      <TopBar onOpenArchive={onPickArchive} />
      <Sidebar />
      <main className="app__main">
        {currentScreen === "oql" && <OQLConsoleScreen onLoadArchive={onPickArchive} />}
        {currentScreen !== "oql" && (
          <div style={{ padding: 32, color: "var(--o-text-3)" }}>
            {format(t.app.screenPlaceholder, { id: currentScreen })}
          </div>
        )}
      </main>
      <StatusBar />

      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onLoadArchive={onPickArchive} />
      <DropZone onFile={loadArchiveFromPath} />
      <Toasts />
    </div>
  );
}
