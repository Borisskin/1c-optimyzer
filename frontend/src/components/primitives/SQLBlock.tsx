// Простой SQL syntax highlighter. Портировано из design/opt/shared.jsx (hlSQL).

import type { ReactElement } from "react";

const KW_EN =
  /\b(SELECT|FROM|WHERE|AND|OR|GROUP BY|ORDER BY|JOIN|INNER|LEFT|RIGHT|ON|AS|SUM|COUNT|MAX|MIN|CASE|WHEN|THEN|ELSE|END|TOP|LIMIT|HAVING|UNION|ALL|IN|EXISTS|NOT|IS|NULL|DISTINCT|WITH|INDEX|CREATE|INCLUDE|UPDATE|STATISTICS)\b/g;
const KW_RU =
  /\b(ВЫБРАТЬ|ИЗ|ГДЕ|И|ИЛИ|СГРУППИРОВАТЬ ПО|УПОРЯДОЧИТЬ ПО|СОЕДИНЕНИЕ|ВНУТРЕННЕЕ|ЛЕВОЕ|ПРАВОЕ|ПО|КАК|СУММА|КОЛИЧЕСТВО|МАКСИМУМ|МИНИМУМ|ВЫБОР|КОГДА|ТОГДА|ИНАЧЕ|КОНЕЦ|ИМЕЮЩИЕ|ОБЪЕДИНИТЬ|ВСЕ|В|НЕ|ЕСТЬ|NULL|РАЗЛИЧНЫЕ|РегистрНакопления|Документ|Справочник|Регистр|В ИЕРАРХИИ|ИЕРАРХИИ)\b/g;

interface Part {
  t: string;
  c: string | null;
}

function tokenize(input: string): Part[] {
  let parts: Part[] = [{ t: input, c: null }];
  const apply = (re: RegExp, color: string) => {
    const out: Part[] = [];
    for (const p of parts) {
      if (p.c) {
        out.push(p);
        continue;
      }
      let last = 0;
      let m: RegExpExecArray | null;
      re.lastIndex = 0;
      while ((m = re.exec(p.t))) {
        if (m.index > last) out.push({ t: p.t.slice(last, m.index), c: null });
        out.push({ t: m[0], c: color });
        last = m.index + m[0].length;
      }
      if (last < p.t.length) out.push({ t: p.t.slice(last), c: null });
    }
    parts = out;
  };
  apply(KW_EN, "var(--o-accent)");
  apply(KW_RU, "var(--o-accent)");
  apply(/\b\d+(\.\d+)?\b/g, "var(--o-warn)");
  apply(/'[^']*'/g, "var(--o-ok)");
  apply(/--.*$/gm, "var(--o-text-4)");
  apply(/\b(T\d+|t\d+)\.(_?[A-Za-z0-9_]+)/g, "var(--o-info)");
  apply(/_[A-Z][A-Za-z0-9_]+/g, "var(--o-violet)");
  return parts;
}

export function SQLBlock({ children, className }: { children: string; className?: string }) {
  const parts = tokenize(children);
  return (
    <pre className={`mono codebox ${className || ""}`} style={{ padding: 10, fontSize: 12, lineHeight: 1.55 }}>
      {parts.map((p, i) =>
        p.c ? (
          <span key={i} style={{ color: p.c }}>
            {p.t}
          </span>
        ) : (
          <span key={i}>{p.t}</span>
        ),
      )}
    </pre>
  );
}
