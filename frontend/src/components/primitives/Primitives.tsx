// UI primitives — Badge, Sev, Panel, PageHeader, KPI, Tabs, SegBtn, Th, Td, KBD.
// Портировано из design/opt/shared.jsx с переводом на CSS Modules + design-tokens.

import type { CSSProperties, ReactNode } from "react";
import { Icon, type IconName } from "@/components/icons/Icon";
import styles from "./Primitives.module.css";

// ---------- Sev (severity dot) ----------

export type SevLevel = "ok" | "warn" | "err" | "info" | "mute";

export function Sev({ level, size = 10 }: { level: SevLevel; size?: number }) {
  const colors: Record<SevLevel, string> = {
    ok: "var(--o-ok)",
    warn: "var(--o-warn)",
    err: "var(--o-err)",
    info: "var(--o-info)",
    mute: "var(--o-text-4)",
  };
  return (
    <span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        borderRadius: "50%",
        background: colors[level],
      }}
    />
  );
}

// ---------- Badge ----------

export type BadgeTone = "ok" | "warn" | "err" | "info" | "teal" | "mute" | "ink";

export function Badge({
  tone = "mute",
  children,
  mono = false,
  className,
}: {
  tone?: BadgeTone;
  children: ReactNode;
  mono?: boolean;
  className?: string;
}) {
  return (
    <span
      className={[
        styles.badge,
        styles[`badge_${tone}`],
        mono ? "mono" : "",
        className || "",
      ].join(" ")}
    >
      {children}
    </span>
  );
}

// ---------- KBD ----------

export function KBD({ children }: { children: ReactNode }) {
  return <kbd>{children}</kbd>;
}

// ---------- Panel ----------

export function Panel({
  title,
  sub,
  right,
  children,
  className,
  dense,
  pad = true,
}: {
  title?: ReactNode;
  sub?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  dense?: boolean;
  pad?: boolean;
}) {
  return (
    <section className={[styles.panel, className || ""].join(" ")}>
      {(title || right) && (
        <header className={dense ? styles.panel_header_dense : styles.panel_header}>
          {title && <h3 className={styles.panel_title}>{title}</h3>}
          {sub && <span className={styles.panel_sub}>{sub}</span>}
          <div className={styles.panel_right}>{right}</div>
        </header>
      )}
      <div className={pad ? (dense ? styles.panel_body_dense : styles.panel_body) : undefined}>
        {children}
      </div>
    </section>
  );
}

// ---------- PageHeader ----------

export type Breadcrumb = string | { label: string; onClick: () => void };

export function PageHeader({
  title,
  sub,
  right,
  breadcrumbs,
  kpis,
}: {
  title: ReactNode;
  sub?: ReactNode;
  right?: ReactNode;
  breadcrumbs?: Breadcrumb[];
  kpis?: ReactNode;
}) {
  return (
    <div className={styles.page_header}>
      {breadcrumbs && (
        <div className={styles.breadcrumbs}>
          {breadcrumbs.map((b, i) => {
            const label = typeof b === "string" ? b : b.label;
            const onClick = typeof b === "object" ? b.onClick : undefined;
            return (
              <span key={i} className={styles.crumb}>
                {i > 0 && <Icon name="ChevronRight" size={11} />}
                {onClick ? (
                  <button
                    type="button"
                    onClick={onClick}
                    className={styles.crumb_link}
                  >
                    {label}
                  </button>
                ) : (
                  <span>{label}</span>
                )}
              </span>
            );
          })}
        </div>
      )}
      <div className={styles.title_row}>
        <h1 className={styles.title}>{title}</h1>
        {sub && <p className={styles.sub}>{sub}</p>}
        <div className={styles.title_right}>{right}</div>
      </div>
      {kpis && <div className={styles.kpis}>{kpis}</div>}
    </div>
  );
}

// ---------- KPI ----------

export function KPI({
  label,
  value,
  sub,
  tone = "ink",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "ink" | "ok" | "warn" | "err" | "teal";
}) {
  const colorVar: Record<string, string> = {
    ink: "var(--o-text-1)",
    ok: "var(--o-ok)",
    warn: "var(--o-warn)",
    err: "var(--o-err)",
    teal: "var(--o-accent)",
  };
  return (
    <div className={styles.kpi}>
      <div className={styles.kpi_label}>{label}</div>
      <div className={`${styles.kpi_value} tnum`} style={{ color: colorVar[tone] }}>
        {value}
      </div>
      {sub && <div className={styles.kpi_sub}>{sub}</div>}
    </div>
  );
}

// ---------- Tabs ----------

export interface TabSpec {
  id: string;
  label: ReactNode;
  icon?: IconName;
  count?: number;
}

export function Tabs({
  tabs,
  value,
  onChange,
  dense = false,
}: {
  tabs: TabSpec[];
  value: string;
  onChange: (id: string) => void;
  dense?: boolean;
}) {
  return (
    <div className={dense ? styles.tabs_dense : styles.tabs}>
      {tabs.map((t) => {
        const active = t.id === value;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={`${styles.tab} ${active ? styles.tab_active : ""}`}
          >
            {t.icon && <Icon name={t.icon} size={12} />}
            <span>{t.label}</span>
            {t.count != null && (
              <span className={`${styles.tab_count} ${active ? styles.tab_count_active : ""}`}>
                {t.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ---------- Segmented buttons ----------

export function SegBtn({
  children,
  active,
  onClick,
}: {
  children: ReactNode;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button onClick={onClick} className={`${styles.seg_btn} ${active ? styles.seg_btn_active : ""}`}>
      {children}
    </button>
  );
}

export function SegGroup({ children }: { children: ReactNode }) {
  return <div className={styles.seg_group}>{children}</div>;
}

// ---------- Table primitives ----------

export function Th({
  children,
  w,
  align = "left",
  className,
}: {
  children: ReactNode;
  w?: string;
  align?: "left" | "right" | "center";
  className?: string;
}) {
  const style: CSSProperties = { width: w, textAlign: align };
  return (
    <th className={`${styles.th} ${className || ""}`} style={style}>
      {children}
    </th>
  );
}

export function Td({
  children,
  align = "left",
  mono = false,
  className,
}: {
  children: ReactNode;
  align?: "left" | "right" | "center";
  mono?: boolean;
  className?: string;
}) {
  const style: CSSProperties = { textAlign: align };
  return (
    <td className={`${styles.td} ${mono ? "mono tnum" : ""} ${className || ""}`} style={style}>
      {children}
    </td>
  );
}

// ---------- CodeBlock ----------

export function CodeBlock({ children, className }: { children: ReactNode; className?: string }) {
  return <pre className={`${styles.codeblock} mono ${className || ""}`}>{children}</pre>;
}
