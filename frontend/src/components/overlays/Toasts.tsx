import { useEffect } from "react";
import { useAppStore } from "@/store/appStore";
import styles from "./Toasts.module.css";

// 1000 ms — верхняя граница диапазона который попросил юзер (0.5-1 сек).
// Достаточно чтобы прочитать короткое сообщение «Архив удалён · 2.0 МБ»,
// и не залипает на экране стопкой если действие повторяется.
const TOAST_DURATION_MS = 1000;

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
        // Click — убрать тост вручную (если нужно прочитать остальные за
        // стопкой). title="Кликни — закрыть" даёт hint без рисования X-кнопки.
        <div
          key={t.id}
          className={`${styles.toast} ${styles[`tone_${t.tone}`]}`}
          onClick={() => dismiss(t.id)}
          title="Кликни — закрыть"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") dismiss(t.id);
          }}
        >
          {t.text}
        </div>
      ))}
    </div>
  );
}
