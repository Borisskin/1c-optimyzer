/**
 * Открыть URL в системном браузере.
 *
 * В Tauri webview `<a target="_blank">` просто ничего не делает — webview2
 * (Windows) и WKWebView (macOS) блокируют new-window по умолчанию. Чтобы
 * ссылки на cabinet/landing/docs реально открывались, нужно вызывать
 * `@tauri-apps/plugin-shell` `openUrl()`.
 *
 * В обычном браузере (vite dev page открыт напрямую) — fallback на window.open.
 */
import { open as openUrl } from "@tauri-apps/plugin-shell";

function isTauri(): boolean {
  return typeof (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ !==
    "undefined";
}

export async function openExternal(url: string): Promise<void> {
  if (!url) return;
  if (isTauri()) {
    try {
      await openUrl(url);
      return;
    } catch (err) {
      // Fallback на window.open если плагин почему-то не работает.
      console.warn("[openExternal] tauri openUrl failed, falling back:", err);
    }
  }
  window.open(url, "_blank", "noreferrer,noopener");
}

/**
 * Глобальный hijack: ловит клики по `<a target="_blank">` и открывает через
 * Tauri shell. Достаточно установить один раз в `main.tsx`.
 */
export function installExternalLinkHijack(): void {
  document.addEventListener(
    "click",
    (event) => {
      const target = event.target as HTMLElement | null;
      if (!target) return;
      const anchor = target.closest("a[target=\"_blank\"]") as HTMLAnchorElement | null;
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("javascript:") || href.startsWith("#")) return;
      event.preventDefault();
      void openExternal(href);
    },
    { capture: true },
  );
}
