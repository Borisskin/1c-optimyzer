/**
 * Convenience-функции для эмита событий телеметрии из любого места приложения.
 *
 * Важно: не отправляем содержимое запросов / имена баз / контексты ТЖ /
 * содержимое AI ответов. Только метаданные (размеры, количества, типы).
 *
 * Полный список того что собирается / не собирается — в docs/.../privacy-and-data.md.
 */

import { useTelemetryStore, type EventCategory } from "@/store/telemetryStore";
import { t } from "@/i18n/ru";
import { computeFingerprint, detectPlatform } from "@/utils/fingerprint";

let cachedFingerprint: string | null = null;

async function getFingerprint(): Promise<string> {
  if (cachedFingerprint) return cachedFingerprint;
  cachedFingerprint = await computeFingerprint();
  return cachedFingerprint;
}

async function emit(category: EventCategory, event_type: string, payload: Record<string, unknown> = {}): Promise<void> {
  const fp = await getFingerprint();
  useTelemetryStore.getState().add({
    device_fingerprint: fp,
    app_version: t.app.version,
    platform: detectPlatform(),
    category,
    event_type,
    payload,
    timestamp: new Date().toISOString(),
  });
}

export const telemetry = {
  screenView(screen: string): void {
    void emit("behavior", "screen_view", { screen });
  },

  archiveLoaded(opts: { sizeBytes: number; eventsCount: number; parseMs: number }): void {
    void emit("tech", "archive_loaded", {
      size_mb: Math.round(opts.sizeBytes / (1024 * 1024)),
      events_count: opts.eventsCount,
      parse_ms: opts.parseMs,
    });
  },

  aiClicked(opts: { kind: string; success: boolean }): void {
    void emit("behavior", "ai_clicked", opts);
  },

  paywallShown(opts: { reason: string | null }): void {
    void emit("conversion", "paywall_shown", { reason: opts.reason ?? "unknown" });
  },

  upgradeClicked(opts: { from: string }): void {
    void emit("conversion", "upgrade_clicked", opts);
  },

  appStarted(opts: { first_run: boolean }): void {
    void emit("behavior", "app_started", opts);
  },
};
