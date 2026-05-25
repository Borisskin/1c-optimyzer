/**
 * Sprint 8 Phase B — тесты для detectPlanEngine.
 *
 * Coverage: 20+ test cases для разных реальных planов из Sprint 7
 * (research/* MSSQL .sqlplan) и Sprint 8 Phase A discovery
 * (tools/sprint8_discovery/pg_tj_samples/ + pg_plans/).
 */

import { describe, expect, it } from "vitest";
import { detectPlanEngine, detectPlanFormat } from "./detectPlanEngine";

// === MSSQL XML samples ===

const MSSQL_XML_FULL = `<?xml version="1.0" encoding="utf-16"?>
<ShowPlanXML xmlns="http://schemas.microsoft.com/sqlserver/2004/07/showplan" Version="1.564" Build="16.0.4150.1">
  <BatchSequence>
    <Batch>
      <Statements>
        <StmtSimple StatementText="SELECT 1" StatementId="1">
          <QueryPlan>
            <RelOp NodeId="0" PhysicalOp="Clustered Index Seek" />
          </QueryPlan>
        </StmtSimple>
      </Statements>
    </Batch>
  </BatchSequence>
</ShowPlanXML>`;

const MSSQL_XML_NAKED = `<ShowPlanXML xmlns="http://schemas.microsoft.com/sqlserver/2004/07/showplan">
  <RelOp PhysicalOp="Clustered Index Seek" />
</ShowPlanXML>`;

const MSSQL_XML_STMT_ONLY = `<StmtSimple StatementText="SELECT 1" StatementId="1">
  <QueryPlan />
</StmtSimple>`;

// === MSSQL SHOWPLAN_TEXT samples ===

const MSSQL_TEXT_BASIC = `|--Clustered Index Seek(OBJECT:([db].[dbo].[_Reference15]))
|     SEEK:([_Reference15].[_IDRRef] = (?))
|     Estimated Rows = 1`;

const MSSQL_TEXT_HASH_MATCH = `Hash Match(Inner Join, HASH:([t1].[id])=([t2].[id]))
  |--Clustered Index Scan(OBJECT:([db].[dbo].[t1]))
  |--Clustered Index Scan(OBJECT:([db].[dbo].[t2]))`;

const MSSQL_TEXT_AGG = `Stream Aggregate(GROUP BY:([_Document100].[_Date]))
  |--Sort(ORDER BY:([_Document100].[_Date] ASC))
       |--Clustered Index Scan(OBJECT:([_Document100]))`;

// === PostgreSQL EXPLAIN TEXT samples ===

const PG_TEXT_FULL = `Seq Scan on pg_catalog.pg_tablespace  (cost=0.00..1.02 rows=2 width=64) (actual time=0.011..0.011 rows=0.00 loops=1)
  Output: spcname
  Filter: ((pg_tablespace.spcname = 'v81c_index'::name) OR (pg_tablespace.spcname = 'v81c_data'::name))
  Rows Removed by Filter: 2
  Buffers: shared hit=1
Planning Time: 0.783 ms
Execution Time: 0.024 ms`;

const PG_TEXT_JOIN = `Hash Join  (cost=12.50..100.30 rows=500 width=12) (actual time=0.5..2.3 rows=480 loops=1)
  Hash Cond: (a.id = b.a_id)
  -> Seq Scan on table_a a  (cost=0.00..10.00 rows=500 width=4)
  -> Hash  (cost=5.00..5.00 rows=500 width=8)
        -> Seq Scan on table_b b  (cost=0.00..5.00 rows=500 width=8)
Planning Time: 0.15 ms
Execution Time: 2.55 ms`;

const PG_TEXT_INDEX_ONLY = `Index Only Scan using _document201_pk on public._document201  (cost=0.42..8.44 rows=1 width=16)
  Index Cond: (_idrref = '\\\\x123456'::bytea)
  Heap Fetches: 0
Planning Time: 0.05 ms
Execution Time: 0.08 ms`;

const PG_TEXT_NO_ANALYZE = `Seq Scan on _reference15  (cost=0.00..1500.00 rows=10000 width=120)
  Filter: (_fld11355 = 1)`;

const PG_TEXT_MEMOIZE = `Nested Loop  (cost=0.43..5.50 rows=10 width=12)
  -> Memoize  (cost=0.10..2.50 rows=10 width=8)
        Cache Key: a.id
  -> Index Scan using b_pk on b  (cost=0.33..3.00 rows=1 width=4)
Planning Time: 0.2 ms
Execution Time: 1.8 ms`;

// === PostgreSQL JSON samples ===

const PG_JSON_ARRAY = JSON.stringify([
  {
    Plan: {
      "Node Type": "Seq Scan",
      "Relation Name": "_reference15",
      "Total Cost": 100.5,
    },
    "Planning Time": 0.15,
    "Execution Time": 2.55,
  },
]);

const PG_JSON_OBJECT = JSON.stringify({
  Plan: { "Node Type": "Index Scan", "Index Name": "_pk" },
});

// === Edge cases ===

const EMPTY = "";
const WHITESPACE_ONLY = "   \n\n  \t  ";
const RANDOM_TEXT = "Это случайный текст без признаков плана запроса.";
const HTML_FRAGMENT = "<div>Hello</div>";
const BROKEN_JSON = "{this is not json}";

// ============================================================
// Tests
// ============================================================

describe("detectPlanEngine — MSSQL XML format", () => {
  it("полный .sqlplan от SSMS → mssql/xml", () => {
    const r = detectPlanEngine(MSSQL_XML_FULL);
    expect(r.engine).toBe("mssql");
    expect(r.format).toBe("xml");
  });

  it("ShowPlanXML без XML declaration → mssql/xml", () => {
    const r = detectPlanEngine(MSSQL_XML_NAKED);
    expect(r.engine).toBe("mssql");
    expect(r.format).toBe("xml");
  });

  it("StmtSimple отдельным фрагментом → mssql/xml", () => {
    const r = detectPlanEngine(MSSQL_XML_STMT_ONLY);
    expect(r.engine).toBe("mssql");
    expect(r.format).toBe("xml");
  });
});

describe("detectPlanEngine — MSSQL SHOWPLAN_TEXT", () => {
  it("базовый |-- indent + Clustered Index Seek → mssql/text", () => {
    const r = detectPlanEngine(MSSQL_TEXT_BASIC);
    expect(r.engine).toBe("mssql");
    expect(r.format).toBe("text");
  });

  it("Hash Match join → mssql/text", () => {
    const r = detectPlanEngine(MSSQL_TEXT_HASH_MATCH);
    expect(r.engine).toBe("mssql");
    expect(r.format).toBe("text");
  });

  it("Stream Aggregate + Sort → mssql/text", () => {
    const r = detectPlanEngine(MSSQL_TEXT_AGG);
    expect(r.engine).toBe("mssql");
    expect(r.format).toBe("text");
  });
});

describe("detectPlanEngine — PostgreSQL EXPLAIN TEXT", () => {
  it("Seq Scan + Planning/Execution Time → postgres/text", () => {
    const r = detectPlanEngine(PG_TEXT_FULL);
    expect(r.engine).toBe("postgres");
    expect(r.format).toBe("text");
  });

  it("Hash Join с -> arrows → postgres/text", () => {
    const r = detectPlanEngine(PG_TEXT_JOIN);
    expect(r.engine).toBe("postgres");
    expect(r.format).toBe("text");
  });

  it("Index Only Scan на 1С-таблице → postgres/text", () => {
    const r = detectPlanEngine(PG_TEXT_INDEX_ONLY);
    expect(r.engine).toBe("postgres");
    expect(r.format).toBe("text");
  });

  it("план без ANALYZE (только cost=) → postgres/text", () => {
    const r = detectPlanEngine(PG_TEXT_NO_ANALYZE);
    expect(r.engine).toBe("postgres");
    expect(r.format).toBe("text");
  });

  it("Memoize node (PG 14+) → postgres/text", () => {
    const r = detectPlanEngine(PG_TEXT_MEMOIZE);
    expect(r.engine).toBe("postgres");
    expect(r.format).toBe("text");
  });
});

describe("detectPlanEngine — PostgreSQL JSON", () => {
  it("array из EXPLAIN (FORMAT JSON) → postgres/json", () => {
    const r = detectPlanEngine(PG_JSON_ARRAY);
    expect(r.engine).toBe("postgres");
    expect(r.format).toBe("json");
  });

  it("одиночный объект с Plan → postgres/json", () => {
    const r = detectPlanEngine(PG_JSON_OBJECT);
    expect(r.engine).toBe("postgres");
    expect(r.format).toBe("json");
  });
});

describe("detectPlanEngine — edge cases", () => {
  it("пустая строка → unknown/text", () => {
    const r = detectPlanEngine(EMPTY);
    expect(r.engine).toBe("unknown");
    expect(r.format).toBe("text");
  });

  it("только whitespace → unknown/text", () => {
    const r = detectPlanEngine(WHITESPACE_ONLY);
    expect(r.engine).toBe("unknown");
    expect(r.format).toBe("text");
  });

  it("случайный текст без признаков → unknown/text", () => {
    const r = detectPlanEngine(RANDOM_TEXT);
    expect(r.engine).toBe("unknown");
    expect(r.format).toBe("text");
  });

  it("HTML фрагмент → unknown (не MSSQL XML)", () => {
    const r = detectPlanEngine(HTML_FRAGMENT);
    // <div> не матчит SSMS-tags → fallback на TEXT detection,
    // там тоже нет PG/MSSQL сигнатур → unknown.
    expect(r.engine).toBe("unknown");
  });

  it("сломанный JSON → не падает, fallback на text detection", () => {
    const r = detectPlanEngine(BROKEN_JSON);
    expect(r.engine).toBe("unknown");
    expect(r.format).toBe("text");
  });
});

describe("detectPlanFormat — standalone format detection", () => {
  it("XML → xml", () => {
    expect(detectPlanFormat(MSSQL_XML_FULL)).toBe("xml");
  });

  it("JSON array → json", () => {
    expect(detectPlanFormat(PG_JSON_ARRAY)).toBe("json");
  });

  it("PG text → text", () => {
    expect(detectPlanFormat(PG_TEXT_FULL)).toBe("text");
  });

  it("MSSQL text → text", () => {
    expect(detectPlanFormat(MSSQL_TEXT_BASIC)).toBe("text");
  });

  it("пустая → text", () => {
    expect(detectPlanFormat("")).toBe("text");
  });
});
