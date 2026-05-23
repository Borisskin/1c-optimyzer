/**
 * Стабильный device fingerprint для license activation.
 *
 * Идеал — на Rust через `machine-uid`. Чтобы не тянуть новый crate сейчас,
 * считаем fingerprint в браузерном слое: stable-machine-derived строка
 * (platform + screen + timezone + first-launch-uuid).
 *
 * Реальная стабильность приходит из first-launch-uuid, который пишется один
 * раз в localStorage. Если юзер сотрёт localStorage — fingerprint поменяется
 * и придётся повторно активировать (это приемлемо).
 */

const FP_STORAGE_KEY = "optimyzer.device-fp.v1";

async function sha256Hex(input: string): Promise<string> {
  const enc = new TextEncoder().encode(input);
  const buf = await crypto.subtle.digest("SHA-256", enc);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function getOrCreateMachineUuid(): string {
  try {
    const existing = localStorage.getItem(FP_STORAGE_KEY);
    if (existing) return existing;
    const fresh = crypto.randomUUID();
    localStorage.setItem(FP_STORAGE_KEY, fresh);
    return fresh;
  } catch {
    // Private mode / quota — fallback на нестабильный UUID.
    return crypto.randomUUID();
  }
}

export async function computeFingerprint(): Promise<string> {
  const components = [
    navigator.platform,
    navigator.userAgent.slice(0, 80),
    new Date().getTimezoneOffset().toString(),
    Intl.DateTimeFormat().resolvedOptions().timeZone || "unknown",
    `${screen.width}x${screen.height}`,
    getOrCreateMachineUuid(),
  ].join("|");
  return sha256Hex(components);
}

export function detectPlatform(): "windows" | "macos" | "linux" {
  const p = navigator.platform.toLowerCase();
  if (p.includes("win")) return "windows";
  if (p.includes("mac")) return "macos";
  return "linux";
}

export function detectDeviceName(): string {
  // Лучше — Tauri API (machine name). Пока — производный из platform.
  const platform = detectPlatform();
  const labels: Record<typeof platform, string> = {
    windows: "Windows PC",
    macos: "Mac",
    linux: "Linux PC",
  };
  return labels[platform];
}
