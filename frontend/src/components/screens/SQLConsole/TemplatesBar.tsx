// Dropdown templates picker для SQLConsole. По клику на template — load в editor.

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { backend, type SqlTemplate } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import styles from "./SQLConsole.module.css";

interface Props {
  onLoadTemplate: (sql: string) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  performance: "Производительность",
  locks: "Блокировки",
  errors: "Ошибки",
  memory: "Память",
  stats: "Статистика",
};

export function TemplatesBar({ onLoadTemplate }: Props) {
  const [templates, setTemplates] = useState<SqlTemplate[]>([]);
  const [open, setOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>("performance");
  const pushToast = useAppStore((s) => s.pushToast);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    backend
      .listSqlTemplates()
      .then(setTemplates)
      .catch((e) => pushToast(`${t.toast.error}: ${String(e)}`, "err"));
  }, [pushToast]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const categories = Array.from(new Set(templates.map((tpl) => tpl.category)));
  const filtered = templates.filter((tpl) => tpl.category === activeCategory);

  return (
    <div className={styles.saved_menu} ref={dropdownRef}>
      <button
        className={styles.template_btn}
        onClick={() => setOpen((v) => !v)}
        title={t.sql.presets.label}
      >
        <Icon name="FileText" size={11} color="var(--o-text-3)" />
        {t.sql.presets.label}
        <Icon name="ChevronDown" size={10} color="var(--o-text-3)" />
      </button>

      {open && (
        <div className={styles.saved_dropdown} style={{ minWidth: 360, maxHeight: 400 }}>
          <div style={tabsStyle}>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                style={tabStyle(cat === activeCategory)}
                type="button"
              >
                {CATEGORY_LABELS[cat] ?? cat}
              </button>
            ))}
          </div>
          {filtered.length === 0 ? (
            <div className={styles.saved_empty}>—</div>
          ) : (
            filtered.map((tpl) => (
              <div key={tpl.id} className={styles.saved_row}>
                <button
                  className={styles.saved_load_btn}
                  onClick={() => {
                    onLoadTemplate(tpl.sql);
                    setOpen(false);
                  }}
                  title={tpl.description}
                >
                  {tpl.label}
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

const tabsStyle: React.CSSProperties = {
  display: "flex",
  gap: 4,
  padding: "8px 8px 4px",
  borderBottom: "1px solid var(--o-border-2)",
  flexWrap: "wrap",
};

function tabStyle(active: boolean): React.CSSProperties {
  return {
    padding: "4px 8px",
    fontSize: 10.5,
    fontFamily: "var(--o-font-mono)",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    background: active ? "var(--o-accent)" : "transparent",
    color: active ? "#fff" : "var(--o-text-3)",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
  };
}
