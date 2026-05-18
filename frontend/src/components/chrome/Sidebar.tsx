import { Icon } from "@/components/icons/Icon";
import { useAppStore } from "@/store/appStore";
import { t } from "@/i18n/ru";
import { GROUPS, NAV_ITEMS } from "./nav";
import styles from "./Sidebar.module.css";

export function Sidebar() {
  const open = useAppStore((s) => s.sidebarOpen);
  const toggle = useAppStore((s) => s.toggleSidebar);
  const current = useAppStore((s) => s.currentScreen);
  const setScreen = useAppStore((s) => s.setScreen);
  const pushToast = useAppStore((s) => s.pushToast);

  return (
    <aside className={styles.sidebar}>
      <nav className={styles.nav}>
        {GROUPS.map((g) => {
          const items = NAV_ITEMS.filter((n) => n.group === g.key);
          if (items.length === 0) return null;
          return (
            <div key={g.key} className={styles.group}>
              {open ? (
                <div className={styles.group_label}>{g.name}</div>
              ) : (
                <div className={styles.group_div} />
              )}
              {items.map((n) => {
                const active = current === n.id;
                const disabled = !n.enabled;
                return (
                  <button
                    key={n.id}
                    onClick={() => {
                      if (disabled) {
                        pushToast(n.tooltip || t.sidebar.soon, "info");
                        return;
                      }
                      setScreen(n.id);
                    }}
                    className={[
                      styles.item,
                      open ? styles.item_open : styles.item_collapsed,
                      active ? styles.item_active : "",
                      disabled ? styles.item_disabled : "",
                    ].join(" ")}
                    title={!open || disabled ? n.label + (n.tooltip ? ` — ${n.tooltip}` : "") : undefined}
                  >
                    {active && <span className={styles.item_marker} />}
                    <Icon
                      name={n.icon}
                      size={15}
                      color={active ? "var(--o-accent)" : "var(--o-text-2)"}
                    />
                    {open && <span className={styles.item_label}>{n.label}</span>}
                    {open && disabled && <span className={styles.item_pill}>{t.sidebar.soon}</span>}
                  </button>
                );
              })}
            </div>
          );
        })}
      </nav>
      <div className={styles.footer}>
        <button onClick={toggle} className={styles.collapse}>
          <Icon name={open ? "ChevronLeft" : "ChevronRight"} size={13} />
          {open && <span>{t.sidebar.collapse}</span>}
        </button>
      </div>
    </aside>
  );
}
