import { Icon } from "@/components/icons/Icon";
import { useAppStore } from "@/store/appStore";
import { useDevMode } from "@/hooks/useDevMode";
import { t } from "@/i18n/ru";
import { DRILLDOWN_PARENT, GROUPS, NAV_ITEMS } from "./nav";
import styles from "./Sidebar.module.css";

export function Sidebar() {
  const open = useAppStore((s) => s.sidebarOpen);
  const toggle = useAppStore((s) => s.toggleSidebar);
  const current = useAppStore((s) => s.currentScreen);
  const setScreen = useAppStore((s) => s.setScreen);
  const pushToast = useAppStore((s) => s.pushToast);
  const devMode = useDevMode();

  // Для drill-down экранов (Anatomy / DeadlockAnatomy) подсвечиваем
  // родительский пункт в Sidebar: юзер концептуально остался внутри
  // «Бизнес-операций» / «Блокировок», просто смотрит детали одного элемента.
  const highlightedScreen = DRILLDOWN_PARENT[current] ?? current;

  return (
    <aside className={styles.sidebar}>
      <div className={`${styles.header} ${open ? styles.header_open : styles.header_collapsed}`}>
        <button
          onClick={toggle}
          className={styles.hamburger}
          title={open ? t.sidebar.collapse : t.sidebar.expand}
          aria-label={open ? t.sidebar.collapse : t.sidebar.expand}
        >
          <Icon name="Menu" size={14} />
        </button>
      </div>
      <nav className={styles.nav}>
        {GROUPS.map((g) => {
          let items = NAV_ITEMS.filter((n) => n.group === g.key);
          // Dev-only items видны только при включённом dev mode
          // (Ctrl+Shift+D или localStorage["optimyzer:dev"] = "1").
          if (!devMode) {
            items = items.filter((n) => !n.devOnly);
          }
          if (items.length === 0) return null;
          return (
            <div key={g.key} className={styles.group}>
              {open ? (
                <div className={styles.group_label}>{g.name}</div>
              ) : (
                <div className={styles.group_div} />
              )}
              {items.map((n) => {
                const active = highlightedScreen === n.id;
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
        <button
          onClick={toggle}
          className={`${styles.collapse} ${open ? styles.collapse_open : styles.collapse_collapsed}`}
        >
          <Icon name={open ? "ChevronLeft" : "ChevronRight"} size={13} />
          {open && <span>{t.sidebar.collapse}</span>}
        </button>
      </div>
    </aside>
  );
}
