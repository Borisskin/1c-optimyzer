/**
 * Sprint 10 Phase B — тесты volumeEstimator.
 */

import { describe, expect, it } from "vitest";
import { estimateVolume, formatVolume } from "../volumeEstimator";
import type { LogcfgConfig } from "../types";

const EMPTY_CONFIG: LogcfgConfig = {
  events: {},
  capture_plans: false,
  log_directory: "C:\\1C-TechLog",
  max_size_gb: 10,
};

describe("estimateVolume", () => {
  it("пустой config → 0 МБ/час", () => {
    const result = estimateVolume(EMPTY_CONFIG);
    expect(result.typical).toBe(0);
    expect(result.quiet).toBe(0);
    expect(result.busy).toBe(0);
    expect(result.warning_if_too_large).toBe(false);
  });

  it("только disabled события → 0 МБ/час", () => {
    const config: LogcfgConfig = {
      ...EMPTY_CONFIG,
      events: {
        CALL: { enabled: false, threshold_cs: 100 },
        DBMSSQL: { enabled: false, threshold_cs: 10 },
      },
    };
    const result = estimateVolume(config);
    expect(result.typical).toBe(0);
  });

  it("minimal шаблон (EXCP + TDEADLOCK) → малый объём", () => {
    const config: LogcfgConfig = {
      ...EMPTY_CONFIG,
      events: {
        EXCP: { enabled: true },
        TDEADLOCK: { enabled: true },
      },
    };
    const result = estimateVolume(config);
    // Типовой объём минимальной конфигурации — не более 50 МБ/ч.
    expect(result.typical).toBeLessThan(50);
    expect(result.warning_if_too_large).toBe(false);
  });

  it("DBMSSQL без порога → больше чем с порогом", () => {
    const noThreshold: LogcfgConfig = {
      ...EMPTY_CONFIG,
      events: { DBMSSQL: { enabled: true, threshold_cs: 0 } },
    };
    const withThreshold: LogcfgConfig = {
      ...EMPTY_CONFIG,
      events: { DBMSSQL: { enabled: true, threshold_cs: 100 } },
    };
    expect(estimateVolume(noThreshold).typical)
      .toBeGreaterThan(estimateVolume(withThreshold).typical);
  });

  it("capture_plans увеличивает объём DBMSSQL", () => {
    const withoutPlans: LogcfgConfig = {
      ...EMPTY_CONFIG,
      events: { DBMSSQL: { enabled: true, threshold_cs: 10 } },
      capture_plans: false,
    };
    const withPlans: LogcfgConfig = {
      ...withoutPlans,
      capture_plans: true,
    };
    // С планами должно быть минимум в 3× больше.
    expect(estimateVolume(withPlans).typical)
      .toBeGreaterThan(estimateVolume(withoutPlans).typical * 2.5);
  });

  it("полная диагностика с планами → warning_if_too_large=true", () => {
    // threshold_cs=0 = без порога (все события). Планы × 4 для DBMSSQL/DBPOSTGRS.
    const config: LogcfgConfig = {
      events: {
        CALL: { enabled: true, threshold_cs: 0 },
        SCALL: { enabled: true, threshold_cs: 0 },
        SDBL: { enabled: true, threshold_cs: 0 },
        DBMSSQL: { enabled: true, threshold_cs: 0 },
        DBPOSTGRS: { enabled: true, threshold_cs: 0 },
        TLOCK: { enabled: true, threshold_cs: 0 },
      },
      capture_plans: true,
      log_directory: "C:\\1C-TechLog",
      max_size_gb: 10,
    };
    const result = estimateVolume(config);
    expect(result.warning_if_too_large).toBe(true);
  });

  it("busy > typical > quiet", () => {
    const config: LogcfgConfig = {
      ...EMPTY_CONFIG,
      events: {
        CALL: { enabled: true, threshold_cs: 100 },
        DBMSSQL: { enabled: true, threshold_cs: 10 },
      },
    };
    const result = estimateVolume(config);
    expect(result.busy).toBeGreaterThan(result.typical);
    expect(result.typical).toBeGreaterThan(result.quiet);
  });

  it("высокий порог уменьшает объём", () => {
    const low: LogcfgConfig = {
      ...EMPTY_CONFIG,
      events: { CALL: { enabled: true, threshold_cs: 10 } },
    };
    const high: LogcfgConfig = {
      ...EMPTY_CONFIG,
      events: { CALL: { enabled: true, threshold_cs: 1000 } },
    };
    expect(estimateVolume(low).typical).toBeGreaterThan(estimateVolume(high).typical);
  });

  it("capture_plans не влияет на события без Duration (EXCP)", () => {
    const withoutPlans: LogcfgConfig = {
      ...EMPTY_CONFIG,
      events: { EXCP: { enabled: true } },
      capture_plans: false,
    };
    const withPlans: LogcfgConfig = {
      ...withoutPlans,
      capture_plans: true,
    };
    // EXCP не имеет планов → объём одинаковый.
    expect(estimateVolume(withPlans).typical)
      .toBeCloseTo(estimateVolume(withoutPlans).typical, 1);
  });
});

describe("formatVolume", () => {
  it("0 → < 1 МБ/ч", () => {
    expect(formatVolume(0)).toBe("< 1 МБ/ч");
  });
  it("0.5 → < 1 МБ/ч", () => {
    expect(formatVolume(0.5)).toBe("< 1 МБ/ч");
  });
  it("100 → ~100 МБ/ч", () => {
    expect(formatVolume(100)).toBe("~100 МБ/ч");
  });
  it("1024 → ~1.0 ГБ/ч", () => {
    expect(formatVolume(1024)).toBe("~1.0 ГБ/ч");
  });
  it("2048 → ~2.0 ГБ/ч", () => {
    expect(formatVolume(2048)).toBe("~2.0 ГБ/ч");
  });
});
