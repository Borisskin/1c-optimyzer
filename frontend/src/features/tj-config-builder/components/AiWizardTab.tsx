/**
 * Sprint 10 — AiWizardTab: AI-генерация настройки logcfg.xml.
 * Описание проблемы → Haiku → структурированный ответ + кнопка «Применить».
 */
import { useState, useCallback } from "react";
import type { LogcfgConfig } from "../types";
import { cloud, CloudError } from "@/api/cloud";
import type { AiLogcfgGenerateResponse } from "@/api/cloud";
import styles from "./AiWizardTab.module.css";

interface Props {
  platformVersion: string | null;
  onApply: (config: LogcfgConfig) => void;
}

type Status = "idle" | "loading" | "done" | "error";

// Типичные описания проблем для вдохновения юзера
const EXAMPLE_PROMPTS = [
  "Тормозит проведение документов в обед",
  "Дедлоки при работе 50 пользователей",
  "1С на PostgreSQL медленно работает с регистрами",
  "Закрытие месяца идёт несколько часов",
  "Не понимаю где медленно — нужен общий обзор",
];

function formatAiError(e: unknown): string {
  if (e instanceof CloudError) {
    if (e.reason === "network") {
      return (
        "Сервер AI недоступен (localhost:8001 не отвечает). " +
        "Запустите сервер: cd server && .venv\\Scripts\\uvicorn.exe api.main:app --port 8001"
      );
    }
    const payload = e.payload as Record<string, unknown> | undefined;
    if (payload?.detail && typeof payload.detail === "object") {
      const det = payload.detail as Record<string, unknown>;
      if (det.error === "ai_not_configured") {
        return (
          "AI отключён: ANTHROPIC_API_KEY не задан в .env. " +
          "Добавьте ключ и перезапустите сервер."
        );
      }
    }
    return e.message;
  }
  return String(e);
}

export function AiWizardTab({ platformVersion, onApply }: Props) {
  const [description, setDescription] = useState("");
  const [dbms, setDbms] = useState<"mssql" | "postgres" | "both" | "unknown">(
    "unknown",
  );
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<AiLogcfgGenerateResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    const desc = description.trim();
    if (desc.length < 10) return;
    setStatus("loading");
    setErrorMsg(null);
    try {
      const resp = await cloud.aiGenerateLogcfg({
        problem_description: desc,
        platform_version: platformVersion ?? null,
        dbms,
      });
      setResult(resp);
      setStatus("done");
    } catch (e) {
      setErrorMsg(formatAiError(e));
      setStatus("error");
    }
  }, [description, dbms, platformVersion]);

  const handleApply = useCallback(() => {
    if (!result) return;
    // Маппим AiLogcfgConfigResult → LogcfgConfig (типы совместимы структурно)
    onApply(result.config as unknown as LogcfgConfig);
  }, [result, onApply]);

  return (
    <div className={styles.root}>
      <div className={styles.form}>
        <div className={styles.form_label}>Опишите проблему производительности</div>
        <textarea
          className={styles.textarea}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={
            "Например: пользователи жалуются на долгий запуск отчётов «Анализ субконто». " +
            "Иногда зависает на 30–60 секунд..."
          }
          rows={3}
          maxLength={2000}
        />
        {/* Примеры описаний — клик подставляет в textarea */}
        <div className={styles.examples}>
          <span className={styles.examples_label}>Примеры:</span>
          {EXAMPLE_PROMPTS.map((example) => (
            <button
              key={example}
              className={styles.example_chip}
              onClick={() => setDescription(example)}
              title={example}
            >
              {example}
            </button>
          ))}
        </div>
        <div className={styles.form_row}>
          <div className={styles.field_group}>
            <label className={styles.field_label} htmlFor="tj-ai-dbms">
              СУБД
            </label>
            <select
              id="tj-ai-dbms"
              className={styles.select}
              value={dbms}
              onChange={(e) =>
                setDbms(
                  e.target.value as "mssql" | "postgres" | "both" | "unknown",
                )
              }
            >
              <option value="unknown">Неизвестно</option>
              <option value="mssql">MS SQL Server</option>
              <option value="postgres">PostgreSQL</option>
              <option value="both">Обе СУБД</option>
            </select>
          </div>
          <button
            className={styles.btn_generate}
            onClick={handleGenerate}
            disabled={
              status === "loading" || description.trim().length < 10
            }
          >
            {status === "loading"
              ? "Генерация..."
              : "Сгенерировать настройку"}
          </button>
        </div>
      </div>

      {status === "loading" && (
        <div className={styles.loading}>
          <span className={styles.spinner} />
          AI анализирует описание…
        </div>
      )}

      {status === "error" && errorMsg && (
        <div className={styles.error}>{errorMsg}</div>
      )}

      {status === "done" && result && (
        <div className={styles.result}>
          {result.explanation && (
            <div className={styles.explanation}>{result.explanation}</div>
          )}

          {result.events_rationale.length > 0 && (
            <div className={styles.rationale}>
              {result.events_rationale.map((r) => (
                <div key={r.event} className={styles.rationale_row}>
                  <span className={styles.rationale_event}>{r.event}</span>
                  <span className={styles.rationale_threshold}>
                    {r.threshold}
                  </span>
                  <span className={styles.rationale_why}>{r.why}</span>
                </div>
              ))}
            </div>
          )}

          {result.warnings.length > 0 && (
            <div className={styles.warnings}>
              {result.warnings.map((w, i) => (
                <div key={i} className={styles.warning_item}>
                  ⚠&nbsp;{w}
                </div>
              ))}
            </div>
          )}

          {result.estimated_use_duration && (
            <div className={styles.duration_hint}>
              Рекомендуемое время сбора: {result.estimated_use_duration}
            </div>
          )}

          <button className={styles.btn_apply} onClick={handleApply}>
            Применить в конструкторе
          </button>
        </div>
      )}
    </div>
  );
}
