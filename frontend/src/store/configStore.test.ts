/**
 * S13 Фаза 1 — тесты configStore (Remote Config на desktop).
 * environment=node, поэтому localStorage мокаем вручную.
 */

import { describe, it, expect, beforeEach } from "vitest";
import type { RemoteConfigPublic } from "@/api/cloud";
import {
  useConfigStore,
  DEFAULT_REMOTE_CONFIG,
  isFeatureEnabled,
  isAiKillSwitchOn,
} from "@/store/configStore";

const KEY = "optimyzer.remoteconfig.v1";

class LSMock {
  store = new Map<string, string>();
  getItem(k: string): string | null {
    return this.store.has(k) ? (this.store.get(k) as string) : null;
  }
  setItem(k: string, v: string): void {
    this.store.set(k, v);
  }
  removeItem(k: string): void {
    this.store.delete(k);
  }
  clear(): void {
    this.store.clear();
  }
}

beforeEach(() => {
  (globalThis as unknown as { localStorage: LSMock }).localStorage = new LSMock();
  // Сброс стора к дефолту между тестами (module-level singleton).
  useConfigStore.setState({ config: DEFAULT_REMOTE_CONFIG, loadedAt: null });
});

describe("configStore — defaults", () => {
  it("дефолт — discovery, всё включено, AI работает", () => {
    expect(DEFAULT_REMOTE_CONFIG.monetization_mode).toBe("discovery");
    expect(DEFAULT_REMOTE_CONFIG.ai_kill_switch).toBe(false);
    expect(isFeatureEnabled("tj_analysis")).toBe(true);
    expect(isFeatureEnabled("plans")).toBe(true);
    expect(isAiKillSwitchOn()).toBe(false);
  });

  it("неизвестный флаг трактуется как включённый (безопасный дефолт)", () => {
    expect(isFeatureEnabled("nonexistent_module")).toBe(true);
  });
});

describe("configStore — setConfig + persist", () => {
  it("setConfig обновляет state, выставляет loadedAt и пишет в localStorage", () => {
    const cfg: RemoteConfigPublic = {
      ...DEFAULT_REMOTE_CONFIG,
      ai_kill_switch: true,
      config_version: 5,
    };
    useConfigStore.getState().setConfig(cfg);

    expect(useConfigStore.getState().config.ai_kill_switch).toBe(true);
    expect(isAiKillSwitchOn()).toBe(true);
    expect(useConfigStore.getState().loadedAt).not.toBeNull();

    const raw = (globalThis as unknown as { localStorage: LSMock }).localStorage.getItem(KEY);
    expect(raw).toBeTruthy();
    expect(raw).toContain('"config_version":5');
  });
});

describe("configStore — hydrate merge", () => {
  it("частичный персист сливается с дефолтами (флаги не теряются)", () => {
    (globalThis as unknown as { localStorage: LSMock }).localStorage.setItem(
      KEY,
      JSON.stringify({ monetization_mode: "paid", feature_flags: { plans: false } }),
    );
    useConfigStore.getState().hydrate();
    const c = useConfigStore.getState().config;

    expect(c.monetization_mode).toBe("paid");
    expect(c.feature_flags.plans).toBe(false); // из персиста
    expect(c.feature_flags.tj_analysis).toBe(true); // дефолт сохранён
    expect(c.limits.ai_per_month).toBeNull(); // дефолт limits
  });

  it("пустой localStorage → дефолтный конфиг", () => {
    useConfigStore.getState().hydrate();
    expect(useConfigStore.getState().config.monetization_mode).toBe("discovery");
  });
});

describe("configStore — graceful", () => {
  it("не падает если localStorage кидает (приватный режим/блокировка)", () => {
    (globalThis as unknown as { localStorage: unknown }).localStorage = {
      getItem() {
        throw new Error("blocked");
      },
      setItem() {
        throw new Error("blocked");
      },
      removeItem() {},
      clear() {},
    };
    expect(() => useConfigStore.getState().hydrate()).not.toThrow();
    expect(useConfigStore.getState().config.monetization_mode).toBe("discovery");
    // setConfig тоже не должен падать при ошибке записи
    expect(() =>
      useConfigStore.getState().setConfig({ ...DEFAULT_REMOTE_CONFIG, config_version: 9 }),
    ).not.toThrow();
    expect(useConfigStore.getState().config.config_version).toBe(9);
  });
});
