/**
 * Dev mode feature flag.
 *
 * Активация:
 *   - Hotkey Ctrl+Shift+D — toggle
 *   - Программно: localStorage.setItem("optimyzer:dev", "1")
 *
 * Когда включён — в Sidebar появляется "DevTools" screen с управлением
 * кешем AI, статусом explainer engine и прочими имплементационными
 * деталями. Обычному пользователю не нужно — это для разработчика.
 */

import { useEffect, useState } from "react";

const STORAGE_KEY = "optimyzer:dev";

export function isDevMode(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(STORAGE_KEY) === "1";
}

export function setDevMode(enabled: boolean): void {
  if (typeof window === "undefined") return;
  if (enabled) {
    window.localStorage.setItem(STORAGE_KEY, "1");
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
  window.dispatchEvent(new CustomEvent("optimyzer:devmode-changed"));
}

export function useDevMode(): boolean {
  const [enabled, setEnabled] = useState<boolean>(isDevMode);

  useEffect(() => {
    const onChange = () => setEnabled(isDevMode());
    const onKey = (e: KeyboardEvent) => {
      // Ctrl+Shift+D — toggle. На Mac — Cmd+Shift+D.
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "D" || e.key === "d")) {
        e.preventDefault();
        setDevMode(!isDevMode());
      }
    };
    window.addEventListener("optimyzer:devmode-changed", onChange);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("optimyzer:devmode-changed", onChange);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  return enabled;
}
