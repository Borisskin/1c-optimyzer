import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  // Единый .env в корне проекта (см. ../.env.example).
  envDir: "..",
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    // host: true → слушать на всех интерфейсах (включая 127.0.0.1 + ::1).
    // По умолчанию vite слушает только ::1 (Windows резолвит localhost как IPv6),
    // и десктоп с URL http://127.0.0.1:5173 получает ECONNREFUSED.
    host: true,
  },
  build: {
    target: "es2020",
    chunkSizeWarningLimit: 600,
  },
});
