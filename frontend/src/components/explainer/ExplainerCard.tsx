import type { CSSProperties } from "react";
import { useCallback, useEffect, useState } from "react";
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
  const [aiRequested, setAiRequested] = useState(false);

  // Rule-based classification — instant, кеш в backend, дешёво. Запускаем
  // сразу при mount.
  //
  // AI: на mount делаем read-only проверку кеша (explainer_check_cache — НЕ
  // вызывает Claude API). Если объяснение уже было сгенерировано раньше —
  // показываем его сразу, без кнопки. Если кеша нет — показываем кнопку.
  // Так пользователь не платит за повторную генерацию того же самого
  // объяснения, но и не тратит токены автоматически на новые операции
  // (это требование Fix #10, "только по кнопке").
  useEffect(() => {
    if (!archiveId || !targetId) return;
    let cancelled = false;

    // При смене операции сбрасываем AI-state до проверки кеша.
    setAi(null);
    setAiRequested(false);
    setAiLoading(false);

    backend
      .explainerClassify(archiveId, anatomyKind, targetId, features)
      .then((res) => {
        if (!cancelled) setRule(res);
      })
      .catch(() => {
        if (!cancelled) setRule(null);
      });

    backend
      .explainerCheckCache(archiveId, anatomyKind, targetId)
      .then((res) => {
        if (cancelled || !res.found || !res.text) return;
        setAi({
          ok: true,
          text: res.text,
          from_cache: true,
          model: res.model,
          tokens_in: res.tokens_in,
          tokens_out: res.tokens_out,
          created_at: res.created_at,
        });
        // aiRequested = true чтобы UI не показывал кнопку «Сгенерировать»
        // когда объяснение уже есть (даже если rule.matched=false).
        setAiRequested(true);
      })
      .catch(() => {
        // Если check_cache упал — продолжаем как будто кеша нет.
      });

    return () => {
      cancelled = true;
    };
  }, [archiveId, anatomyKind, targetId, JSON.stringify(features)]);

  const onRequestAi = useCallback(() => {
    if (aiLoading || aiRequested) return;
    setAiRequested(true);
    setAiLoading(true);
    setAi(null);
    backend
      .explainerAi(archiveId, anatomyKind, targetId, anatomyData, null, null)
      .then((res) => setAi(res))
      .catch(() => setAi({ ok: false, error: "AI call failed" }))
      .finally(() => setAiLoading(false));
  }, [archiveId, anatomyKind, targetId, anatomyData, aiLoading, aiRequested]);

  // Если rule не сработал и AI ещё не запрашивался — компактное сообщение
  // + кнопка для AI (вдруг AI знает что rule не сумел распознать).
  if (rule && !rule.matched && !aiRequested) {
    return (
      <div style={cardStyle}>
        <div style={titleStyle}>
          <span style={iconStyle}>💡</span> Объяснение
        </div>
        <div style={bodyMutedStyle}>
          Для этого паттерна нет подходящего готового правила.
        </div>
        <button type="button" style={aiButtonStyle} onClick={onRequestAi}>
          ✨ Сгенерировать AI-объяснение
        </button>
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <div style={titleStyle}>
        <span style={iconStyle}>💡</span>
        {rule?.matched ? rule.title : "Объяснение"}
        {aiLoading && (
          <span style={aiLoadingStyle}>думаю…</span>
        )}
      </div>

      {/* Body: AI приоритетнее rule если он успешно вернулся (содержит ту же
          rule-инфу + расширения). Иначе показываем rule body. */}
      {ai?.ok && ai.text ? (
        <div style={aiBodyStyle}>
          <Markdown text={ai.text} />
        </div>
      ) : rule?.matched && rule.body ? (
        <div style={ruleBodyStyle}>
          <Markdown text={rule.body} />
        </div>
      ) : null}

      {/* Янтарная кнопка "Сгенерировать AI-объяснение" — показываем если
          AI ещё не запрашивался. После клика — кнопка скрывается, в
          заголовке появляется "думаю…", потом ai body (или ошибка). */}
      {!aiRequested && rule?.matched && (
        <button type="button" style={aiButtonStyle} onClick={onRequestAi}>
          ✨ Сгенерировать AI-объяснение
        </button>
      )}

      {/* AI error показываем ТОЛЬКО когда rule НЕ matched. Если rule сработал
          — у пользователя уже есть rule-объяснение, AI failure нерелевантен. */}
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

const aiButtonStyle: CSSProperties = {
  marginTop: 12,
  padding: "8px 14px",
  background: "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)",
  color: "#FFFBEB",
  border: "1px solid #B45309",
  borderRadius: 6,
  fontFamily: "inherit",
  fontSize: 12.5,
  fontWeight: 600,
  cursor: "pointer",
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  boxShadow: "0 1px 2px rgba(180, 83, 9, 0.18)",
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
