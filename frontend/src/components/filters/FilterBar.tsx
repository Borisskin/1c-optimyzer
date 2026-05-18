// FilterBar — постоянная панель over views (Sprint 2 Phase E, ADR-017).
// Показывает active CrossFilters как chips; клик на × снимает фильтр.
// Если фильтров нет — компактный hint "Нет активных фильтров".

import { Icon } from "@/components/icons/Icon";
import { useAppStore } from "@/store/appStore";
import styles from "./FilterBar.module.css";

export function FilterBar() {
  const filters = useAppStore((s) => s.filters);
  const setFilters = useAppStore((s) => s.setFilters);
  const clearFilters = useAppStore((s) => s.clearFilters);

  const chips: Array<{ key: keyof typeof filters; label: string; value: string }> = [];

  if (filters.time_from || filters.time_to) {
    const from = filters.time_from ? short(filters.time_from) : "—";
    const to = filters.time_to ? short(filters.time_to) : "—";
    chips.push({
      key: "time_from",
      label: "Время",
      value: `${from} — ${to}`,
    });
  }
  if (filters.process_role) {
    chips.push({ key: "process_role", label: "Роль", value: filters.process_role });
  }
  if (filters.event_type) {
    chips.push({ key: "event_type", label: "Тип", value: filters.event_type });
  }

  if (chips.length === 0) {
    return (
      <div className={styles.bar}>
        <span className={styles.hint}>
          <Icon name="Filter" size={11} color="var(--o-text-3)" /> Нет активных фильтров
        </span>
      </div>
    );
  }

  return (
    <div className={styles.bar}>
      <span className={styles.hint}>
        <Icon name="Filter" size={11} color="var(--o-accent)" /> Фильтры:
      </span>
      {chips.map((c) => (
        <span key={c.key} className={styles.chip}>
          <span className={styles.chip_label}>{c.label}:</span>
          <span className={styles.chip_value}>{c.value}</span>
          <button
            className={styles.chip_x}
            onClick={() => {
              if (c.key === "time_from") setFilters({ time_from: null, time_to: null });
              else setFilters({ [c.key]: null } as Partial<typeof filters>);
            }}
            title="Снять фильтр"
            type="button"
          >
            ×
          </button>
        </span>
      ))}
      <button className={styles.clear_btn} onClick={clearFilters} type="button">
        Очистить всё
      </button>
    </div>
  );
}

function short(iso: string): string {
  // ISO -> HH:MM (для compact display в chip)
  if (iso.length >= 16) return iso.slice(11, 16);
  if (iso.length >= 10) return iso.slice(0, 10);
  return iso;
}
