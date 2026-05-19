import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
import { backend, type AiExplanationResult, type RuleClassifyResult } from "@/api/backend";

interface Props {
  archiveId: string;
  anatomyKind: "deadlock" | "operation" | "session" | "lock" | "exception" | "slow_op";
  targetId: string;
  features: Record<string, unknown>;
  anatomyData: Record<string, unknown>;
}

export function ExplainerCard({ archiveId, anatomyKind, targetId, features, anatomyData }: Props) {
  const [rule, setRule] = useState<RuleClassifyResult | null>(null);
  const [ai, setAi] = useState<AiExplanationResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    if (!archiveId || !targetId) return;
    let cancelled = false;

    // Step 1 — instant rule-based classification
    backend
      .explainerClassify(archiveId, anatomyKind, targetId, features)
      .then((res) => {
        if (!cancelled) setRule(res);
      })
      .catch(() => {
        if (!cancelled) setRule(null);
      });

    // Step 2 — AI fire-and-forget (3-15 sec), кеш-aware
    setAiLoading(true);
    setAi(null);
    backend
      .explainerAi(
        archiveId,
        anatomyKind,
        targetId,
        anatomyData,
        null, // rule_id и rule_body заполним после получения rule (но запрос отправляем сразу)
        null,
      )
      .then((res) => {
        if (!cancelled) setAi(res);
      })
      .catch(() => {
        if (!cancelled) setAi({ ok: false, error: "AI call failed" });
      })
      .finally(() => {
        if (!cancelled) setAiLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [archiveId, anatomyKind, targetId, JSON.stringify(features)]);

  // Если ни rule ни AI ничего не дали — компактное сообщение
  if (rule && !rule.matched && !aiLoading && (!ai || !ai.ok)) {
    return (
      <div style={cardStyle}>
        <div style={titleStyle}>
          <span style={iconStyle}>💡</span> Объяснение
        </div>
        <div style={bodyMutedStyle}>
          Для этого паттерна нет подходящего готового правила.
          {ai?.error && (
            <div style={errLineStyle}>AI: {ai.error}</div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <div style={titleStyle}>
        <span style={iconStyle}>💡</span>
        {rule?.matched ? rule.title : "Объяснение"}
        {/* Spinner пока генерируется AI-ответ — единственный visible сигнал.
            Cache hit отдаётся за ~10ms и spinner едва мелькает; новая генерация
            занимает 3-15 сек и spinner информативен. Бейджи "AI/кеш/токены"
            убраны — это технические детали для разработчика, а не для юзера. */}
        {aiLoading && (
          <span style={aiLoadingStyle}>генерируется развёрнутое объяснение…</span>
        )}
      </div>

      {/* AI text если есть — приоритет над rule body */}
      {ai?.ok && ai.text ? (
        <div style={aiBodyStyle}>
          <Markdown text={ai.text} />
        </div>
      ) : rule?.matched && rule.body ? (
        <div style={ruleBodyStyle}>
          <Markdown text={rule.body} />
        </div>
      ) : null}

      {/* AI error показываем ТОЛЬКО когда rule НЕ matched. Если rule сработал —
          у пользователя уже есть полное объяснение, AI failure нерелевантен
          и только запутывает (visible на скрине: одновременно rule body +
          "AI not configured" → confused user). */}
      {ai && !ai.ok && ai.error && !rule?.matched && (
        <div style={errLineStyle}>
          AI: {ai.error}
          {ai.enabled === false && " (ANTHROPIC_API_KEY не задан в .env)"}
        </div>
      )}
    </div>
  );
}

function Markdown({ text }: { text: string }) {
  // Минимальный markdown render — заголовки + параграфы + bullet lists.
  // Полноценный markdown — отдельная зависимость; пока inline для одной функции.
  const blocks = text.split(/\n\n+/);
  return (
    <>
      {blocks.map((block, i) => {
        if (block.startsWith("# ")) {
          return <h3 key={i} style={h3Style}>{block.slice(2)}</h3>;
        }
        if (block.startsWith("## ")) {
          return <h4 key={i} style={h4Style}>{block.slice(3)}</h4>;
        }
        // bullet list
        if (block.split("\n").every((line) => line.trim().startsWith("- ") || line.trim().startsWith("* "))) {
          const items = block.split("\n").map((l) => l.trim().replace(/^[-*]\s+/, ""));
          return (
            <ul key={i} style={listStyle}>
              {items.map((item, j) => (
                <li key={j} style={listItemStyle}>{renderInline(item)}</li>
              ))}
            </ul>
          );
        }
        // numbered list
        if (block.split("\n").every((line) => /^\d+\.\s/.test(line.trim()))) {
          const items = block.split("\n").map((l) => l.trim().replace(/^\d+\.\s+/, ""));
          return (
            <ol key={i} style={listStyle}>
              {items.map((item, j) => (
                <li key={j} style={listItemStyle}>{renderInline(item)}</li>
              ))}
            </ol>
          );
        }
        return <p key={i} style={pStyle}>{renderInline(block)}</p>;
      })}
    </>
  );
}

function renderInline(s: string): React.ReactNode {
  // **bold** и `code`
  const parts: React.ReactNode[] = [];
  let buf = "";
  let i = 0;
  while (i < s.length) {
    if (s.startsWith("**", i)) {
      if (buf) {
        parts.push(buf);
        buf = "";
      }
      const end = s.indexOf("**", i + 2);
      if (end < 0) {
        buf += s.slice(i);
        i = s.length;
        break;
      }
      parts.push(<strong key={parts.length}>{s.slice(i + 2, end)}</strong>);
      i = end + 2;
    } else if (s[i] === "`") {
      if (buf) {
        parts.push(buf);
        buf = "";
      }
      const end = s.indexOf("`", i + 1);
      if (end < 0) {
        buf += s.slice(i);
        i = s.length;
        break;
      }
      parts.push(
        <code key={parts.length} style={codeInlineStyle}>
          {s.slice(i + 1, end)}
        </code>,
      );
      i = end + 1;
    } else {
      buf += s[i];
      i += 1;
    }
  }
  if (buf) parts.push(buf);
  return <>{parts}</>;
}

const cardStyle: CSSProperties = {
  background: "linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)",
  border: "1px solid #FDE68A",
  borderRadius: 6,
  padding: 16,
  marginBottom: 12,
};

const titleStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  fontSize: 14,
  fontWeight: 600,
  color: "#78350F",
  marginBottom: 8,
};

const iconStyle: CSSProperties = {
  fontSize: 16,
};

const aiLoadingStyle: CSSProperties = {
  marginLeft: 8,
  fontSize: 10.5,
  fontWeight: 400,
  color: "#92400E",
  fontFamily: "var(--o-font-mono)",
  fontStyle: "italic",
};


const aiBodyStyle: CSSProperties = {
  color: "#451A03",
  fontSize: 13,
  lineHeight: 1.6,
};

const ruleBodyStyle: CSSProperties = {
  color: "#451A03",
  fontSize: 13,
  lineHeight: 1.6,
};

const bodyMutedStyle: CSSProperties = {
  color: "#92400E",
  fontSize: 12,
  fontStyle: "italic",
};

const errLineStyle: CSSProperties = {
  marginTop: 8,
  padding: 8,
  background: "rgba(220, 38, 38, 0.05)",
  border: "1px solid rgba(220, 38, 38, 0.2)",
  borderRadius: 4,
  fontSize: 11,
  color: "#7F1D1D",
  fontFamily: "var(--o-font-mono)",
};

const h3Style: CSSProperties = { fontSize: 14, fontWeight: 600, margin: "8px 0 4px", color: "#451A03" };
const h4Style: CSSProperties = { fontSize: 12.5, fontWeight: 600, margin: "8px 0 4px", color: "#78350F", textTransform: "uppercase", letterSpacing: "0.04em" };
const pStyle: CSSProperties = { margin: "4px 0", lineHeight: 1.55 };
const listStyle: CSSProperties = { margin: "4px 0 4px 20px", padding: 0 };
const listItemStyle: CSSProperties = { margin: "2px 0", lineHeight: 1.5 };
const codeInlineStyle: CSSProperties = {
  fontFamily: "var(--o-font-mono)",
  fontSize: 11.5,
  background: "rgba(180, 83, 9, 0.1)",
  padding: "1px 4px",
  borderRadius: 2,
};
