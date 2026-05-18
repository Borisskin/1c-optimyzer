import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import { Icon } from "@/components/icons/Icon";
import { useAppStore } from "@/store/appStore";
import { t, format } from "@/i18n/ru";
import styles from "./DropZone.module.css";

type DragDropPayload = {
  type?: "enter" | "over" | "drop" | "leave";
  paths?: string[];
  position?: { x: number; y: number };
};

type PathKind = "folder" | "file" | "missing";

export function DropZone({ onPath }: { onPath: (path: string) => void }) {
  const [active, setActive] = useState(false);
  const pushToast = useAppStore((s) => s.pushToast);

  useEffect(() => {
    const unlistens: Array<() => void> = [];
    let cancelled = false;

    const subscribe = async (event: string, handler: (e: { payload: DragDropPayload }) => void) => {
      const fn = await listen<DragDropPayload>(event, handler);
      if (cancelled) {
        fn();
      } else {
        unlistens.push(fn);
      }
    };

    subscribe("tauri://drag-enter", () => setActive(true));
    subscribe("tauri://drag-over", () => setActive(true));
    subscribe("tauri://drag-leave", () => setActive(false));
    subscribe("tauri://drag-drop", async (event) => {
      setActive(false);
      const paths = event.payload.paths ?? [];
      if (paths.length === 0) return;
      const first = paths[0];
      try {
        const classification = await invoke<{ kind: PathKind }>("classify_path", { path: first });
        if (classification.kind === "folder") {
          onPath(first);
        } else if (classification.kind === "missing") {
          pushToast(t.errors.folderNotFound, "err");
        } else {
          pushToast(t.errors.invalidDropTarget, "err");
        }
      } catch (e) {
        pushToast(format(t.errors.classifyFailed, { detail: String(e) }), "err");
      }
    });

    return () => {
      cancelled = true;
      for (const fn of unlistens) fn();
    };
  }, [onPath, pushToast]);

  if (!active) return null;
  return (
    <div className={styles.overlay}>
      <div className={styles.panel}>
        <Icon name="Folder" size={32} color="var(--o-accent)" />
        <div className={styles.title}>{t.drop.titleFolder}</div>
        <div className={styles.sub}>{t.drop.sub}</div>
      </div>
    </div>
  );
}
