/**
 * Sprint 9 Phase B.5 — Tests для severity helper utilities.
 *
 * Тестирует type guards и mapping helpers для SqlAntipatternSeverity и PlanSeverity.
 * Проверяет что canonical values корректно различаются и неизвестные значения
 * обрабатываются gracefully.
 */

import { describe, expect, it } from "vitest";
import type {
  SqlAntipatternSeverity,
  SqlAntipatternFinding,
  SqlAntipatternsResponse,
  PlanEngine,
} from "./backend";

// ---------------------------------------------------------------------------
// Type guard helpers (inline — тестируем логику, не импорт)
// ---------------------------------------------------------------------------

const VALID_SEVERITIES: SqlAntipatternSeverity[] = [
  "Critical", "Warning", "Info", "Blocker", "Major", "Minor",
];

const VALID_ENGINES: PlanEngine[] = ["mssql", "postgres"];

function isSqlAntipatternSeverity(v: unknown): v is SqlAntipatternSeverity {
  return typeof v === "string" && VALID_SEVERITIES.includes(v as SqlAntipatternSeverity);
}

function isPlanEngine(v: unknown): v is PlanEngine {
  return typeof v === "string" && VALID_ENGINES.includes(v as PlanEngine);
}

function isValidFinding(f: unknown): f is SqlAntipatternFinding {
  if (!f || typeof f !== "object") return false;
  const obj = f as Record<string, unknown>;
  return (
    typeof obj.code === "string" &&
    typeof obj.title === "string" &&
    typeof obj.description === "string" &&
    isSqlAntipatternSeverity(obj.severity) &&
    isPlanEngine(obj.dialect) &&
    typeof obj.is_1c_context_only === "boolean" &&
    (obj.snippet === null || typeof obj.snippet === "string") &&
    typeof obj.rationale === "string" &&
    typeof obj.recommendation === "string"
  );
}

// ---------------------------------------------------------------------------
// SqlAntipatternSeverity guards
// ---------------------------------------------------------------------------

describe("isSqlAntipatternSeverity — type guard", () => {
  it("'Critical' валидный", () => {
    expect(isSqlAntipatternSeverity("Critical")).toBe(true);
  });

  it("'Warning' валидный", () => {
    expect(isSqlAntipatternSeverity("Warning")).toBe(true);
  });

  it("'Info' валидный", () => {
    expect(isSqlAntipatternSeverity("Info")).toBe(true);
  });

  it("'Blocker' валидный (legacy)", () => {
    expect(isSqlAntipatternSeverity("Blocker")).toBe(true);
  });

  it("'Major' валидный (legacy)", () => {
    expect(isSqlAntipatternSeverity("Major")).toBe(true);
  });

  it("'Minor' валидный (legacy)", () => {
    expect(isSqlAntipatternSeverity("Minor")).toBe(true);
  });

  it("'High' НЕ валидный (AI enum drift — должен быть нормализован бэкендом)", () => {
    expect(isSqlAntipatternSeverity("High")).toBe(false);
  });

  it("'Medium' НЕ валидный", () => {
    expect(isSqlAntipatternSeverity("Medium")).toBe(false);
  });

  it("'Low' НЕ валидный", () => {
    expect(isSqlAntipatternSeverity("Low")).toBe(false);
  });

  it("null НЕ валидный", () => {
    expect(isSqlAntipatternSeverity(null)).toBe(false);
  });

  it("число НЕ валидный", () => {
    expect(isSqlAntipatternSeverity(42)).toBe(false);
  });

  it("пустая строка НЕ валидный", () => {
    expect(isSqlAntipatternSeverity("")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// PlanEngine guards
// ---------------------------------------------------------------------------

describe("isPlanEngine — type guard", () => {
  it("'mssql' валидный", () => {
    expect(isPlanEngine("mssql")).toBe(true);
  });

  it("'postgres' валидный", () => {
    expect(isPlanEngine("postgres")).toBe(true);
  });

  it("'oracle' НЕ валидный", () => {
    expect(isPlanEngine("oracle")).toBe(false);
  });

  it("'MSSQL' (uppercase) НЕ валидный", () => {
    expect(isPlanEngine("MSSQL")).toBe(false);
  });

  it("null НЕ валидный", () => {
    expect(isPlanEngine(null)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// SqlAntipatternFinding shape validation
// ---------------------------------------------------------------------------

describe("isValidFinding — finding schema validation", () => {
  const validFinding: SqlAntipatternFinding = {
    code: "select_star",
    title: "SELECT * антипаттерн",
    description: "Получение всех колонок",
    severity: "Warning",
    dialect: "mssql",
    is_1c_context_only: false,
    snippet: "SELECT *",
    rationale: "Лишние данные по сети",
    recommendation: "Указать явный список полей",
  };

  it("корректный finding → true", () => {
    expect(isValidFinding(validFinding)).toBe(true);
  });

  it("finding с null snippet → true (nullable поле)", () => {
    expect(isValidFinding({ ...validFinding, snippet: null })).toBe(true);
  });

  it("finding с неизвестным severity → false", () => {
    expect(isValidFinding({ ...validFinding, severity: "High" })).toBe(false);
  });

  it("finding с неизвестным dialect → false", () => {
    expect(isValidFinding({ ...validFinding, dialect: "oracle" })).toBe(false);
  });

  it("пустой объект → false", () => {
    expect(isValidFinding({})).toBe(false);
  });

  it("null → false", () => {
    expect(isValidFinding(null)).toBe(false);
  });

  it("числовое значение → false", () => {
    expect(isValidFinding(42)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// SqlAntipatternsResponse shape
// ---------------------------------------------------------------------------

describe("SqlAntipatternsResponse structure", () => {
  it("успешный response имеет ok=true и findings", () => {
    const resp: SqlAntipatternsResponse = {
      ok: true,
      engine: "mssql",
      is_1c_context: true,
      findings: [],
    };
    expect(resp.ok).toBe(true);
    expect(resp.engine).toBe("mssql");
    expect(Array.isArray(resp.findings)).toBe(true);
  });

  it("error response имеет ok=false", () => {
    const resp: SqlAntipatternsResponse = {
      ok: false,
      error: "engine must be mssql or postgres",
    };
    expect(resp.ok).toBe(false);
    expect(resp.error).toBeTruthy();
  });

  it("findings с полными данными все проходят валидацию", () => {
    const finding: SqlAntipatternFinding = {
      code: "not_in_with_subquery",
      title: "NOT IN с подзапросом",
      description: "NULL propagation",
      severity: "Critical",
      dialect: "postgres",
      is_1c_context_only: false,
      snippet: "WHERE id NOT IN (SELECT ...)",
      rationale: "NOT IN с NULL даёт неожиданные результаты",
      recommendation: "Использовать NOT EXISTS",
    };
    const resp: SqlAntipatternsResponse = {
      ok: true,
      engine: "postgres",
      is_1c_context: false,
      findings: [finding],
    };
    expect(resp.findings?.every(isValidFinding)).toBe(true);
  });
});
