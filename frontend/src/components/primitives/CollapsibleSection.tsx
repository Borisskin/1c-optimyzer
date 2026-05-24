/**
 * Sprint 7 (post-Phase F) — переиспользуемый wrapper для секций, которые
 * пользователь может свернуть/развернуть, когда мешают другим блокам на экране.
 *
 * Применяется когда:
 *   - Блок занимает много места (AI explanation card, длинный text plan)
 *   - Пользователь уже посмотрел контент и хочет освободить место
 *   - На экране несколько таких блоков (Plan Analyzer: AI card + viz + stats)
 *
 * Default state — expanded (юзер видит фичу из коробки). Можно переопределить
 * через `defaultCollapsed`. State per-session (не сохраняется в localStorage —
 * меньше surprise factor «вчера было видно, сегодня нет»).
 *
 * NB: НЕ используем стрелочки ▶▼ (memory rule «no disclosure triangles»).
 * Только текстовая кнопка «Свернуть» / «Развернуть» — clean и однозначно.
 *
 * Применение в codebase сейчас: PlanAnalyzer → AiPlanExplanationCard.
 * Дальше — добавлять по мере появления конкретной боли «эта секция мешает».
 *
 * Пример:
 *   <CollapsibleSection
 *     title="AI-объяснение плана"
 *     subtitle={response && <SevBadge sev={response.overall_severity} />}
 *   >
 *     <AiCard ... />
 *   </CollapsibleSection>
 */

import { useState, type ReactNode } from "react";
import styles from "./CollapsibleSection.module.css";

interface Props {
  /** Заголовок секции — всегда виден, даже когда collapsed. */
  title: string;
  /** Опциональный подзаголовок справа от title (статус, badge, count). */
  subtitle?: ReactNode;
  /** Дополнительный action слева от кнопки свернуть/развернуть. */
  headerRight?: ReactNode;
  /** Если true — секция изначально свёрнута. По умолчанию expanded. */
  defaultCollapsed?: boolean;
  /** Контент. Скрывается через display:none когда collapsed. */
  children: ReactNode;
  /** Кастомный className для root (опционально, чтобы родитель управлял spacing). */
  className?: string;
}

export function CollapsibleSection({
  title,
  subtitle,
  headerRight,
  defaultCollapsed = false,
  children,
  className,
}: Props) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <div className={`${styles.root} ${className ?? ""}`}>
      <div className={styles.header}>
        <div className={styles.titleBlock}>
          <h3 className={styles.title}>{title}</h3>
          {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
        </div>
        <div className={styles.actions}>
          {headerRight}
          <button
            type="button"
            className={styles.toggleButton}
            onClick={() => setCollapsed((v) => !v)}
            aria-expanded={!collapsed}
          >
            {collapsed ? "Развернуть" : "Свернуть"}
          </button>
        </div>
      </div>
      {/* display:none через CSS, не conditional render — сохраняем DOM состояние
          дочерних компонентов (например AI response не теряется при свёртывании). */}
      <div className={collapsed ? styles.bodyCollapsed : styles.body}>
        {children}
      </div>
    </div>
  );
}
