import type { IconName } from "@/components/icons/Icon";
import type { ScreenId } from "@/store/appStore";

export interface NavItem {
  id: ScreenId;
  label: string;
  icon: IconName;
  group: "live" | "analyze" | "config" | "manage";
  enabled: boolean;
  tooltip?: string;
}

export const NAV_ITEMS: NavItem[] = [
  { id: "oql", label: "OptimyzerQL", icon: "Terminal", group: "manage", enabled: true },

  { id: "dashboard",  label: "Operations",        icon: "Gauge",      group: "live",    enabled: false, tooltip: "Module 2: Real-time monitoring" },
  { id: "apdex",      label: "Apdex & SLA",       icon: "Trend",      group: "live",    enabled: false, tooltip: "Module 2: Real-time monitoring" },
  { id: "workbench",  label: "Investigation",     icon: "Layers",     group: "live",    enabled: false, tooltip: "Module 3: Investigation Workbench" },

  { id: "queries",    label: "Slow Queries",      icon: "Database",   group: "analyze", enabled: false, tooltip: "Module 3" },
  { id: "locks",      label: "Locks & Deadlocks", icon: "Lock",       group: "analyze", enabled: false, tooltip: "Module 3" },
  { id: "cluster",    label: "Cluster Health",    icon: "Cluster",    group: "analyze", enabled: false, tooltip: "Module 2" },
  { id: "indexes",    label: "Indexes & Stats",   icon: "HardDrive",  group: "analyze", enabled: false, tooltip: "Module 4" },
  { id: "profiler",   label: "BSL Profiler",      icon: "Code",       group: "analyze", enabled: false, tooltip: "Module 4" },

  { id: "health",     label: "Health Scan",       icon: "Scan",       group: "config",  enabled: false, tooltip: "Module 5" },
  { id: "compare",    label: "Compare",           icon: "GitCompare", group: "config",  enabled: false, tooltip: "Module 5" },
  { id: "predictive", label: "Predictive",        icon: "Brain",      group: "config",  enabled: false, tooltip: "Module 6" },

  { id: "resolution", label: "Resolution",        icon: "Workflow",   group: "manage",  enabled: false, tooltip: "Module 4" },
  { id: "multibase",  label: "Multi-base",        icon: "Globe",      group: "manage",  enabled: false, tooltip: "Module 6" },
  { id: "knowledge",  label: "Knowledge Base",    icon: "Book",       group: "manage",  enabled: false, tooltip: "Module 7" },
  { id: "alerts",     label: "Alerts",            icon: "Bell",       group: "manage",  enabled: false, tooltip: "Module 2" },
  { id: "reports",    label: "Reports",           icon: "FileText",   group: "manage",  enabled: false, tooltip: "Module 3" },
  { id: "mobile",     label: "Mobile Companion",  icon: "Phone",      group: "manage",  enabled: false, tooltip: "Module 6" },
];

export const GROUPS: { name: string; key: NavItem["group"] }[] = [
  { name: "LIVE",    key: "live" },
  { name: "ANALYZE", key: "analyze" },
  { name: "CONFIG",  key: "config" },
  { name: "MANAGE",  key: "manage" },
];
