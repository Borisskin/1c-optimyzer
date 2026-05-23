/**
 * PulseLogo — официальный логотип Optimyzer (Pulse).
 *
 * Тил-кольцо + три бара (heartbeat / pulse). Должен использоваться ВЕЗДЕ
 * где раньше был placeholder «1C» (TopBar, SettingsDialog, AccountTab,
 * cabinet, landing, docs). Согласован 23.05.2026.
 *
 * Базируется на DESIGN_CONCEPT/index.html — viewBox 0 0 64 64,
 * stroke #0EA5A4, bars #0F1B2D / #0EA5A4.
 */

interface Props {
  /** Размер в пикселях (ширина=высота, viewBox 64x64). */
  size?: number;
  /** Дополнительный className для wrapper'а. */
  className?: string;
  /** Стиль (например marginRight). */
  style?: React.CSSProperties;
}

export function PulseLogo({ size = 32, className, style }: Props) {
  return (
    <svg
      viewBox="0 0 64 64"
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      className={className}
      style={style}
      aria-hidden="true"
    >
      <circle cx="32" cy="32" r="26" fill="none" stroke="#0EA5A4" strokeWidth="6" />
      <rect x="19" y="36" width="6" height="12" rx="1.5" fill="#0F1B2D" />
      <rect x="29" y="28" width="6" height="20" rx="1.5" fill="#0F1B2D" />
      <rect x="39" y="20" width="6" height="28" rx="1.5" fill="#0EA5A4" />
    </svg>
  );
}
