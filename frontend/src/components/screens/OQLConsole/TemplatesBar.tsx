import { useEffect, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { backend, type OQLTemplate } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import styles from "./OQLConsole.module.css";

interface Props {
  onLoadTemplate: (query: string) => void;
}

export function TemplatesBar({ onLoadTemplate }: Props) {
  const [templates, setTemplates] = useState<OQLTemplate[]>([]);
  const pushToast = useAppStore((s) => s.pushToast);

  useEffect(() => {
    backend
      .listTemplates()
      .then(setTemplates)
      .catch((e) => pushToast(`${t.toast.error}: ${String(e)}`, "err"));
  }, [pushToast]);

  if (templates.length === 0) {
    return (
      <div className={styles.templates_bar}>
        <span className={styles.templates_label}>{t.oql.presets.label}</span>
        <span className={styles.placeholder}>…</span>
      </div>
    );
  }

  // Показываем первые 5 в баре, остальные доступны через "Шаблоны" в actions.
  const visible = templates.slice(0, 5);

  return (
    <div className={styles.templates_bar}>
      <span className={styles.templates_label}>{t.oql.presets.label}</span>
      {visible.map((tpl) => (
        <button
          key={tpl.id}
          className={styles.template_btn}
          title={tpl.description}
          onClick={() => onLoadTemplate(tpl.query)}
        >
          <Icon name="FileText" size={11} color="var(--o-text-3)" />
          {tpl.label}
        </button>
      ))}
    </div>
  );
}
