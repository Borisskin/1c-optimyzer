import { useEffect, useState } from "react";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import styles from "./SettingsDialog.module.css";
import { AccountTab } from "./AccountTab";
import { PulseLogo } from "@/components/icons/PulseLogo";

type SettingsTab = "account" | "about";

/**
 * Диалог настроек desktop приложения.
 *
 * Вкладки:
 *  • «Аккаунт» — лицензия, активация, статус подписки (см. AccountTab)
 *  • «О программе» — версия, репозиторий
 */
export function SettingsDialog() {
  const open = useAppStore((s) => s.settingsDialogOpen);
  const setOpen = useAppStore((s) => s.setSettingsDialogOpen);
  const [tab, setTab] = useState<SettingsTab>("account");

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
          <button
            type="button"
            className={`${styles.tab} ${tab === "account" ? styles.tab_active : ""}`}
            onClick={() => setTab("account")}
          >
            {t.settings.tabs.account}
          </button>
          <button
            type="button"
            className={`${styles.tab} ${tab === "about" ? styles.tab_active : ""}`}
            onClick={() => setTab("about")}
          >
            {t.settings.tabs.about}
          </button>
        </div>

        <div className={styles.body}>
          {tab === "account" && <AccountTab />}

          {tab === "about" && (
            <>
              <div className={styles.brand}>
                <PulseLogo size={48} />
                <div className={styles.brand_text}>
                  <div className={styles.brand_name}>Optimyzer</div>
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
                <dt>{t.settings.about.supportLabel}</dt>
                <dd>
                  <a href="mailto:support@optimyzer.pro">support@optimyzer.pro</a>
                </dd>
              </dl>
            </>
          )}
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
