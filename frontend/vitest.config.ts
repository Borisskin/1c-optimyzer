/**
 * Sprint 8 Phase B — Vitest config для frontend unit tests.
 *
 * Pure utility tests (detectPlanEngine, etc) — Node environment, без jsdom.
 * React component tests (если потом понадобятся) — переключаемся на jsdom.
 *
 * Алиас @/ нужен чтобы тесты могли импортировать src/ так же как app code.
 */

import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    globals: false,
    environment: "node",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
