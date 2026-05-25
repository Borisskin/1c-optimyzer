/**
 * Sprint 8 Phase B.5 — React wrapper для pev2 (PG plan visualization).
 *
 * Использует Web Component <pev2-plan> зарегистрированный в pev2-wrapper.
 * React просто рендерит element как обычный HTML — pev2 (Vue под капотом)
 * handles интерактивность.
 *
 * Flow:
 *   1. Юзер просматривает PG план из ТЖ архива в PgPlanTextView (B.2)
 *   2. Если PG connection настроен в Settings → button «Получить интерактивный план»
 *   3. Click → backend re-EXPLAIN → JSON план
 *   4. Этот компонент рендерится с planJson
 */

import { useEffect, useRef } from "react";
import { ensurePev2Registered } from "@/components/vendors/pev2-wrapper";
import styles from "./Pev2PlanVisualization.module.css";

interface Props {
  /** JSON план от backend (re_explain result.plan_json) — это уже JSON string. */
  planJson: string;
  /** Оригинальный SQL запрос — pev2 показывает его на отдельной tab для context. */
  planQuery: string;
}

export function Pev2PlanVisualization({ planJson, planQuery }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Lazy register custom element на mount. Идемпотентно.
  useEffect(() => {
    ensurePev2Registered();
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>
          <span className={styles.engineBadge}>PostgreSQL</span>
          Интерактивный план (pev2)
        </span>
        <span className={styles.subtitle}>
          Кликайте на узлы для деталей. Tab «Query» — SQL запроса.
        </span>
      </div>
      <div ref={containerRef} className={styles.viz}>
        <pev2-plan plan-source={planJson} plan-query={planQuery} />
      </div>
    </div>
  );
}
