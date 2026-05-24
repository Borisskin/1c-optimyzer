/**
 * Loader для html-query-plan v2.6.1.
 *
 * **Inline-bundle approach** (Sprint 7 final fix): qp.js (patched) и qp.css
 * подключаем как `?raw` строки прямо в основной chunk бандла. Никаких
 * external HTTP requests → никаких cache issues, никаких CSP сюрпризов,
 * никаких lazy-chunk async race conditions. Всё работает one-shot.
 *
 * История попыток (что НЕ работало):
 * 1. ESM `import * as QP from "html-query-plan"` — Vite оборачивает в
 *    strict mode, `var SVG = this.SVG` падает (this === undefined).
 * 2. Vite `import "html-query-plan/css/qp.css"` — Vite молча не подключает
 *    CSS в lazy chunk (видимо из-за url('qp_icons.png') resolve проблем).
 * 3. <script src="/vendor/qp.js?v=N"> + <link href="/vendor/qp.css?v=N"> —
 *    WebView2 у юзера всё равно отдавал старый кеш / новый файл не появлялся.
 *
 * Что РАБОТАЕТ (inline):
 * - qp.css inject как <style> (с заменой url('qp_icons.png') → абсолютный путь).
 * - qp.js eval через `new Function(src).call(window)` — UMD wrapper в browser
 *   context (без module/exports/define) сядет на window.QP.
 *
 * qp_icons.png остаётся в public/vendor/ (статичная картинка операторов).
 */

// @ts-expect-error Vite ?raw возвращает string, типы не подтянуты.
import qpJsSource from "./qp-bundle.js?raw";
// @ts-expect-error Vite ?raw возвращает string, типы не подтянуты.
import qpCssSource from "./qp-styles.css?raw";

const QP_ICONS_URL = "/vendor/qp_icons.png";

interface QPGlobal {
  showPlan: (
    el: HTMLElement,
    xml: string,
    opts?: { jsTooltips?: boolean },
  ) => void;
}

let cached: QPGlobal | null = null;

function injectStyles(): void {
  const id = "qp-inline-styles";
  if (document.getElementById(id)) return;
  // qp.css ссылается на url('qp_icons.png') относительно файла стиля.
  // Когда мы inject как <style>, путь резолвится относительно текущей
  // страницы → не находится. Подменяем на абсолютный /vendor/qp_icons.png.
  //
  // ВАЖНО: qp.css имеет UTF-8 BOM (0xFEFF) в начале. При inject как <style>
  // парсер CSS включает BOM в первый селектор:
  //   `﻿div.qp-node` — не матчит `<div class="qp-node">` → правила не
  // применяются → все qp-node остаются transparent → визуализация невидима!
  // (То же что в SHOWPLAN XML — BOM ломает парсер.)
  const cssText = (qpCssSource as string)
    .replace(/^﻿/, "") // strip UTF-8 BOM (есть в qp.css из node_modules)
    .replace(/url\((['"]?)qp_icons\.png\1\)/g, `url('${QP_ICONS_URL}')`);
  const style = document.createElement("style");
  style.id = id;
  style.textContent = cssText;
  document.head.appendChild(style);
}

function injectScript(): QPGlobal {
  const w = window as unknown as Record<string, unknown>;
  if (w.QP && typeof (w.QP as QPGlobal).showPlan === "function") {
    return w.QP as QPGlobal;
  }
  // UMD wrapper в qp.js проверяет typeof exports/module/define. В browser
  // их нет → сядет на root[QP] где root = window (см. webpack wrapper
  // вверху qp.js: `(function(root, factory) { ... }(window, function() { ... }))`).
  // new Function создаёт function в global scope. `.call(window)` гарантирует
  // что `this === window` для встроенного svgjs UMD внутри (это лечит
  // `var SVG = this.SVG = ...` strict-mode bug).
  // eslint-disable-next-line @typescript-eslint/no-implied-eval
  const fn = new Function(qpJsSource as string);
  fn.call(window);
  const QP = w.QP as QPGlobal | undefined;
  if (!QP || typeof QP.showPlan !== "function") {
    throw new Error(
      "html-query-plan: window.QP не появился после eval qp-bundle.js",
    );
  }
  return QP;
}

export function loadQP(): Promise<QPGlobal> {
  // Synchronous под капотом, но возвращаем Promise для API совместимости.
  if (cached) return Promise.resolve(cached);
  try {
    injectStyles();
    cached = injectScript();
    return Promise.resolve(cached);
  } catch (e) {
    return Promise.reject(e instanceof Error ? e : new Error(String(e)));
  }
}
