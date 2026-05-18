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

const tooltip = (module: number) => `${t.sidebar.tooltipModule} ${module}`;

export const NAV_ITEMS: NavItem[] = [
  { id: "sql", label: t.sidebar.items.sql, icon: "Terminal", group: "analyze", enabled: true },

  { id: "dashboard",  label: t.sidebar.items.dashboard, icon: "Gauge",      group: "live",    enabled: false, tooltip: tooltip(2) },
  { id: "apdex",      label: t.sidebar.items.apdex,     icon: "Trend",      group: "live",    enabled: false, tooltip: tooltip(2) },
  { id: "workbench",  label: t.sidebar.items.workbench, icon: "Layers",     group: "live",    enabled: false, tooltip: tooltip(3) },

  { id: "slow-queries", label: t.sidebar.items.queries, icon: "Database",   group: "analyze", enabled: false, tooltip: tooltip(3) },
  { id: "locks",      label: t.sidebar.items.locks,     icon: "Lock",       group: "analyze", enabled: false, tooltip: tooltip(3) },
  { id: "cluster",    label: t.sidebar.items.cluster,   icon: "Cluster",    group: "analyze", enabled: false, tooltip: tooltip(2) },
  { id: "indexes",    label: t.sidebar.items.indexes,   icon: "HardDrive",  group: "analyze", enabled: false, tooltip: tooltip(4) },
  { id: "profiler",   label: t.sidebar.items.profiler,  icon: "Code",       group: "analyze", enabled: false, tooltip: tooltip(4) },

  { id: "health",     label: t.sidebar.items.health,    icon: "Scan",       group: "config",  enabled: false, tooltip: tooltip(5) },
  { id: "comparison", label: t.sidebar.items.compare,   icon: "GitCompare", group: "config",  enabled: false, tooltip: tooltip(5) },
  { id: "predictive", label: t.sidebar.items.predictive, icon: "Brain",     group: "config",  enabled: false, tooltip: tooltip(6) },

  { id: "resolution", label: t.sidebar.items.resolution, icon: "Workflow",  group: "manage",  enabled: false, tooltip: tooltip(4) },
  { id: "multibase",  label: t.sidebar.items.multibase,  icon: "Globe",     group: "manage",  enabled: false, tooltip: tooltip(6) },
  { id: "knowledge",  label: t.sidebar.items.knowledge,  icon: "Book",      group: "manage",  enabled: false, tooltip: tooltip(7) },
  { id: "alerts",     label: t.sidebar.items.alerts,     icon: "Bell",      group: "manage",  enabled: false, tooltip: tooltip(2) },
  { id: "reports",    label: t.sidebar.items.reports,    icon: "FileText",  group: "manage",  enabled: false, tooltip: tooltip(3) },
  { id: "mobile",     label: t.sidebar.items.mobile,     icon: "Phone",     group: "manage",  enabled: false, tooltip: tooltip(6) },
];

export const GROUPS: { name: string; key: NavItem["group"] }[] = [
  { name: t.sidebar.groups.live,    key: "live" },
  { name: t.sidebar.groups.analyze, key: "analyze" },
  { name: t.sidebar.groups.config,  key: "config" },
  { name: t.sidebar.groups.manage,  key: "manage" },
];
