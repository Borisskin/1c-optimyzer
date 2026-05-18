import { useEffect, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import styles from "./DropZone.module.css";

export function DropZone({ onFile }: { onFile: (path: string) => void }) {
  const [active, setActive] = useState(false);

  useEffect(() => {
    let counter = 0;
    const onEnter = (e: DragEvent) => {
      e.preventDefault();
      counter += 1;
      setActive(true);
    };
    const onLeave = (e: DragEvent) => {
      e.preventDefault();
      counter -= 1;
      if (counter <= 0) setActive(false);
    };
    const onOver = (e: DragEvent) => e.preventDefault();
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      counter = 0;
      setActive(false);
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      // В Tauri-окне у File нет webkitGetAsEntry с абсолютным путём — но Tauri
      // предоставляет file.path через onFileDropEvent на уровне окна. Sprint 0:
      // если path есть — используем; иначе info-toast о необходимости file dialog.
      // @ts-expect-error tauri-extended File
      const tauriPath: string | undefined = file.path;
      if (tauriPath) {
        onFile(tauriPath);
      }
    };
    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("dragover", onOver);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("dragover", onOver);
      window.removeEventListener("drop", onDrop);
    };
  }, [onFile]);

  if (!active) return null;
  return (
    <div className={styles.overlay}>
      <div className={styles.panel}>
        <Icon name="Upload" size={32} color="var(--o-accent)" />
        <div className={styles.title}>Drop TZ archive here</div>
        <div className={styles.sub}>.zip с папкой logcfg или структурой rphost_*/...</div>
      </div>
    </div>
  );
}
