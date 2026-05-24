/**
 * Sprint 7 Phase B — SSMS-style визуализация execution plan.
 *
 * Wraps html-query-plan v2.6.1 (MIT, Justin Pealing). qp.showPlan рендерит
 * HTML/SVG operator tree с tooltips (cost, rows, IO, predicates). Использует
 * XSLT transformation от SHOWPLAN XML → HTML / SVG.
 *
 * Загрузка qp.js и qp.css — через qpLoader (см. src/vendor/qpLoader.ts):
 * Vite ESM-импорт qp.js ломает strict-mode `this`, а qp.css из node_modules
 * Vite молча не подключает в lazy chunk. Поэтому грузим оба файла как
 * static assets из public/vendor/.
 *
 * Re-rendering: на каждое изменение planXml — container.innerHTML="" + showPlan,
 * чтобы не аккумулировать узлы дерева в DOM.
 */

import { useEffect, useRef, useState } from "react";
import { loadQP } from "@/vendor/qpLoader";
import styles from "./PlanVisualization.module.css";

interface Props {
  planXml: string | null;
  onError?: (err: Error) => void;
}

export function PlanVisualization({ planXml, onError }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!planXml) {
      el.innerHTML = "";
      setError(null);
      return;
    }
    let cancelled = false;
    el.innerHTML = "";
    setError(null);
    loadQP()
      .then((QP) => {
        if (cancelled) return;
        try {
          QP.showPlan(el, planXml, { jsTooltips: true });
          // Sanity check — если XSLT отдал пустоту, дадим юзеру понять.
          if (el.children.length === 0) {
            throw new Error(
              "XSLT не сгенерировал visualization. Проверьте что plan XML " +
                "содержит правильный namespace и SHOWPLAN structure.",
            );
          }
        } catch (e) {
          const msg = String(e);
          setError(msg);
          onError?.(e instanceof Error ? e : new Error(msg));
        }
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setError(e.message);
        onError?.(e);
      });
    return () => {
      cancelled = true;
    };
  }, [planXml, onError]);

  if (!planXml) {
    return (
      <div className={styles.empty}>
        Визуализация недоступна — план не загружен из файла или XML.
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorBox}>
        <div className={styles.errorTitle}>Не удалось отрендерить визуализацию</div>
        <div className={styles.errorDetail}>{error}</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.title}>Визуализация плана (SSMS-style)</div>
      <div ref={containerRef} className={styles.viz} />
    </div>
  );
}
