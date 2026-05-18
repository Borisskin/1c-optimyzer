import { useEffect } from "react";
import { useAppStore } from "@/store/appStore";
import styles from "./Toasts.module.css";

const TOAST_DURATION_MS = 4000;

export function Toasts() {
  const toasts = useAppStore((s) => s.toasts);
  const dismiss = useAppStore((s) => s.dismissToast);

  useEffect(() => {
    if (toasts.length === 0) return;
    const timers = toasts.map((t) => window.setTimeout(() => dismiss(t.id), TOAST_DURATION_MS));
    return () => timers.forEach((id) => window.clearTimeout(id));
  }, [toasts, dismiss]);

  return (
    <div className={styles.stack}>
      {toasts.map((t) => (
        <div key={t.id} className={`${styles.toast} ${styles[`tone_${t.tone}`]}`}>
          {t.text}
        </div>
      ))}
    </div>
  );
}
