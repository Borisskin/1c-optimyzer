/**
 * Sprint 7 Phase B — SSMS-style визуализация execution plan.
 *
 * Wraps html-query-plan v2.6.1 (MIT, Justin Pealing). qp.showPlan рендерит
 * SVG operator tree с tooltips (cost, rows, IO, predicates). Использует
 * XSLT transformation от SHOWPLAN XML → HTML / SVG.
 *
 * CSS импортируется из node_modules — Vite разрешает относительный
 * url('qp_icons.png') автоматически.
 *
 * Re-rendering: на каждое изменение planXml — container.innerHTML="" + showPlan,
 * чтобы не аккумулировать узлы дерева в DOM.
 */

import { useEffect, useRef, useState } from "react";
import "html-query-plan/css/qp.css";
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
          // Detailed diagnostic: hwh визуализация выходит «пустой» (нулевая
          // высота, qp-root отсутствует, инлайн стили перебивают и т.п.)
          const qpRoot = el.querySelector(".qp-root");
          const rect = el.getBoundingClientRect();
          const innerLen = el.innerHTML.length;
          // eslint-disable-next-line no-console
          console.log("[PlanViz] showPlan done", {
            children: el.children.length,
            innerHtmlLen: innerLen,
            qpRootFound: !!qpRoot,
            qpRootRect: qpRoot ? qpRoot.getBoundingClientRect() : null,
            containerRect: { w: rect.width, h: rect.height },
          });
          if (el.children.length === 0) {
            const xmlPreview = planXml.slice(0, 200).replace(/\s+/g, " ");
            throw new Error(
              `XSLT вернул пустое дерево. Preview: ${xmlPreview}…`,
            );
          }
          if (!qpRoot) {
            throw new Error(
              `XSLT отдал DOM (${innerLen} символов), но не нашли .qp-root — ` +
                `возможно qp.css не загружен или XSLT template не сработал.`,
            );
          }
          const qpRect = qpRoot.getBoundingClientRect();
          if (qpRect.height < 10 || qpRect.width < 10) {
            throw new Error(
              `.qp-root найден, но имеет нулевые размеры (${qpRect.width}×` +
                `${qpRect.height}px). CSS qp.css не применился или конфликтует.`,
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
