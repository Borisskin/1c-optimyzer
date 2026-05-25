/**
 * Sprint 8 Phase B.5 — JSX namespace augmentation для <pev2-plan> Web Component.
 *
 * React TypeScript строго проверяет JSX элементы. <pev2-plan> — это custom
 * element (зарегистрирован через customElements.define), не стандартный
 * HTML/SVG element. Расширяем IntrinsicElements чтобы TypeScript знал
 * какие props доступны.
 *
 * pev2 Vue компонент принимает (см. https://github.com/dalibo/pev2/blob/main/src/components/Plan.vue):
 *   - plan-source: string  — JSON план как string или Plan object as JSON.stringify
 *   - plan-query: string   — оригинальный SQL запрос (для context tab)
 */

import type { DetailedHTMLProps, HTMLAttributes } from "react";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "pev2-plan": DetailedHTMLProps<
        HTMLAttributes<HTMLElement> & {
          "plan-source": string;
          "plan-query": string;
        },
        HTMLElement
      >;
    }
  }
}

// Make this file a module (vs ambient script).
export {};
