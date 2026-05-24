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
// Версия в имени файла (не query) — WebView2 агрессивно кеширует /vendor/qp.js
// на disk, и ?v=N может быть проигнорирован. Меняем path → cache miss гарантирован.
// При обновлении qp.js / qp.css или patch'е — бамп: qp.v6.js → qp.v7.js.
const QP_SCRIPT_URL = "/vendor/qp.v6.js";
const QP_STYLE_URL = "/vendor/qp.v2.css";

interface QPGlobal {
  showPlan: (
    el: HTMLElement,
    xml: string,
    opts?: { jsTooltips?: boolean },
  ) => void;
}

let cachedPromise: Promise<QPGlobal> | null = null;

function ensureStylesheet(): Promise<void> {
  const id = "qp-stylesheet";
  const existing = document.getElementById(id) as HTMLLinkElement | null;
  if (existing) {
    // Если link уже есть, ждём что он применён. sheet ≠ null когда CSS загружен.
    if ((existing as HTMLLinkElement & { sheet: unknown }).sheet) {
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => resolve(), { once: true });
    });
  }
  return new Promise((resolve) => {
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = QP_STYLE_URL;
    link.onload = () => resolve();
    link.onerror = () => resolve(); // не блокируем, даже если CSS не загрузился
    document.head.appendChild(link);
  });
}

export function loadQP(): Promise<QPGlobal> {
  if (cachedPromise) return cachedPromise;

  cachedPromise = (async (): Promise<QPGlobal> => {
    // Сначала ждём CSS — иначе showPlan нарисует невидимые qp-node
    // (CSS подтянется позже, но showPlan уже завершится).
    await ensureStylesheet();

    const w = window as unknown as Record<string, unknown>;
    if (w.QP && typeof (w.QP as QPGlobal).showPlan === "function") {
      return w.QP as QPGlobal;
    }
    return new Promise<QPGlobal>((resolve, reject) => {
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
  })();
  return cachedPromise;
}
