/**
 * Sprint 7 Phase B — SSMS-style визуализация execution plan.
 *
 * Wraps html-query-plan v2.6.1 (MIT, Justin Pealing). qp.showPlan рендерит
 * HTML/SVG operator tree с tooltips. Использует XSLT transformation от
 * SHOWPLAN XML → HTML / SVG.
 *
 * qp.js и qp.css inline-bundled через qpLoader — никаких external HTTP
 * requests, никакого WebView2 cache. См. src/vendor/qpLoader.ts.
 *
 * Re-rendering: на каждое изменение planXml — container.innerHTML="" + showPlan.
 */

import { useEffect, useRef, useState } from "react";
import { loadQP } from "@/vendor/qpLoader";
import styles from "./PlanVisualization.module.css";

interface Props {
  planXml: string | null;
  onError?: (err: Error) => void;
}

interface DebugInfo {
  childrenCount: number;
  qpRootFound: boolean;
  qpNodeCount: number;
  qpNodeBg: string | null;
  cssLoaded: boolean;
}

export function PlanVisualization({ planXml, onError }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [debug, setDebug] = useState<DebugInfo | null>(null);
  // Sprint 7 post-Phase F — collapse toggle. Визуализация может быть большой
  // (длинное дерево операторов в широком SVG); юзер должен мочь свернуть
  // когда читает AI-объяснение или statement-card ниже. Default expanded —
  // визуал это основной артефакт XML-импорта.
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!planXml) {
      el.innerHTML = "";
      setError(null);
      setDebug(null);
      return;
    }
    let cancelled = false;
    el.innerHTML = "";
    setError(null);
    setDebug(null);
    // Strip UTF-8 BOM (0xFEFF). SSMS экспортирует .sqlplan с BOM, DOMParser
    // в некоторых WebView версиях на BOM тихо отдаёт пустой документ.
    const cleanXml =
      planXml.charCodeAt(0) === 0xfeff ? planXml.slice(1) : planXml;
    loadQP()
      .then((QP) => {
        if (cancelled) return;
        try {
          QP.showPlan(el, cleanXml, { jsTooltips: true });
          const qpRoot = el.querySelector(".qp-root");
          const qpNode = el.querySelector(".qp-node") as HTMLElement | null;
          const cs = qpNode ? window.getComputedStyle(qpNode) : null;
          const info: DebugInfo = {
            childrenCount: el.children.length,
            qpRootFound: !!qpRoot,
            qpNodeCount: el.querySelectorAll(".qp-node").length,
            qpNodeBg: cs?.backgroundColor ?? null,
            cssLoaded:
              cs?.backgroundColor === "rgb(255, 255, 204)" ||
              cs?.backgroundColor === "#FFFFCC",
          };
          setDebug(info);
          if (el.children.length === 0) {
            throw new Error(
              "showPlan не положил ни одного child в container. " +
                "XSLT вернул пустоту — возможно XML не SHOWPLAN или сломан.",
            );
          }
          if (!qpRoot) {
            throw new Error(
              `showPlan создал ${el.children.length} children, но .qp-root не найден. ` +
                "XSLT template не подошёл к XML.",
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
        setError(`loadQP failed: ${e.message}`);
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
        {debug && (
          <div className={styles.errorDetail} style={{ marginTop: 8 }}>
            children={debug.childrenCount}, qp-root={debug.qpRootFound ? "✓" : "✗"},
            nodes={debug.qpNodeCount}, bg={debug.qpNodeBg ?? "none"},
            css={debug.cssLoaded ? "✓" : "✗"}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`${styles.container} ${collapsed ? styles.containerCollapsed : ""}`}>
      <div className={styles.titleBar}>
        <div className={styles.title}>Визуализация плана (SSMS-style)</div>
        <button
          type="button"
          className={styles.collapseToggle}
          onClick={() => setCollapsed((v) => !v)}
          aria-expanded={!collapsed}
        >
          {collapsed ? "Развернуть" : "Свернуть"}
        </button>
      </div>
      {/* display:none сохраняет рендеренный qp.js DOM (innerHTML не сбрасывается
          при свёртывании — это критично, иначе пришлось бы пере-рендерить план
          при каждом expand). */}
      <div
        ref={containerRef}
        className={styles.viz}
        style={collapsed ? { display: "none" } : undefined}
      />
    </div>
  );
}
