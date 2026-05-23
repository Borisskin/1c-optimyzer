// Общий wrapper для chart-компонентов: empty / loading / error state +
// фиксированная высота. Главная цель — единообразный пустой/ошибочный вид
// во всех views и предсказуемый layout при ленивых данных.

import type { ReactNode } from "react";
import { Icon } from "@/components/icons/Icon";

export interface ChartShellProps {
  isLoading?: boolean;
  hasData: boolean;
  error?: string | null;
  emptyMessage?: string;
  height?: number | string;
  children: ReactNode;
}

export function ChartShell({
  isLoading,
  hasData,
  error,
  emptyMessage = "Нет данных",
  height = 240,
  children,
}: ChartShellProps) {
  const wrapStyle = { width: "100%", height, position: "relative" as const };

  if (error) {
    return (
      <div style={wrapStyle}>
        <div style={center}>
          <Icon name="AlertTriangle" size={20} color="var(--o-err)" />
          <div style={msgStyle("var(--o-err)")}>{error}</div>
        </div>
      </div>
    );
  }
  if (isLoading) {
    return (
      <div style={wrapStyle}>
        <div style={center}>
          <Icon name="Refresh" size={18} color="var(--o-text-3)" className="spin" />
          <div style={msgStyle("var(--o-text-3)")}>Загрузка…</div>
        </div>
      </div>
    );
  }
  if (!hasData) {
    return (
      <div style={wrapStyle}>
        <div style={center}>
          <Icon name="Circle" size={16} color="var(--o-text-3)" />
          <div style={msgStyle("var(--o-text-3)")}>{emptyMessage}</div>
        </div>
      </div>
    );
  }
  return <div style={wrapStyle}>{children}</div>;
}

const center = {
  position: "absolute" as const,
  inset: 0,
  display: "flex",
  flexDirection: "column" as const,
  alignItems: "center",
  justifyContent: "center",
  gap: 8,
};

const msgStyle = (color: string) => ({
  fontSize: 12,
  color,
  fontFamily: "var(--o-font-mono)",
});
