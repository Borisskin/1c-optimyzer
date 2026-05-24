/**
 * Loader для html-query-plan v2.6.1.
 *
 * qp.js — webpack UMD bundle (JustinPealing/html-query-plan). Импорт
 * через Vite ESM ломается из-за strict-mode `this` внутри встроенного
 * svgjs (`var SVG = this.SVG = ...` → undefined).
 *
 * Workaround: грузим qp.js как классический <script> из public/vendor/
 * (Vite отдаёт public assets без трансформации). UMD wrapper сам сядет
 * на window.QP в non-strict browser context.
 *
 * Файл копируется в public/ скриптом setup-planview-binary.ps1 (Phase A),
 * либо вручную: cp node_modules/html-query-plan/dist/qp.js public/vendor/
 */
// Cache-buster версионируем по бампу при патче qp.js.
const QP_SCRIPT_URL = "/vendor/qp.js?v=4";

interface QPGlobal {
  showPlan: (
    el: HTMLElement,
    xml: string,
    opts?: { jsTooltips?: boolean },
  ) => void;
}

let cachedPromise: Promise<QPGlobal> | null = null;

export function loadQP(): Promise<QPGlobal> {
  if (cachedPromise) return cachedPromise;

  cachedPromise = new Promise<QPGlobal>((resolve, reject) => {
    const w = window as unknown as Record<string, unknown>;
    if (w.QP && typeof (w.QP as QPGlobal).showPlan === "function") {
      resolve(w.QP as QPGlobal);
      return;
    }
    const script = document.createElement("script");
    script.src = QP_SCRIPT_URL;
    script.async = true;
    script.onload = () => {
      const QP = w.QP as QPGlobal | undefined;
      if (!QP || typeof QP.showPlan !== "function") {
        reject(
          new Error(
            "html-query-plan: window.QP.showPlan not available after script load",
          ),
        );
        return;
      }
      resolve(QP);
    };
    script.onerror = () =>
      reject(new Error(`Failed to load ${QP_SCRIPT_URL}`));
    document.head.appendChild(script);
  });
  return cachedPromise;
}
