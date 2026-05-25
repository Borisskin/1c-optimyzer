/**
 * Sprint 7 Phase A — главный экран Plan Analyzer.
 *
 * Flow:
 *   1. PlanImport → юзер выбирает .sqlplan файл или вставляет XML
 *   2. backend.planAnalyzerAnalyzeFile/Xml → PerformanceStudio CLI
 *   3. Render: PlanStats + PlanWarnings + MissingIndexes per statement
 *
 * Phase B добавит PlanVisualization (html-query-plan SSMS-style).
 * Phase C добавит AiPlanExplanationCard поверх warnings (Claude Sonnet 4.5).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  backend,
  type PlanAnalysisResult,
  type PlanAnalyzeResponse,
  type PlanAnalyzerStatus,
  type PlanEngine as BackendPlanEngine,
  type SqlAntipatternFinding,
} from "@/api/backend";
import { cloud, CloudError, type AiExplainPlanResponse } from "@/api/cloud";
import { t, format } from "@/i18n/ru";
import { Icon } from "@/components/icons/Icon";
import { useAppStore } from "@/store/appStore";
import { PlanImport } from "./PlanImport";
import { PlanWarnings } from "./PlanWarnings";
import { MissingIndexes } from "./MissingIndexes";
import { PlanStats } from "./PlanStats";
import { PlanVisualization } from "./PlanVisualization";
import { AiPlanExplanationCard } from "./AiPlanExplanationCard";
import { PlanTextView } from "./PlanTextView";
import { PgPlanTextView } from "./views/PgPlanTextView";
import { Pev2PlanVisualization } from "./views/Pev2PlanVisualization";
import { detectPlanEngine, type PlanEngine } from "./utils/detectPlanEngine";
import { SqlAntipatternsCard } from "./SqlAntipatternsCard";
import styles from "./PlanAnalyzer.module.css";

// Sprint 7 Phase D + Sprint 8 Phase B — text-format plan import payload
// (из tab «Из архива ТЖ»). engine приходит из RPC (DBMSSQL → mssql, DBPOSTGRS → postgres).
interface TjPlanPayload {
  event_id: number;
  sql_text: string;
  plan_text: string;
  ts: string | null;
  duration_us: number | null;
  context: string | null;
  engine?: PlanEngine | null;
}

// Внутренний state для text-format пути (отдельно от result/planXmlForViz).
// Sprint 8 Phase B — добавлено поле engine для dispatcher PG vs MSSQL view.
interface TextPlanState {
  text: string;
  sql_text: string;
  source_label: string;
  // "mssql" → PlanTextView (Sprint 7), "postgres" → PgPlanTextView (Sprint 8 B.2).
  // "unknown" — fallback на PlanTextView с уведомлением.
  engine: PlanEngine | "unknown";
  meta: {
    ts: string | null;
    duration_us: number | null;
    context: string | null;
  };
}

/**
 * Распознаёт типичные сценарии и даёт читаемое сообщение вместо
 * raw "Failed to fetch" или JSON.stringify(detail). Используется в UI поверх
 * AiPlanExplanationCard (errorBox).
 */
function formatAiError(e: unknown): string {
  if (e instanceof CloudError) {
    // Server вернул 503 с {detail: {error: "ai_not_configured"}}.
    const payload = e.payload;
    if (
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof (payload as { detail: unknown }).detail === "object"
    ) {
      const det = (payload as { detail: Record<string, unknown> }).detail;
      if (det && det.error === "ai_not_configured") {
        return (
          "AI отключён: ANTHROPIC_API_KEY не задан в .env. " +
          "Добавьте ключ и перезапустите сервер."
        );
      }
    }
    if (e.reason === "network") {
      return (
        "Сервер AI недоступен (localhost:8001 не отвечает). " +
        "Запустите сервер: cd server && .venv\\Scripts\\uvicorn.exe api.main:app --port 8001"
      );
    }
    return e.message;
  }
  return String(e);
}

export function PlanAnalyzerScreen() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlanAnalysisResult | null>(null);
  const [sourceLabel, setSourceLabel] = useState<string | null>(null);
  const [status, setStatus] = useState<PlanAnalyzerStatus | null>(null);
  const [planXmlForViz, setPlanXmlForViz] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<AiExplainPlanResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  // Sprint 7 Phase D — отдельный state для text format (из ТЖ архива).
  // result/planXmlForViz используются для XML path. Они взаимоисключающие:
  // если textPlan != null → render text view, иначе → render XML viz+stats.
  const [textPlan, setTextPlan] = useState<TextPlanState | null>(null);
  // Sprint 8 Phase B.4/B.5 — есть ли в Settings хотя бы одно PG connection?
  // Используется для показа кнопки «Получить интерактивный план» в PgPlanTextView.
  const [hasPgConnection, setHasPgConnection] = useState<boolean>(false);
  // Sprint 8 Phase B.5 — результат re-EXPLAIN (JSON план) для текущего textPlan.
  // Когда заполнен — рендерится Pev2PlanVisualization вместо PgPlanTextView.
  const [pev2PlanJson, setPev2PlanJson] = useState<string | null>(null);
  const [reExplainLoading, setReExplainLoading] = useState(false);
  const [reExplainError, setReExplainError] = useState<string | null>(null);
  // Sprint 8 Phase C — SQL antipatterns. Запускаются параллельно с AI explain
  // когда у нас есть sql_text + engine. Локальный sqlglot parser — быстро (<100ms).
  const [antipatterns, setAntipatterns] = useState<SqlAntipatternFinding[] | null>(
    null,
  );
  // SQL секция в textPlan — collapsed по умолчанию. Сбрасывается при каждом
  // новом плане из ТЖ (через setSqlTextOpen(false) в onPickTjPlan).
  const [sqlTextOpen, setSqlTextOpen] = useState(false);
  const [antipatternsLoading, setAntipatternsLoading] = useState(false);
  const [antipatternsError, setAntipatternsError] = useState<string | null>(null);
  const [antipatternsEngine, setAntipatternsEngine] = useState<BackendPlanEngine | null>(
    null,
  );
  const [is1cContext, setIs1cContext] = useState(false);
  const pushToast = useAppStore((s) => s.pushToast);

  // Sprint 7 Phase D fix — scroll to result после клика по плану из ТЖ.
  // Список планов длинный (200 rows), без scroll юзер не видит что плана
  // импортировался — выглядит как «ничего не происходит».
  const resultAreaRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (textPlan && resultAreaRef.current) {
      resultAreaRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [textPlan]);
  useEffect(() => {
    if (result && resultAreaRef.current) {
      resultAreaRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  // Status check — на mount узнаём доступен ли planview.exe.
  useEffect(() => {
    backend
      .planAnalyzerStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  // Sprint 8 Phase B.4 — на mount проверяем есть ли PG connections в Settings.
  // Используем длину списка как простой флаг (default connection или нет
  // не имеет значения здесь — UI любому даст возможность re-EXPLAIN).
  useEffect(() => {
    backend
      .pgListConnections()
      .then((resp) => {
        if (resp.ok && (resp.items?.length ?? 0) > 0) {
          setHasPgConnection(true);
        } else {
          setHasPgConnection(false);
        }
      })
      .catch(() => setHasPgConnection(false));
  }, []);

  // Sprint 8 Phase C — параллельный запуск SQL antipatterns detection.
  // Локальный sqlglot parser → быстро (<100ms на типичный запрос).
  // Вызывается из обоих handler'ов: XML path и text path.
  const runAntipatterns = useCallback(
    async (sql: string, engine: BackendPlanEngine) => {
      if (!sql || !sql.trim()) {
        setAntipatterns(null);
        setAntipatternsEngine(null);
        setIs1cContext(false);
        return;
      }
      setAntipatternsLoading(true);
      setAntipatternsError(null);
      setAntipatternsEngine(engine);
      try {
        const resp = await backend.sqlAntipatternsDetect(sql, engine);
        if (!resp.ok) {
          setAntipatternsError(resp.error ?? "Неизвестная ошибка");
          setAntipatterns([]);
          return;
        }
        setAntipatterns(resp.findings ?? []);
        setIs1cContext(Boolean(resp.is_1c_context));
      } catch (e) {
        setAntipatternsError(String(e));
        setAntipatterns([]);
      } finally {
        setAntipatternsLoading(false);
      }
    },
    [],
  );

  const requestAiExplanation = useCallback(
    async (planResult: PlanAnalysisResult, planXml: string) => {
      // AI explain работает только если есть оба: plan XML + хотя бы один statement.
      const firstStmt = planResult.statements[0];
      if (!firstStmt) return;
      setAiLoading(true);
      setAiError(null);
      setAiResponse(null);
      try {
        const allWarnings = planResult.statements.flatMap((s) => s.warnings);
        const allMissing = planResult.statements.flatMap((s) => s.missing_indexes);
        const resp = await cloud.aiExplainPlan({
          sql_text: firstStmt.statement_text,
          plan_xml: planXml,
          plan_format: "xml",
          planview_warnings: allWarnings,
          missing_indexes: allMissing,
          plan_summary: planResult.summary as unknown as Record<string, unknown>,
          // Sprint 8 Phase C — передаём antipatterns в AI context (если уже найдены).
          detected_antipatterns: antipatterns
            ? antipatterns.map((f) => ({ ...f }))
            : [],
        });
        setAiResponse(resp);
      } catch (e) {
        setAiError(formatAiError(e));
      } finally {
        setAiLoading(false);
      }
    },
    [antipatterns],
  );

  // Sprint 7 Phase D + Sprint 8 Phase B — AI explanation для text-format плана.
  // Отличается от requestAiExplanation тем что нет PerformanceStudio warnings
  // и нет missing_indexes (CLI на text не работает). Передаём только SQL + text.
  // Sprint 8 Phase B: engine передаётся в request — сервер выбирает правильный
  // prompt (MSSQL terminology vs PG terminology + 1С-specific knowledge).
  const requestAiExplanationText = useCallback(
    async (state: TextPlanState) => {
      setAiLoading(true);
      setAiError(null);
      setAiResponse(null);
      try {
        // engine="unknown" → fallback на mssql (legacy default).
        const aiEngine: "mssql" | "postgres" =
          state.engine === "postgres" ? "postgres" : "mssql";
        const resp = await cloud.aiExplainPlan({
          sql_text: state.sql_text,
          plan_xml: state.text,
          plan_format: "text",
          engine: aiEngine,
          planview_warnings: [],
          missing_indexes: [],
          plan_summary: null,
          // Sprint 8 Phase C — передаём antipatterns (особенно важно для PG).
          detected_antipatterns: antipatterns
            ? antipatterns.map((f) => ({ ...f }))
            : [],
        });
        setAiResponse(resp);
      } catch (e) {
        setAiError(formatAiError(e));
      } finally {
        setAiLoading(false);
      }
    },
    [antipatterns],
  );

  const handleResponse = useCallback(
    (resp: PlanAnalyzeResponse, source: string, sourceXml: string | null) => {
      if (!resp.ok || !resp.result) {
        const msg = resp.details ?? resp.error ?? "unknown error";
        setError(format(t.planAnalyzer.analysisFailed, { detail: msg }));
        setResult(null);
        setAiResponse(null);
        setAiError(null);
        return;
      }
      setError(null);
      setResult(resp.result);
      setSourceLabel(source);
      setPlanXmlForViz(sourceXml);
      // Sprint 7 Phase D — переключаемся в XML-режим, гасим textPlan если был
      // (например предыдущий импорт был из ТЖ, а сейчас юзер залил .sqlplan).
      setTextPlan(null);
      // Сбрасываем AI-state предыдущего плана — иначе stale-card висит
      // поверх нового результата. Этот reset работает и при переключении
      // табов «Импорт файла» ↔ «Вставить XML», и при последовательных
      // импортах в одном табе.
      setAiResponse(null);
      setAiError(null);
      setAiLoading(false);
      // Sprint 8 Phase C — параллельно запускаем antipatterns detection
      // (быстро, локально). XML path = всегда MSSQL.
      const firstStmt = resp.result.statements[0];
      if (firstStmt?.statement_text) {
        void runAntipatterns(firstStmt.statement_text, "mssql");
      } else {
        setAntipatterns(null);
        setAntipatternsEngine(null);
        setIs1cContext(false);
      }
      // AI больше не запускаем автоматически — пользователь жмёт кнопку
      // в AiPlanExplanationCard (экономия квоты и токенов).
    },
    [runAntipatterns],
  );

  // Sprint 7 Phase D + Sprint 8 Phase B — handler для tab «Из архива ТЖ».
  // Text format не идёт через PerformanceStudio CLI (XSLT не поддерживает
  // text), поэтому result/planXmlForViz сбрасываем и работаем через textPlan
  // state + PlanTextView/PgPlanTextView + AI (без warnings/missing_indexes).
  // engine определяется так: сначала смотрим явный payload.engine из RPC
  // (DBMSSQL → mssql, DBPOSTGRS → postgres), если его нет — fallback на
  // эвристику detectPlanEngine по содержимому плана.
  const onPickTjPlan = useCallback(
    (payload: TjPlanPayload) => {
      const sourceLbl = `ТЖ архив · event #${payload.event_id}`;
      // engine: явный из RPC > эвристика > "unknown"
      let engine: PlanEngine | "unknown";
      if (payload.engine === "postgres") {
        engine = "postgres";
      } else if (payload.engine === "mssql") {
        engine = "mssql";
      } else {
        const det = detectPlanEngine(payload.plan_text);
        engine = det.engine === "unknown" ? "unknown" : det.engine;
      }
      setError(null);
      setResult(null);
      setPlanXmlForViz(null);
      setSourceLabel(sourceLbl);
      setTextPlan({
        text: payload.plan_text,
        sql_text: payload.sql_text,
        source_label: sourceLbl,
        engine,
        meta: {
          ts: payload.ts,
          duration_us: payload.duration_us,
          context: payload.context,
        },
      });
      // Sprint 8 Phase B.5 — сброс pev2 state при смене плана.
      setPev2PlanJson(null);
      setReExplainError(null);
      setReExplainLoading(false);
      // Сбрасываем collapse-state SQL секции — каждый новый план начинает
      // с закрытой секцией (договорились: все подобные области collapsed).
      setSqlTextOpen(false);
      setAiResponse(null);
      setAiError(null);
      setAiLoading(false);
      // Sprint 8 Phase C — antipatterns. engine="unknown" → skip (нет смысла
      // парсить если мы не знаем диалект).
      if (engine !== "unknown" && payload.sql_text) {
        void runAntipatterns(payload.sql_text, engine);
      } else {
        setAntipatterns(null);
        setAntipatternsEngine(null);
        setIs1cContext(false);
      }
      const engineLabel =
        engine === "postgres" ? "PostgreSQL" : engine === "mssql" ? "MS SQL" : "неизв. движок";
      pushToast(
        `Импортирован план из ТЖ (event #${payload.event_id}, ${engineLabel})`,
        "info",
      );
    },
    [pushToast],
  );

  // Sprint 8 Phase B.5 — callback для PG re-EXPLAIN. Когда юзер кликает
  // «Получить интерактивный план» в PgPlanTextView, мы:
  //   1. Берём sql_text из textPlan
  //   2. Делаем backend.planAnalyzerReExplain (использует default PG connection)
  //   3. Если успешно → сохраняем JSON план в pev2PlanJson → dispatcher
  //      переключается на Pev2PlanVisualization
  const requestReExplain = useCallback(async () => {
    if (!textPlan || !textPlan.sql_text) {
      setReExplainError("Нет SQL запроса для re-EXPLAIN");
      return;
    }
    setReExplainLoading(true);
    setReExplainError(null);
    try {
      const resp = await backend.planAnalyzerReExplain(textPlan.sql_text);
      if (!resp.ok) {
        // Развёрнутое сообщение для частых случаев.
        if (resp.error === "no_default_connection") {
          setReExplainError(
            "Не настроено PG подключение. Откройте Настройки → PostgreSQL → Добавить.",
          );
        } else if (resp.error === "unsafe_query") {
          setReExplainError(
            "SQL не безопасен для re-EXPLAIN (не SELECT/WITH). " +
              "Интерактивный план доступен только для read-only запросов.",
          );
        } else {
          setReExplainError(resp.details ?? resp.error ?? "Неизвестная ошибка");
        }
        return;
      }
      if (resp.plan_json) {
        setPev2PlanJson(resp.plan_json);
        pushToast("Получен интерактивный план через PG re-EXPLAIN", "info");
      } else {
        setReExplainError("Backend вернул пустой план");
      }
    } catch (e) {
      setReExplainError(String(e));
    } finally {
      setReExplainLoading(false);
    }
  }, [textPlan, pushToast, runAntipatterns]);

  // Колбек для idle-кнопки в AiPlanExplanationCard.
  // Sprint 7 Phase D — distinguishing XML vs text path.
  const onRequestAi = useCallback(() => {
    if (aiLoading || aiResponse) return;
    if (textPlan) {
      void requestAiExplanationText(textPlan);
      return;
    }
    if (result && planXmlForViz) {
      void requestAiExplanation(result, planXmlForViz);
    }
  }, [
    result,
    planXmlForViz,
    textPlan,
    aiLoading,
    aiResponse,
    requestAiExplanation,
    requestAiExplanationText,
  ]);

  // Сброс состояния при смене таба — чтобы не показывался старый результат
  // из предыдущего таба (например MSSQL .sqlplan под списком ТЖ).
  const onTabChange = useCallback((tab: "file" | "paste" | "tj") => {
    if (tab === "tj") {
      // Переходим в ТЖ — сбрасываем XML-результат
      setResult(null);
      setPlanXmlForViz(null);
      setSourceLabel(null);
      setAiResponse(null);
      setAiError(null);
      setAiLoading(false);
      setAntipatterns(null);
      setAntipatternsEngine(null);
      setIs1cContext(false);
    } else {
      // Переходим в file/paste — сбрасываем ТЖ-результат
      setTextPlan(null);
      setPev2PlanJson(null);
      setAiResponse(null);
      setAiError(null);
      setAiLoading(false);
      setAntipatterns(null);
      setAntipatternsEngine(null);
      setIs1cContext(false);
    }
  }, []);

  const onPickFile = useCallback(
    async (filePath: string) => {
      setBusy(true);
      setError(null);
      try {
        // Параллельно: backend analyze + tauri read file.
        // analyze идёт через PerformanceStudio (warnings + missing_indexes),
        // raw XML нужен для html-query-plan visualization (Phase B).
        // read_plan_text_file — custom Tauri command в main.rs (Phase B).
        const [resp, rawXml] = await Promise.all([
          backend.planAnalyzerAnalyzeFile(filePath),
          invoke<string>("read_plan_text_file", { path: filePath }).catch(() => null),
        ]);
        const name = filePath.split(/[\\/]/).pop() ?? filePath;
        handleResponse(resp, name, rawXml);
        pushToast(format(t.planAnalyzer.fileImportToast, { name }), "info");
      } catch (e) {
        setError(format(t.planAnalyzer.analysisFailed, { detail: String(e) }));
      } finally {
        setBusy(false);
      }
    },
    [handleResponse, pushToast],
  );

  const onPasteXml = useCallback(
    async (xml: string) => {
      setBusy(true);
      setError(null);
      try {
        const resp = await backend.planAnalyzerAnalyzeXml(xml);
        handleResponse(resp, "pasted XML", xml);
        pushToast(format(t.planAnalyzer.pasteImportToast, { size: xml.length }), "info");
      } catch (e) {
        setError(format(t.planAnalyzer.analysisFailed, { detail: String(e) }));
      } finally {
        setBusy(false);
      }
    },
    [handleResponse, pushToast],
  );

  const summary = result?.summary;
  const binaryUnavailable = status !== null && !status.available;

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <div className={styles.titleBlock}>
          <h1 className={styles.title}>{t.planAnalyzer.pageTitle}</h1>
          <div className={styles.subtitle}>{t.planAnalyzer.description}</div>
        </div>
        {status && (
          <div className={styles.statusBlock}>
            <div>
              <span
                className={
                  status.available ? styles.statusAvailable : styles.statusUnavailable
                }
              >
                {status.available ? "● PerformanceStudio готов" : "○ planview.exe нет"}
              </span>
            </div>
            <div>{status.rules_count} правил · v1.11.2</div>
          </div>
        )}
      </div>

      {binaryUnavailable && (
        <div className={styles.binaryMissingBanner}>
          <div className={styles.binaryMissingTitle}>
            {t.planAnalyzer.binaryMissingTitle}
          </div>
          <div>{t.planAnalyzer.binaryMissingDetail}</div>
        </div>
      )}

      <div className={styles.body}>
        <PlanImport
          onPickFile={onPickFile}
          onPasteXml={onPasteXml}
          onPickTjPlan={onPickTjPlan}
          onTabChange={onTabChange}
          busy={busy}
        />

        {error && <div className={styles.error}>{error}</div>}

        {/* Sprint 7 Phase D + Sprint 8 Phase B — text-format plan path (импорт из ТЖ архива).
            Не имеет PerformanceStudio analysis (CLI не работает на text),
            визуализации XSLT тоже нет, warnings/missing_indexes — пустые.
            Dispatcher по engine:
              postgres → PgPlanTextView (Sprint 8 Phase B.2)
              mssql / unknown → PlanTextView (Sprint 7 Phase D) */}
        {textPlan && (
          <div className={styles.resultArea} ref={resultAreaRef}>
            <AiPlanExplanationCard
              response={aiResponse}
              loading={aiLoading}
              error={aiError}
              showIdleButton
              onRequest={onRequestAi}
            />

            {/* Sprint 8 Phase C — antipatterns (fast, local sqlglot) */}
            <SqlAntipatternsCard
              findings={antipatterns}
              loading={antipatternsLoading}
              error={antipatternsError}
              engine={antipatternsEngine}
              is1cContext={is1cContext}
            />

            {textPlan.engine === "postgres" ? (
              <>
                {/* Sprint 8 Phase B.5 — если уже получен JSON план — рендерим pev2.
                    Иначе показываем TEXT view с кнопкой «Получить интерактивный план». */}
                {pev2PlanJson ? (
                  <Pev2PlanVisualization
                    planJson={pev2PlanJson}
                    planQuery={textPlan.sql_text}
                  />
                ) : (
                  <PgPlanTextView
                    planText={textPlan.text}
                    meta={textPlan.meta}
                    onRequestInteractive={requestReExplain}
                    isInteractiveAvailable={hasPgConnection}
                  />
                )}
                {/* Sprint 8 Phase B.5 — показываем ошибку re-EXPLAIN если есть. */}
                {reExplainError && (
                  <div className={styles.error}>
                    Не удалось получить интерактивный план: {reExplainError}
                  </div>
                )}
                {reExplainLoading && (
                  <div className={styles.error}>
                    Выполняется re-EXPLAIN через PG connection...
                  </div>
                )}
                {/* Toggle для переключения обратно с pev2 на TEXT view. */}
                {pev2PlanJson && (
                  <div style={{ textAlign: "right" }}>
                    <button
                      type="button"
                      onClick={() => setPev2PlanJson(null)}
                      style={{
                        padding: "4px 10px",
                        background: "transparent",
                        border: "1px solid var(--o-border-2)",
                        borderRadius: 4,
                        color: "var(--o-text-2)",
                        fontSize: 11,
                        cursor: "pointer",
                      }}
                    >
                      ← Вернуться к текстовому плану
                    </button>
                  </div>
                )}
              </>
            ) : (
              <PlanTextView planText={textPlan.text} meta={textPlan.meta} />
            )}

            {textPlan.sql_text && (
              <div className={styles.statementCard}>
                <div
                  className={`${styles.statementHeader} ${styles.statementHeaderCollapsible}`}
                  onClick={() => setSqlTextOpen((v) => !v)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSqlTextOpen((v) => !v);
                    }
                  }}
                >
                  <span className={styles.statementLabel}>
                    SQL запроса · {textPlan.source_label}
                  </span>
                  <span className={styles.collapseHint}>
                    {sqlTextOpen ? "скрыть" : "показать"}
                  </span>
                </div>
                {sqlTextOpen && (
                  <pre className={styles.statementTextBlock}>{textPlan.sql_text}</pre>
                )}
              </div>
            )}
          </div>
        )}

        {!textPlan && result && summary && (
          <div className={styles.resultArea} ref={resultAreaRef}>
            {/* AI explanation — idle с кнопкой пока юзер не запросил */}
            {planXmlForViz && (
              <AiPlanExplanationCard
                response={aiResponse}
                loading={aiLoading}
                error={aiError}
                showIdleButton
                onRequest={onRequestAi}
              />
            )}

            {/* Sprint 8 Phase C — antipatterns (fast, local sqlglot) */}
            <SqlAntipatternsCard
              findings={antipatterns}
              loading={antipatternsLoading}
              error={antipatternsError}
              engine={antipatternsEngine}
              is1cContext={is1cContext}
            />

            {/* Phase B: SSMS-style visualization (html-query-plan) */}
            {planXmlForViz && <PlanVisualization planXml={planXmlForViz} />}

            <div className={styles.resultHeader}>
              <div className={styles.resultMeta}>
                <div className={styles.resultMetaLabel}>{t.planAnalyzer.sourceLabel}</div>
                <div className={styles.resultMetaValue}>
                  {sourceLabel ?? result.plan_source}
                </div>
              </div>
              {result.sql_server_version && (
                <div className={styles.resultMeta}>
                  <div className={styles.resultMetaLabel}>
                    {t.planAnalyzer.sqlServerVersionLabel}
                  </div>
                  <div className={styles.resultMetaValue}>
                    v{result.sql_server_version}
                    {result.sql_server_build ? ` build ${result.sql_server_build}` : ""}
                  </div>
                </div>
              )}
              <div className={styles.resultMeta}>
                <div className={styles.resultMetaLabel}>
                  {t.planAnalyzer.statementsLabel}
                </div>
                <div className={styles.resultMetaValue}>{summary.total_statements}</div>
              </div>
              <div className={styles.resultMeta}>
                <div className={styles.resultMetaLabel}>Сводка</div>
                <div className={styles.sevSummary}>
                  {summary.critical_warnings > 0 && (
                    <span className={`${styles.sevChip} ${styles.sevChipCritical}`}>
                      {summary.critical_warnings} критичных
                    </span>
                  )}
                  {summary.total_warnings - summary.critical_warnings > 0 && (
                    <span className={`${styles.sevChip} ${styles.sevChipWarning}`}>
                      {summary.total_warnings - summary.critical_warnings} предупр.
                    </span>
                  )}
                  {summary.missing_indexes > 0 && (
                    <span className={`${styles.sevChip} ${styles.sevChipInfo}`}>
                      {summary.missing_indexes} индексов
                    </span>
                  )}
                  {summary.total_warnings === 0 && summary.missing_indexes === 0 && (
                    <span className={`${styles.sevChip} ${styles.sevChipOK}`}>
                      Без проблем
                    </span>
                  )}
                </div>
              </div>
            </div>

            {result.statements.map((stmt, idx) => (
              <div key={idx} className={styles.statementCard}>
                <div className={styles.statementHeader}>
                  <span className={styles.statementLabel}>
                    {t.planAnalyzer.statementCardLabel} #{idx + 1} · {stmt.statement_type}
                  </span>
                </div>
                <pre className={styles.statementTextBlock}>{stmt.statement_text}</pre>
                <PlanStats statement={stmt} />
                <PlanWarnings warnings={stmt.warnings} />
                <MissingIndexes indexes={stmt.missing_indexes} />
              </div>
            ))}
          </div>
        )}

        {/* Empty state скрывается когда уже есть импортированный план в любом виде:
            - textPlan (text-формат из ТЖ) — иначе после клика по строке списка
              виден импортированный план ВВЕРХУ + дублирующая «Импортируйте план»
              ВНИЗУ → юзер думает что ничего не произошло
            - result (XML-формат от PerformanceStudio) — то же поведение */}
        {!result && !textPlan && !error && !busy && (
          <div className={styles.empty}>
            <div className={styles.emptyIcon}>
              <Icon name="FileBarChart" size={28} color="var(--o-text-mute)" />
            </div>
            <div className={styles.emptyTitle}>Импортируйте план запроса</div>
            <div className={styles.emptyHint}>
              .sqlplan файл из SSMS или XML вставкой → получите анализ за секунды
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
