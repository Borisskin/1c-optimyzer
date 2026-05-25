/**
 * Sprint 8 Phase B.5 — pev2 (Vue Plan Explorer V2) Web Component wrapper.
 *
 * pev2 — Vue 3 компонент от Dalibo Labs (BSD license) для интерактивной
 * визуализации PostgreSQL EXPLAIN (FORMAT JSON, ANALYZE) планов.
 *
 * Поскольку Optimyzer на React, оборачиваем pev2 в Web Custom Element
 * (`<pev2-plan>`) через Vue.defineCustomElement. React видит обычный
 * HTML element и не знает про Vue внутри — clean abstraction.
 *
 * Pattern:
 *   1. ensurePev2Registered() — вызывается lazy на mount, registers <pev2-plan>
 *      в global custom elements registry. Идемпотентно.
 *   2. React компонент Pev2PlanVisualization рендерит <pev2-plan> с props.
 *   3. pev2 проксирует attributes на Vue component внутри shadow DOM.
 *
 * NB: pev2 css автоматически inject'ится через defineCustomElement (он бандлит
 * CSS внутрь shadow DOM). Дополнительный import "pev2/dist/style.css" не нужен.
 */

import { defineCustomElement } from "vue";
import { Plan } from "pev2";

// defineCustomElement создаёт Custom Element class из Vue компонента.
// CSS bundling — он автоматически inject'ит styles внутрь shadow DOM
// (shadow=true по умолчанию).
const Pev2PlanElement = defineCustomElement(Plan as never, {
  shadowRoot: true,
});

let registered = false;

/**
 * Регистрирует `<pev2-plan>` в global custom elements registry.
 *
 * Идемпотентно — повторные вызовы safely игнорируются. Это важно потому
 * что React.useEffect может выполниться несколько раз (StrictMode, HMR),
 * а customElements.define() выбрасывает Error при повторной регистрации.
 */
export function ensurePev2Registered(): void {
  if (registered) return;
  if (typeof customElements === "undefined") {
    // SSR / non-browser environment — silently skip.
    return;
  }
  if (!customElements.get("pev2-plan")) {
    customElements.define("pev2-plan", Pev2PlanElement);
  }
  registered = true;
}
