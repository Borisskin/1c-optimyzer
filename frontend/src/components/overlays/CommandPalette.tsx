import { useEffect, useMemo, useState } from "react";
import { Icon, type IconName } from "@/components/icons/Icon";
import { KBD } from "@/components/primitives/Primitives";
import { useAppStore } from "@/store/appStore";
import { NAV_ITEMS } from "@/components/chrome/nav";
import { t, format } from "@/i18n/ru";
import styles from "./CommandPalette.module.css";

export interface CommandItem {
  id: string;
  label: string;
  hint: string;
  icon: IconName;
  action: () => void;
}

export function CommandPalette({
  open,
  onClose,
  onLoadArchive,
}: {
  open: boolean;
  onClose: () => void;
  onLoadArchive: () => void;
}) {
  const [q, setQ] = useState("");
  const setScreen = useAppStore((s) => s.setScreen);
  const pushToast = useAppStore((s) => s.pushToast);

  useEffect(() => {
    if (open) setQ("");
  }, [open]);

  const items: CommandItem[] = useMemo(() => {
    return [
      {
        id: "open-archive",
        label: t.cmdpalette.commands.loadFolder,
        hint: t.cmdpalette.hints.file,
        icon: "Upload",
        action: () => {
          onClose();
          onLoadArchive();
        },
      },
      {
        id: "recent",
        label: t.cmdpalette.commands.recentSources,
        hint: t.cmdpalette.hints.list,
        icon: "FileText",
        action: () => {
          onClose();
          pushToast(t.cmdpalette.commands.recentSourcesHint, "info");
        },
      },
      ...NAV_ITEMS.filter((n) => n.enabled).map((n) => ({
        id: `nav-${n.id}`,
        label: format(t.cmdpalette.commands.goTo, { label: n.label }),
        hint: t.cmdpalette.hints.navigate,
        icon: n.icon,
        action: () => {
          setScreen(n.id);
          onClose();
        },
      })),
      {
        id: "about",
        label: t.cmdpalette.commands.about,
        hint: t.cmdpalette.hints.info,
        icon: "Info",
        action: () => {
          onClose();
          pushToast(t.cmdpalette.aboutToast, "info");
        },
      },
    ];
  }, [onClose, onLoadArchive, pushToast, setScreen]);

  if (!open) return null;

  const filtered = items.filter((i) => i.label.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className={styles.backdrop} onMouseDown={onClose}>
      <div className={styles.modal} onMouseDown={(e) => e.stopPropagation()}>
        <div className={styles.head}>
          <Icon name="Search" size={15} color="var(--o-text-3)" />
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t.cmdpalette.placeholder}
            className={styles.input}
            onKeyDown={(e) => {
              if (e.key === "Enter" && filtered[0]) {
                filtered[0].action();
              }
            }}
          />
          <span className={styles.esc}>{t.cmdpalette.escClose}</span>
        </div>
        <div className={styles.list}>
          {filtered.length === 0 && <div className={styles.empty}>{t.cmdpalette.noResults}</div>}
          {filtered.slice(0, 30).map((it) => (
            <div key={it.id} className={styles.row} onClick={it.action}>
              <Icon name={it.icon} size={14} color="var(--o-text-2)" />
              <span className={styles.row_label}>{it.label}</span>
              <span className={styles.row_hint}>{it.hint}</span>
            </div>
          ))}
        </div>
        <div className={styles.foot}>
          <span>
            <KBD>↑</KBD>
            <KBD>↓</KBD> {t.cmdpalette.keys.navigate}
          </span>
          <span>
            <KBD>↵</KBD> {t.cmdpalette.keys.open}
          </span>
          <span>
            <KBD>Esc</KBD> {t.cmdpalette.keys.close}
          </span>
        </div>
      </div>
    </div>
  );
}
