/**
 * Sprint 10 Phase B — тесты шаблонов.
 */

import { describe, expect, it } from "vitest";
import { serializeToXml } from "../xmlSerializer";
import { BUILTIN_TEMPLATES, getTemplateById } from "../templates";

describe("BUILTIN_TEMPLATES", () => {
  it("ровно 6 встроенных шаблонов", () => {
    expect(BUILTIN_TEMPLATES).toHaveLength(6);
  });

  it("все шаблоны имеют уникальные id", () => {
    const ids = BUILTIN_TEMPLATES.map((t) => t.id);
    const unique = new Set(ids);
    expect(unique.size).toBe(BUILTIN_TEMPLATES.length);
  });

  it("все шаблоны имеют name, description, volume_hint", () => {
    for (const t of BUILTIN_TEMPLATES) {
      expect(t.name.length).toBeGreaterThan(0);
      expect(t.description.length).toBeGreaterThan(0);
      expect(t.volume_hint.length).toBeGreaterThan(0);
    }
  });

  it("все шаблоны имеют valid estimated_volume", () => {
    const valid = ["low", "medium", "high", "very_high"];
    for (const t of BUILTIN_TEMPLATES) {
      expect(valid).toContain(t.estimated_volume);
    }
  });

  it("все шаблоны имеют valid LogcfgConfig", () => {
    for (const t of BUILTIN_TEMPLATES) {
      expect(t.config).toBeDefined();
      expect(t.config.log_directory).toBeTruthy();
      expect(t.config.history_hours).toBeGreaterThan(0);
      expect(t.config.events).toBeDefined();
    }
  });

  it("каждый шаблон сериализуется без ошибок", () => {
    for (const t of BUILTIN_TEMPLATES) {
      const xml = serializeToXml(t.config);
      expect(xml).toContain('<?xml version="1.0"');
      expect(xml).toContain("</config>");
    }
  });

  it("minimal — только EXCP и TDEADLOCK включены", () => {
    const t = BUILTIN_TEMPLATES.find((x) => x.id === "minimal")!;
    expect(t).toBeDefined();
    expect(t.config.events.EXCP?.enabled).toBe(true);
    expect(t.config.events.TDEADLOCK?.enabled).toBe(true);
    expect(t.config.capture_plans).toBe(false);
    // Не должно быть DBMSSQL/DBPOSTGRS.
    expect(t.config.events.DBMSSQL).toBeUndefined();
  });

  it("slow_operations — включает CALL, DBMSSQL, DBPOSTGRS", () => {
    const t = BUILTIN_TEMPLATES.find((x) => x.id === "slow_operations")!;
    expect(t).toBeDefined();
    expect(t.config.events.CALL?.enabled).toBe(true);
    expect(t.config.events.DBMSSQL?.enabled).toBe(true);
    expect(t.config.events.DBPOSTGRS?.enabled).toBe(true);
  });

  it("full_diagnostic — capture_plans=true", () => {
    const t = BUILTIN_TEMPLATES.find((x) => x.id === "full_diagnostic")!;
    expect(t).toBeDefined();
    expect(t.config.capture_plans).toBe(true);
  });

  it("deadlocks_only — включает TDEADLOCK и TLOCK", () => {
    const t = BUILTIN_TEMPLATES.find((x) => x.id === "deadlocks_only")!;
    expect(t).toBeDefined();
    expect(t.config.events.TDEADLOCK?.enabled).toBe(true);
    expect(t.config.events.TLOCK?.enabled).toBe(true);
  });

  it("expert_audit — включает MEM", () => {
    const t = BUILTIN_TEMPLATES.find((x) => x.id === "expert_audit")!;
    expect(t).toBeDefined();
    expect(t.config.events.MEM?.enabled).toBe(true);
  });

  it("pre_release_baseline — capture_plans=false, малые события", () => {
    const t = BUILTIN_TEMPLATES.find((x) => x.id === "pre_release_baseline")!;
    expect(t).toBeDefined();
    expect(t.config.capture_plans).toBe(false);
    expect(t.estimated_volume).toBe("low");
  });
});

describe("getTemplateById", () => {
  it("находит по существующему id", () => {
    const t = getTemplateById("minimal");
    expect(t).toBeDefined();
    expect(t!.id).toBe("minimal");
  });

  it("возвращает undefined для несуществующего id", () => {
    const t = getTemplateById("nonexistent");
    expect(t).toBeUndefined();
  });
});
