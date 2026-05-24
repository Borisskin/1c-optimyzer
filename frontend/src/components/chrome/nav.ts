import type { IconName } from "@/components/icons/Icon";
import type { ScreenId } from "@/store/appStore";
import { t } from "@/i18n/ru";

export interface NavItem {
  id: ScreenId;
  label: string;
  icon: IconName;
  group: "live" | "analyze" | "config" | "manage" | "dev";
  enabled: boolean;
  tooltip?: string;
  /** Текст keyboard-шортката для отображения справа в Sidebar (Ctrl+1, Ctrl+Q …). */
  shortcut?: string;
  /** Если true — пункт показывается только когда включён dev mode
   *  (localStorage["optimyzer:dev"]="1", toggle Ctrl+Shift+D). */
  devOnly?: boolean;
}

// Sales build (v0.5.0): все disabled пункты скрыты из Sidebar — оставлено только
// 10 работающих инструментов в двух группах (Анализ + Конфигурация). Disabled
// пункты не удалены — они закомментированы ниже и при необходимости возвращаются
// одной строкой. См. docs/UI_INVENTORY_2026_05.md для полной картины.

export const NAV_ITEMS: NavItem[] = [
  // ----- ANALYZE -----
  { id: "operations",     label: t.sidebar.items.operations,     icon: "Layers",        group: "analyze", enabled: true, shortcut: "Ctrl+1" },
  { id: "sql",            label: t.sidebar.items.sql,            icon: "Terminal",      group: "analyze", enabled: true, shortcut: "Ctrl+2" },
  // Sprint 6 — восстановлен из hidden через интеграцию с bsl-language-server
  // (LGPL-3.0, 19 SDBL диагностик с полной MDO type resolution). Старый
  // regex-валидатор остался как secondary, главный источник — bsl-LS sidecar.
  // Cloud AI (Claude Sonnet 4.5) — structured explanation поверх диагностик.
  // См. docs/sales_sprint/SPRINT_6_PROMT.md.
  { id: "query-analyzer", label: t.sidebar.items.queryAnalyzer,  icon: "Code",          group: "analyze", enabled: true, shortcut: "Ctrl+Q" },
  // Sprint 7 — анализ execution plans MS SQL Server (PerformanceStudio CLI +
  // html-query-plan visualization + AI explanation). Главный premium-feature
  // оправдывающий Pro 9 900 ₽/мес. См. docs/sales_sprint/SPRINT_7_PROMT.md.
  { id: "plan-analyzer",  label: t.sidebar.items.planAnalyzer,   icon: "FileBarChart",  group: "analyze", enabled: true, shortcut: "Ctrl+P" },
  { id: "slow-queries",   label: t.sidebar.items.slowQueries,    icon: "Database",      group: "analyze", enabled: true, shortcut: "Ctrl+3" },
  { id: "locks",          label: t.sidebar.items.locksView,      icon: "Lock",          group: "analyze", enabled: true, shortcut: "Ctrl+4" },
  { id: "process-roles",  label: t.sidebar.items.processRoles,   icon: "Cluster",       group: "analyze", enabled: true, shortcut: "Ctrl+5" },
  { id: "duration",       label: t.sidebar.items.duration,       icon: "Trend",         group: "analyze", enabled: true, shortcut: "Ctrl+6" },
  { id: "errors",         label: t.sidebar.items.errors,         icon: "AlertTriangle", group: "analyze", enabled: true, shortcut: "Ctrl+7" },
  { id: "activity",       label: t.sidebar.items.activity,       icon: "Activity",      group: "analyze", enabled: true, shortcut: "Ctrl+8" },

  // ----- CONFIG -----
  { id: "comparison",     label: t.sidebar.items.comparison,     icon: "GitCompare",    group: "config",  enabled: true, shortcut: "Ctrl+9" },

  // Dev-only — видно только при localStorage["optimyzer:dev"]="1"
  { id: "dev-tools",      label: "DevTools",                     icon: "Settings",      group: "dev",     enabled: true,  devOnly: true },

  // ----- Hidden until Sprint 7+ (future modules) -----
  // Раскомментировать обратно при готовности соответствующих экранов.
  // { id: "indexes",    label: t.sidebar.items.indexes,     icon: "HardDrive",  group: "analyze", enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "profiler",   label: t.sidebar.items.profiler,    icon: "Code",       group: "analyze", enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "cluster",    label: t.sidebar.items.cluster,     icon: "Cluster",    group: "config",  enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "health",     label: t.sidebar.items.health,      icon: "Scan",       group: "config",  enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "predictive", label: t.sidebar.items.predictive,  icon: "Brain",      group: "config",  enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "dashboard",  label: t.sidebar.items.dashboard,   icon: "Gauge",      group: "live",    enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "apdex",      label: t.sidebar.items.apdex,       icon: "Trend",      group: "live",    enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "workbench",  label: t.sidebar.items.workbench,   icon: "Layers",     group: "live",    enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "resolution", label: t.sidebar.items.resolution,  icon: "Workflow",   group: "manage",  enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "multibase",  label: t.sidebar.items.multibase,   icon: "Globe",      group: "manage",  enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "knowledge",  label: t.sidebar.items.knowledge,   icon: "Book",       group: "manage",  enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "alerts",     label: t.sidebar.items.alerts,      icon: "Bell",       group: "manage",  enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "reports",    label: t.sidebar.items.reports,     icon: "FileText",   group: "manage",  enabled: false, tooltip: "Доступно в будущих обновлениях" },
  // { id: "mobile",     label: t.sidebar.items.mobile,      icon: "Phone",      group: "manage",  enabled: false, tooltip: "Доступно в будущих обновлениях" },
];

/**
 * Drill-down экраны, у которых нет своего пункта в Sidebar, но юзер
 * концептуально остался «внутри» родительского раздела.
 *
 * Sidebar использует это для подсветки: когда current === "anatomy",
 * визуально активным остаётся пункт «Бизнес-операции», потому что
 * Anatomy = детали одной операции из списка.
 */
export const DRILLDOWN_PARENT: Partial<Record<ScreenId, ScreenId>> = {
  "anatomy": "operations",
  "deadlock-anatomy": "locks",
};

export const GROUPS: { name: string; key: NavItem["group"] }[] = [
  { name: t.sidebar.groups.analyze, key: "analyze" },
  { name: t.sidebar.groups.config,  key: "config" },
  // Hidden until Sprint 7+: группы НАБЛЮДЕНИЕ и УПРАВЛЕНИЕ пока не содержат
  // ни одного работающего экрана. Раскомментировать при готовности.
  // { name: t.sidebar.groups.live,    key: "live" },
  // { name: t.sidebar.groups.manage,  key: "manage" },
  { name: "DEV",                    key: "dev" },
];
