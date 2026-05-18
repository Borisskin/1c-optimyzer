import type { IconName } from "@/components/icons/Icon";
import type { ScreenId } from "@/store/appStore";
import { t } from "@/i18n/ru";

export interface NavItem {
  id: ScreenId;
  label: string;
  icon: IconName;
  group: "live" | "analyze" | "config" | "manage";
  enabled: boolean;
  tooltip?: string;
}

const futureTooltip = "Доступно в будущих обновлениях";

export const NAV_ITEMS: NavItem[] = [
  // ----- ANALYZE (Sprint 2 active set) -----
  { id: "sql",           label: t.sidebar.items.sql,           icon: "Terminal",   group: "analyze", enabled: true },
  { id: "slow-queries",  label: t.sidebar.items.slowQueries,   icon: "Database",   group: "analyze", enabled: true },
  { id: "locks",         label: t.sidebar.items.locksView,     icon: "Lock",       group: "analyze", enabled: true },
  { id: "process-roles", label: t.sidebar.items.processRoles,  icon: "Cluster",    group: "analyze", enabled: true },
  { id: "duration",      label: t.sidebar.items.duration,      icon: "Trend",      group: "analyze", enabled: true },
  { id: "errors",        label: t.sidebar.items.errors,        icon: "AlertTriangle", group: "analyze", enabled: true },
  { id: "activity",      label: t.sidebar.items.activity,      icon: "Activity",   group: "analyze", enabled: true },

  // ----- CONFIG -----
  { id: "comparison",    label: t.sidebar.items.comparison,    icon: "GitCompare", group: "config",  enabled: true },

  // ----- Disabled (future modules) -----
  { id: "dashboard",  label: t.sidebar.items.dashboard,   icon: "Gauge",      group: "live",    enabled: false, tooltip: futureTooltip },
  { id: "apdex",      label: t.sidebar.items.apdex,       icon: "Trend",      group: "live",    enabled: false, tooltip: futureTooltip },
  { id: "workbench",  label: t.sidebar.items.workbench,   icon: "Layers",     group: "live",    enabled: false, tooltip: futureTooltip },

  { id: "cluster",    label: t.sidebar.items.cluster,     icon: "Cluster",    group: "config",  enabled: false, tooltip: futureTooltip },
  { id: "indexes",    label: t.sidebar.items.indexes,     icon: "HardDrive",  group: "analyze", enabled: false, tooltip: futureTooltip },
  { id: "profiler",   label: t.sidebar.items.profiler,    icon: "Code",       group: "analyze", enabled: false, tooltip: futureTooltip },

  { id: "health",     label: t.sidebar.items.health,      icon: "Scan",       group: "config",  enabled: false, tooltip: futureTooltip },
  { id: "predictive", label: t.sidebar.items.predictive,  icon: "Brain",      group: "config",  enabled: false, tooltip: futureTooltip },

  { id: "resolution", label: t.sidebar.items.resolution,  icon: "Workflow",   group: "manage",  enabled: false, tooltip: futureTooltip },
  { id: "multibase",  label: t.sidebar.items.multibase,   icon: "Globe",      group: "manage",  enabled: false, tooltip: futureTooltip },
  { id: "knowledge",  label: t.sidebar.items.knowledge,   icon: "Book",       group: "manage",  enabled: false, tooltip: futureTooltip },
  { id: "alerts",     label: t.sidebar.items.alerts,      icon: "Bell",       group: "manage",  enabled: false, tooltip: futureTooltip },
  { id: "reports",    label: t.sidebar.items.reports,     icon: "FileText",   group: "manage",  enabled: false, tooltip: futureTooltip },
  { id: "mobile",     label: t.sidebar.items.mobile,      icon: "Phone",      group: "manage",  enabled: false, tooltip: futureTooltip },
];

export const GROUPS: { name: string; key: NavItem["group"] }[] = [
  { name: t.sidebar.groups.analyze, key: "analyze" },
  { name: t.sidebar.groups.config,  key: "config" },
  { name: t.sidebar.groups.live,    key: "live" },
  { name: t.sidebar.groups.manage,  key: "manage" },
];
