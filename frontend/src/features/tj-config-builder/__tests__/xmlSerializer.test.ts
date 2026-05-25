/**
 * Sprint 10 Phase B — тесты xmlSerializer.
 */

import { describe, expect, it } from "vitest";
import { escapeXml, serializeToXml } from "../xmlSerializer";
import type { LogcfgConfig } from "../types";

const BASE_CONFIG: LogcfgConfig = {
  events: {},
  capture_plans: false,
  log_directory: "C:\\1C-TechLog",
  history_hours: 72,
};

describe("serializeToXml", () => {
  it("содержит XML declaration и корневой тег", () => {
    const xml = serializeToXml(BASE_CONFIG);
    expect(xml).toContain('<?xml version="1.0" encoding="UTF-8"?>');
    expect(xml).toContain('<config xmlns="http://v8.1c.ru/v8/tech-log">');
    expect(xml).toContain("</config>");
  });

  it("содержит тег <log> с location и history", () => {
    const xml = serializeToXml(BASE_CONFIG);
    expect(xml).toContain('location="C:\\1C-TechLog"');
    expect(xml).toContain('history="72"');
  });

  it("history отражает значение history_hours из config", () => {
    const config: LogcfgConfig = { ...BASE_CONFIG, history_hours: 168 };
    const xml = serializeToXml(config);
    expect(xml).toContain('history="168"');
  });

  it("содержит property name=all", () => {
    const xml = serializeToXml(BASE_CONFIG);
    expect(xml).toContain('<property name="all"/>');
  });

  it("включает событие CALL с порогом", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: { CALL: { enabled: true, threshold_cs: 100 } },
    };
    const xml = serializeToXml(config);
    expect(xml).toContain('<eq property="name" value="CALL"/>');
    // threshold_cs=100 → value="10000" (100 cs × 100 units/cs = 10000; 1 unit = 100мкс → 10000 × 100мкс = 1 сек)
    expect(xml).toContain('<gt property="duration" value="10000"/>');
  });

  it("включает событие TDEADLOCK без порога", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: { TDEADLOCK: { enabled: true } },
    };
    const xml = serializeToXml(config);
    expect(xml).toContain('<eq property="name" value="TDEADLOCK"/>');
    expect(xml).not.toContain("duration");
  });

  it("не включает disabled события", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: {
        CALL: { enabled: true, threshold_cs: 100 },
        DBMSSQL: { enabled: false, threshold_cs: 10 },
      },
    };
    const xml = serializeToXml(config);
    expect(xml).toContain("CALL");
    expect(xml).not.toContain("DBMSSQL");
  });

  it("threshold=0 — не добавляет duration фильтр", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: { CALL: { enabled: true, threshold_cs: 0 } },
    };
    const xml = serializeToXml(config);
    expect(xml).toContain("CALL");
    expect(xml).not.toContain("duration");
  });

  it("threshold=null — не добавляет duration фильтр", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: { EXCP: { enabled: true, threshold_cs: null } },
    };
    const xml = serializeToXml(config);
    expect(xml).toContain("EXCP");
    expect(xml).not.toContain("duration");
  });

  it("capture_plans=true добавляет plansqltext и plansql", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: { DBMSSQL: { enabled: true, threshold_cs: 10 } },
      capture_plans: true,
    };
    const xml = serializeToXml(config);
    expect(xml).toContain('<property name="plansqltext"/>');
    expect(xml).toContain("<plansql/>");
  });

  it("capture_plans=false — нет plansqltext и plansql", () => {
    const xml = serializeToXml(BASE_CONFIG);
    expect(xml).not.toContain("plansqltext");
    expect(xml).not.toContain("plansql");
  });

  it("несколько событий — все в XML", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: {
        CALL: { enabled: true, threshold_cs: 100 },
        DBMSSQL: { enabled: true, threshold_cs: 10 },
        EXCP: { enabled: true },
      },
    };
    const xml = serializeToXml(config);
    expect(xml).toContain("CALL");
    expect(xml).toContain("DBMSSQL");
    expect(xml).toContain("EXCP");
  });

  it("пустые события — только property name=all", () => {
    const xml = serializeToXml(BASE_CONFIG);
    expect(xml).not.toContain("<event>");
    expect(xml).toContain('<property name="all"/>');
  });

  it("путь с пробелами экранируется в атрибуте", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      log_directory: "C:\\Program Files\\1C-TechLog",
    };
    const xml = serializeToXml(config);
    expect(xml).toContain("Program Files");
  });

  it("SCALL с порогом — duration добавляется (SCALL входит в EVENTS_WITH_DURATION)", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: { SCALL: { enabled: true, threshold_cs: 50 } },
    };
    const xml = serializeToXml(config);
    expect(xml).toContain("SCALL");
    // threshold_cs=50 → value="5000" (50 × 100 = 5000; 5000 × 100мкс = 500мс)
    expect(xml).toContain('<gt property="duration" value="5000"/>');
  });

  it("EXCPCNTX не имеет duration (нет в EVENTS_WITH_DURATION)", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: { EXCPCNTX: { enabled: true, threshold_cs: 100 } },
    };
    const xml = serializeToXml(config);
    expect(xml).toContain("EXCPCNTX");
    // threshold_cs есть, но EXCPCNTX не в EVENTS_WITH_DURATION → без duration
    expect(xml).not.toContain("duration");
  });

  it("результат валидный XML — начинается с <?xml и закрывается </config>", () => {
    const config: LogcfgConfig = {
      ...BASE_CONFIG,
      events: {
        CALL: { enabled: true, threshold_cs: 100 },
        TDEADLOCK: { enabled: true },
      },
    };
    const xml = serializeToXml(config);
    expect(xml.trimStart().startsWith("<?xml")).toBe(true);
    expect(xml.trimEnd().endsWith("</config>")).toBe(true);
  });
});

describe("escapeXml", () => {
  it("экранирует амперсанд", () => {
    expect(escapeXml("a&b")).toBe("a&amp;b");
  });
  it("экранирует <", () => {
    expect(escapeXml("a<b")).toBe("a&lt;b");
  });
  it("экранирует >", () => {
    expect(escapeXml("a>b")).toBe("a&gt;b");
  });
  it("экранирует двойные кавычки", () => {
    expect(escapeXml('a"b')).toBe("a&quot;b");
  });
  it("не изменяет обычный путь", () => {
    expect(escapeXml("C:\\1C-TechLog")).toBe("C:\\1C-TechLog");
  });
});
