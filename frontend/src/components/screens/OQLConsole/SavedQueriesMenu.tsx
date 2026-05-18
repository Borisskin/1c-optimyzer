import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { backend, type SavedQuery } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import styles from "./OQLConsole.module.css";

interface Props {
  currentQuery: string;
  onLoadQuery: (query: string) => void;
}

export function SavedQueriesMenu({ currentQuery, onLoadQuery }: Props) {
  const [items, setItems] = useState<SavedQuery[]>([]);
  const [open, setOpen] = useState(false);
  const pushToast = useAppStore((s) => s.pushToast);

  const refresh = useCallback(() => {
    backend
      .listSavedQueries()
      .then(setItems)
      .catch((e) => pushToast(`${t.toast.error}: ${String(e)}`, "err"));
  }, [pushToast]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleSave = useCallback(async () => {
    const name = window.prompt(`${t.oql.actions.save}: ${t.oql.saved.newQuery}?`);
    if (!name || !name.trim()) return;
    try {
      await backend.saveQuery(name.trim(), currentQuery);
      pushToast(t.toast.success, "ok");
      refresh();
    } catch (e) {
      pushToast(`${t.toast.error}: ${String(e)}`, "err");
    }
  }, [currentQuery, pushToast, refresh]);

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await backend.deleteSavedQuery(id);
        refresh();
      } catch (e) {
        pushToast(`${t.toast.error}: ${String(e)}`, "err");
      }
    },
    [pushToast, refresh],
  );

  return (
    <div className={styles.saved_menu}>
      <button
        className={styles.template_btn}
        onClick={() => setOpen((v) => !v)}
        title={t.oql.saved.label}
      >
        <Icon name="Bookmark" size={11} color="var(--o-text-3)" />
        {t.oql.saved.label}
        <Icon name="ChevronDown" size={10} color="var(--o-text-3)" />
      </button>
      <button className={styles.template_btn} onClick={handleSave} title={t.oql.actions.save}>
        <Icon name="Upload" size={11} color="var(--o-text-3)" />
        {t.oql.actions.save}
      </button>

      {open && (
        <div className={styles.saved_dropdown}>
          {items.length === 0 ? (
            <div className={styles.saved_empty}>{t.oql.saved.empty}</div>
          ) : (
            items.map((it) => (
              <div key={it.id} className={styles.saved_row}>
                <button
                  className={styles.saved_load_btn}
                  onClick={() => {
                    onLoadQuery(it.query);
                    setOpen(false);
                    backend.markQueryRun(it.id).catch(() => undefined);
                  }}
                  title={it.description ?? ""}
                >
                  {it.name}
                </button>
                <button
                  className={styles.saved_del_btn}
                  onClick={() => handleDelete(it.id)}
                  title={t.toast.error}
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
