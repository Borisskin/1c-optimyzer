/**
 * Loader для html-query-plan v2.6.1.
 *
 * qp.js — webpack UMD bundle (JustinPealing/html-query-plan). При попытке
 * подгрузить его через Vite ESM (`import * as QP from "html-query-plan"`)
 * ломается strict-mode `this` внутри встроенного svgjs.
 *
 * qp.css — содержит `url('qp_icons.png')` относительный путь. Vite в lazy
 * chunk молча не подключает этот CSS (проверено: standalone HTML через
 * <link> работает, а ESM import — нет). Поэтому грузим оба файла через
 * `<script>` и `<link>` из public/vendor/ — Vite отдаёт их как static
 * assets без трансформации.
 *
 * Файлы лежат в frontend/public/vendor/{qp.js,qp.css,qp_icons.png}.
 * Бамп `?v=N` при патче qp.js — для инвалидации browser cache.
 */
const QP_SCRIPT_URL = "/vendor/qp.js?v=5";
const QP_STYLE_URL = "/vendor/qp.css?v=1";

interface QPGlobal {
  showPlan: (
    el: HTMLElement,
    xml: string,
    opts?: { jsTooltips?: boolean },
  ) => void;
}

let cachedPromise: Promise<QPGlobal> | null = null;

function ensureStylesheet(): void {
  const id = "qp-stylesheet";
  if (document.getElementById(id)) return;
  const link = document.createElement("link");
  link.id = id;
  link.rel = "stylesheet";
  link.href = QP_STYLE_URL;
  document.head.appendChild(link);
}

export function loadQP(): Promise<QPGlobal> {
  if (cachedPromise) return cachedPromise;

  cachedPromise = new Promise<QPGlobal>((resolve, reject) => {
    ensureStylesheet();

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
