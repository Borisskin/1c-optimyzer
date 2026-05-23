import type { CSSProperties } from "react";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { backend, type AiExplanationResult, type RuleClassifyResult } from "@/api/backend";
import { cloud, CloudError } from "@/api/cloud";
import { useAccountStore } from "@/store/accountStore";
import { PaywallModal } from "@/components/overlays/PaywallModal";

interface Props {
  archiveId: string;
  anatomyKind: "deadlock" | "operation" | "session" | "lock" | "exception" | "slow_op";
  targetId: string;
  features: Record<string, unknown>;
  anatomyData: Record<string, unknown>;
}

/**
 * Компактная карточка-объяснение для anatomy-view.
 *
 * UX (Sprint 5 feedback batch 4):
 *  - Если контента нет (rule не сматчил И AI ещё не запрашивался) —
 *    показываем ТОЛЬКО тонкую кнопку-ссылку «Объяснить через AI». Никаких
 *    больших жёлтых баннеров «нет правила».
 *  - Если есть rule-объяснение ИЛИ AI-текст — разворачиваем полноценную
 *    панель с заголовком и markdown-телом.
 *  - Иконки — из общей Icon-системы (минималистичные SVG, currentColor),
 *    без эмодзи 💡✨.
 *  - Цвет панели — нейтральный синий-accent (а не «алертный жёлтый»):
 *    объяснение это полезная информация, а не предупреждение.
 *
 * AI-кеш проверяется на mount через explainer_check_cache (read-only RPC,
 * не дёргает Claude API). Если объяснение уже есть в БД — показываем сразу.
 */
export function ExplainerCard({ archiveId, anatomyKind, targetId, features, anatomyData }: Props) {
  const [rule, setRule] = useState<RuleClassifyResult | null>(null);
  const [ai, setAi] = useState<AiExplanationResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiRequested, setAiRequested] = useState(false);
  const [paywall, setPaywall] = useState<{
    open: boolean;
    reason: string | null;
    freeRemaining: number | null;
  }>({ open: false, reason: null, freeRemaining: null });

  const accessToken = useAccountStore((s) => s.accessToken);

  useEffect(() => {
    if (!archiveId || !targetId) return;
    let cancelled = false;

    setRule(null);
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
        setAiRequested(true);
      })
      .catch(() => {
        /* кеша нет — продолжаем как обычно */
      });

    return () => {
      cancelled = true;
    };
  }, [archiveId, anatomyKind, targetId, JSON.stringify(features)]);

  const onRequestAi = useCallback(async () => {
    if (aiLoading || aiRequested) return;

    // Без активации AI запрещён — не можем учитывать генерации, не можем
    // enforce'ить лимиты. Показываем paywall с CTA «Зарегистрируйтесь».
    if (!accessToken) {
      setPaywall({
        open: true,
        reason: "not_authenticated",
        freeRemaining: null,
      });
      return;
    }

    // Soft cap check — есть accessToken.
    try {
      const check = await cloud.checkUsage(accessToken);
      if (!check.allowed) {
        setPaywall({
          open: true,
          reason: check.reason,
          freeRemaining: check.free_quota_remaining,
        });
        return;
      }
    } catch (err) {
      // Cloud недоступен — не блокируем активного юзера (graceful degradation).
      // Просто логируем и продолжаем — но только если accessToken есть.
      console.warn("Soft cap check failed:", (err as CloudError).message);
    }

    setAiRequested(true);
    setAiLoading(true);
    setAi(null);

    let aiResult: AiExplanationResult | null = null;
    let success = false;
    try {
      aiResult = await backend.explainerAi(
        archiveId,
        anatomyKind,
        targetId,
        anatomyData,
        null,
        null,
      );
      success = !!aiResult?.ok;
      setAi(aiResult);
    } catch {
      setAi({ ok: false, error: "AI call failed" });
    } finally {
      setAiLoading(false);
    }

    // Best-effort report в cloud. Не блокирует UI.
    if (accessToken) {
      const opType =
        anatomyKind === "deadlock"
          ? "ai_deadlock_explanation"
          : "ai_explanation";
      void cloud
        .trackUsage(accessToken, {
          operationType: opType,
          archiveHash: null,
          success,
          aiTokensInput: aiResult?.tokens_in ?? undefined,
          aiTokensOutput: aiResult?.tokens_out ?? undefined,
        })
        .catch((err) => {
          console.warn("Usage tracking failed:", (err as CloudError).message);
        });
    }
  }, [
    accessToken,
    aiLoading,
    aiRequested,
    archiveId,
    anatomyKind,
    targetId,
    anatomyData,
  ]);

  const hasRuleBody = Boolean(rule?.matched && rule.body);
  const hasAiText = Boolean(ai?.ok && ai.text);
  const hasContent = hasRuleBody || hasAiText;
  const aiError = ai && !ai.ok ? ai.error : null;

  // Compact mode: правил нет, AI не запрашивался, ошибок нет —
  // только тонкая inline-кнопка, никакой большой панели.
  if (!hasContent && !aiLoading && !aiRequested && !aiError) {
    return (
      <>
        <button type="button" style={compactBtnStyle} onClick={onRequestAi}>
          <Icon name="Brain" size={13} color="var(--o-accent)" />
          <span>Объяснить через AI</span>
          <Icon name="ArrowRight" size={11} color="var(--o-accent)" />
        </button>
        <PaywallModal
          open={paywall.open}
          reason={paywall.reason}
          freeQuotaRemaining={paywall.freeRemaining}
          onClose={() => setPaywall({ open: false, reason: null, freeRemaining: null })}
        />
      </>
    );
  }

  // Loading mode: показываем компактную «думающую» строку, не разворачивая
  // пустую панель.
  if (aiLoading && !hasContent) {
    return (
      <div style={loadingRowStyle}>
        <Icon name="Brain" size={13} color="var(--o-accent)" className="pulse" />
        <span>AI готовит объяснение…</span>
      </div>
    );
  }

  // Full panel: есть rule body или AI text (или AI вернул ошибку).
  return (
    <div style={cardStyle}>
      <div style={titleRowStyle}>
        <Icon name={hasAiText ? "Brain" : "Info"} size={14} color="var(--o-accent)" />
        <span style={titleTextStyle}>
          {rule?.matched ? rule.title : "Объяснение"}
        </span>
        {hasAiText && (
          <span style={aiBadgeStyle} title="Объяснение сгенерировано AI">AI</span>
        )}
        {aiLoading && (
          <span style={loadingHintStyle}>обновляю…</span>
        )}
      </div>

      {hasAiText ? (
        <div style={bodyStyle}>
          <Markdown text={ai!.text!} />
        </div>
      ) : hasRuleBody ? (
        <div style={bodyStyle}>
          <Markdown text={rule!.body!} />
        </div>
      ) : null}

      {/* Кнопка «Объяснить через AI» — показываем когда есть rule body,
          но AI ещё не запрашивался (юзер может захотеть второе мнение). */}
      {!aiRequested && hasRuleBody && (
        <button type="button" style={inlineAiBtnStyle} onClick={onRequestAi}>
          <Icon name="Brain" size={12} color="var(--o-accent)" />
          <span>Объяснить через AI</span>
        </button>
      )}

      {aiError && !rule?.matched && (
        <div style={errLineStyle}>
          AI: {aiError}
          {ai!.enabled === false && " (ANTHROPIC_API_KEY не задан в .env)"}
        </div>
      )}

      <PaywallModal
        open={paywall.open}
        reason={paywall.reason}
        freeQuotaRemaining={paywall.freeRemaining}
        onClose={() => setPaywall({ open: false, reason: null, freeRemaining: null })}
      />
    </div>
  );
}

// ---------- Markdown render (минимальный inline) ----------

function Markdown({ text }: { text: string }) {
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

// ---------- Styles ----------
// Палитра: нейтральный фон (subtle), accent-синий для иконок и AI-бейджа.
// Без жёлтого «алертного» цвета — объяснение это полезная информация,
// а не предупреждение.

const compactBtnStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "6px 10px",
  marginBottom: 12,
  border: "1px solid var(--o-border-2)",
  borderRadius: 6,
  background: "transparent",
  color: "var(--o-text-2)",
  fontSize: 12,
  fontFamily: "inherit",
  cursor: "pointer",
  transition: "border-color 120ms ease, background 120ms ease",
};

const loadingRowStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  padding: "8px 12px",
  marginBottom: 12,
  border: "1px solid var(--o-border-2)",
  borderRadius: 6,
  background: "var(--o-subtle)",
  color: "var(--o-text-2)",
  fontSize: 12,
  fontFamily: "inherit",
};

const cardStyle: CSSProperties = {
  background: "var(--o-panel)",
  border: "1px solid var(--o-border)",
  borderLeft: "3px solid var(--o-accent)",
  borderRadius: 6,
  padding: "12px 16px",
  marginBottom: 12,
};

const titleRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  marginBottom: 8,
};

const titleTextStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: "var(--o-text-1)",
};

const aiBadgeStyle: CSSProperties = {
  padding: "1px 6px",
  borderRadius: 3,
  background: "var(--o-accent)",
  color: "#fff",
  fontSize: 9.5,
  fontWeight: 600,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  fontFamily: "var(--o-font-mono)",
};

const loadingHintStyle: CSSProperties = {
  marginLeft: 4,
  fontSize: 11,
  color: "var(--o-text-3)",
  fontFamily: "var(--o-font-mono)",
  fontStyle: "italic",
};

const bodyStyle: CSSProperties = {
  color: "var(--o-text-1)",
  fontSize: 13,
  lineHeight: 1.55,
};

const inlineAiBtnStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  marginTop: 10,
  padding: "5px 9px",
  border: "1px solid var(--o-border-2)",
  borderRadius: 4,
  background: "transparent",
  color: "var(--o-text-2)",
  fontSize: 11.5,
  fontFamily: "inherit",
  cursor: "pointer",
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

const h3Style: CSSProperties = { fontSize: 13.5, fontWeight: 600, margin: "8px 0 4px", color: "var(--o-text-1)" };
const h4Style: CSSProperties = { fontSize: 12, fontWeight: 600, margin: "8px 0 4px", color: "var(--o-text-2)", textTransform: "uppercase", letterSpacing: "0.04em" };
const pStyle: CSSProperties = { margin: "4px 0", lineHeight: 1.5 };
const listStyle: CSSProperties = { margin: "4px 0 4px 20px", padding: 0 };
const listItemStyle: CSSProperties = { margin: "2px 0", lineHeight: 1.5 };
const codeInlineStyle: CSSProperties = {
  fontFamily: "var(--o-font-mono)",
  fontSize: 11.5,
  background: "var(--o-subtle)",
  color: "var(--o-text-1)",
  padding: "1px 4px",
  borderRadius: 2,
};
