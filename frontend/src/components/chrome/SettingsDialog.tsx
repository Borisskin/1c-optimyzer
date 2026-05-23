import { useEffect, useState } from "react";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import styles from "./SettingsDialog.module.css";

/**
 * Минимальный диалог настроек (Sales build v0.5.0).
 * Сейчас одна вкладка — «О программе». В следующих спринтах сюда добавятся
 * аккаунт, биллинг и другие настройки. Кнопка-шестерёнка в TopBar открывает
 * этот диалог через флаг settingsDialogOpen в AppStore.
 */
export function SettingsDialog() {
  const open = useAppStore((s) => s.settingsDialogOpen);
  const setOpen = useAppStore((s) => s.setSettingsDialogOpen);
  const [tab] = useState<"about">("about");

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, setOpen]);

  if (!open) return null;

  return (
    <div className={styles.backdrop} onClick={() => setOpen(false)}>
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.head}>
          <h2 className={styles.title}>{t.settings.title}</h2>
          <button
            className={styles.closeBtn}
            onClick={() => setOpen(false)}
            title="ESC"
            aria-label={t.settings.close}
          >
            ×
          </button>
        </div>

        <div className={styles.tabs}>
          <button className={`${styles.tab} ${tab === "about" ? styles.tab_active : ""}`}>
            {t.settings.tabs.about}
          </button>
        </div>

        <div className={styles.body}>
          <div className={styles.brand}>
            <div className={styles.brand_box}>1C</div>
            <div className={styles.brand_text}>
              <div className={styles.brand_name}>{t.app.name}</div>
              <div className={styles.brand_ver}>
                {t.app.version} · {t.app.edition}
              </div>
            </div>
          </div>

          <p className={styles.description}>{t.settings.about.description}</p>

          <dl className={styles.meta}>
            <dt>{t.settings.about.versionLabel}</dt>
            <dd>{t.app.version}</dd>
            <dt>{t.settings.about.editionLabel}</dt>
            <dd>{t.app.edition}</dd>
            <dt>{t.settings.about.repoLabel}</dt>
            <dd>
              <a
                href="https://github.com/anymasoft/1c-optimyzer"
                target="_blank"
                rel="noreferrer noopener"
              >
                github.com/anymasoft/1c-optimyzer
              </a>
            </dd>
          </dl>
        </div>

        <div className={styles.foot}>
          <button className={styles.btnSecondary} onClick={() => setOpen(false)}>
            {t.settings.close}
          </button>
        </div>
      </div>
    </div>
  );
}
