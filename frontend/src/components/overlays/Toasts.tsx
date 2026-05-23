import { useEffect } from "react";
import { Icon } from "@/components/icons/Icon";
import { useAppStore, type ToastMessage } from "@/store/appStore";
import styles from "./Toasts.module.css";

// Auto-dismiss длительность зависит от важности сообщения:
//  - ok    — успех (короткий feedback типа «Архив удалён»), 1.5 сек
//  - info  — нейтральная информация, 2.5 сек
//  - warn  — предупреждение, нужно успеть прочитать, 6 сек
//  - err   — ошибка, НЕ автодизмиссится. Закрытие только по клику —
//            пользователь обязан её прочитать целиком (там стектрейс,
//            детали бага, имя файла и т.п.). Раньше err тоже закрывался
//            за 1 сек, и юзер не успевал прочитать «Binder Error:
//            Referenced column total_ms not found …» (см. SQL Console).
const TOAST_DURATION_MS: Record<ToastMessage["tone"], number | null> = {
  ok: 1500,
  info: 2500,
  warn: 6000,
  err: null,
};

export function Toasts() {
  const toasts = useAppStore((s) => s.toasts);
  const dismiss = useAppStore((s) => s.dismissToast);

  useEffect(() => {
    if (toasts.length === 0) return;
    const timers: number[] = [];
    for (const t of toasts) {
      const duration = TOAST_DURATION_MS[t.tone];
      if (duration === null) continue; // err — только click-to-dismiss
      timers.push(window.setTimeout(() => dismiss(t.id), duration));
    }
    return () => timers.forEach((id) => window.clearTimeout(id));
  }, [toasts, dismiss]);

  return (
    <div className={styles.stack}>
      {toasts.map((t) => {
        const isErr = t.tone === "err";
        return (
          // Click — убрать тост вручную (для err это единственный способ
          // закрытия). title даёт hint без рисования X-кнопки.
          <div
            key={t.id}
            className={`${styles.toast} ${styles[`tone_${t.tone}`]}`}
            onClick={() => dismiss(t.id)}
            title={isErr ? "Кликни чтобы скрыть ошибку" : "Кликни — закрыть"}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") dismiss(t.id);
            }}
          >
            <span className={styles.toast_text}>{t.text}</span>
            {isErr && (
              <span className={styles.toast_dismiss_hint} aria-hidden>
                <Icon name="X" size={12} />
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
