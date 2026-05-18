// Shared design-system tokens для всех charts (Sprint 2 Phase C).
// Источник правды — CSS-переменные в global.css; здесь только JS-фолбэки на
// случай если Recharts требует hex literal (SVG fill в legends).

export const CHART_COLORS = {
  primary: "#0F766E",     // --o-accent
  primarySoft: "#5EEAD4", // --o-accent-soft
  err: "#DC2626",         // --o-err
  warn: "#F59E0B",        // --o-warn
  ok: "#15803D",          // --o-ok
  mute: "#A3A3A3",        // --o-text-3
  text2: "#525252",       // --o-text-2
  text1: "#171717",       // --o-text-1
  grid: "#EDEDED",        // --o-border-2
  panel: "#FFFFFF",       // --o-panel
};

// Палитра для distinct categories (process_role, event_type, ...). Замостить
// design-system colors + complementary hues, чтобы 6-8 категорий легко
// различались на одном графике.
export const CATEGORICAL_PALETTE = [
  "#0F766E", // teal
  "#7C3AED", // violet
  "#F59E0B", // amber
  "#0EA5E9", // sky
  "#DC2626", // red
  "#15803D", // green
  "#EC4899", // pink
  "#737373", // neutral
];

export const CHART_FONT = {
  axis: "Inter, system-ui, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace",
};

export const AXIS_TICK_STYLE = {
  fontSize: 11,
  fill: CHART_COLORS.text2,
  fontFamily: CHART_FONT.axis,
};

export const TOOLTIP_BG = CHART_COLORS.panel;
export const TOOLTIP_BORDER = CHART_COLORS.grid;
