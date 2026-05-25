/**
 * Sprint 10 — TemplatesSelector: горизонтальные chips для выбора шаблона.
 */
import type { Template } from "../types";
import styles from "./TemplatesSelector.module.css";

interface Props {
  templates: Template[];
  activeId: string | null;
  onSelect: (template: Template) => void;
}

export function TemplatesSelector({ templates, activeId, onSelect }: Props) {
  return (
    <div className={styles.root}>
      {templates.map((t) => (
        <button
          key={t.id}
          className={[styles.chip, activeId === t.id ? styles.chip_active : ""].join(" ")}
          onClick={() => onSelect(t)}
          title={`${t.description}\n${t.volume_hint}`}
        >
          <span className={[styles.volume_dot, styles[`volume_${t.estimated_volume}`]].join(" ")} />
          {t.name}
        </button>
      ))}
    </div>
  );
}
