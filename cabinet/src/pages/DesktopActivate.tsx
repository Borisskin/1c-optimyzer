import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiLicense } from "@/api/endpoints";

/**
 * Страница активации desktop приложения.
 *
 * Юзер попадает сюда автоматически после OAuth login (если открыл cabinet из
 * desktop'а через `/login?from=desktop`). Cabinet генерирует одноразовый
 * activation key через /v1/license/issue-for-cabinet и предлагает два пути:
 *
 *   1. **Deep link** (primary) — кнопка «Открыть в Optimyzer» открывает
 *      `optimyzer://activate?key=OPTM-XXXX-...`. Tauri ловит deep link,
 *      активирует desktop без копи-паста.
 *   2. **Manual copy** (fallback) — поле с ключом + кнопка «Скопировать».
 *      Юзер вставляет в desktop Settings → «Введите ключ активации».
 */
export function DesktopActivate() {
  const issue = useMutation({ mutationFn: () => apiLicense.issueForCabinet() });
  const [copied, setCopied] = useState(false);

  // Автоматически выпускаем ключ при первом mount'е.
  useEffect(() => {
    if (!issue.data && !issue.isPending && !issue.error) {
      issue.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function copyKey() {
    if (!issue.data?.key) return;
    try {
      await navigator.clipboard.writeText(issue.data.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // fallback: select text
    }
  }

  return (
    <>
      <div className="page__head">
        <h1 className="page__title">Активация desktop приложения</h1>
        <p className="page__lead">
          Один ключ = одно устройство. Free даёт 5 AI-объяснений в месяц на ваш
          аккаунт.
        </p>
      </div>

      {issue.isPending && (
        <div className="card">
          <div className="loader">Генерируем ключ…</div>
        </div>
      )}

      {issue.error && (
        <div className="error-banner">
          Не удалось получить ключ: {issue.error.message}
        </div>
      )}

      {issue.data && (
        <>
          <div className="card">
            <h2 className="card__title">Способ 1 — открыть в Optimyzer (рекомендуем)</h2>
            <p style={{ color: "var(--fg-2)", marginTop: 0 }}>
              Откройте Optimyzer на этом компьютере прямо отсюда. Сработает
              если desktop приложение установлено.
            </p>
            <a
              href={issue.data.deep_link}
              className="btn btn--primary"
              style={{ fontSize: 15 }}
            >
              Открыть в Optimyzer
            </a>
          </div>

          <div className="card">
            <h2 className="card__title">Способ 2 — скопировать ключ вручную</h2>
            <p style={{ color: "var(--fg-2)", marginTop: 0 }}>
              Откройте Optimyzer → Настройки → Аккаунт → «Введите ключ активации».
              Вставьте этот ключ:
            </p>
            <div
              style={{
                display: "flex",
                gap: 8,
                alignItems: "center",
                marginTop: 12,
              }}
            >
              <code
                style={{
                  flex: 1,
                  fontFamily: "var(--font-mono)",
                  fontSize: 16,
                  padding: "12px 16px",
                  background: "var(--bg-3)",
                  borderRadius: "var(--r)",
                  letterSpacing: "0.05em",
                  userSelect: "all",
                }}
              >
                {issue.data.key}
              </code>
              <button
                type="button"
                className="btn"
                onClick={copyKey}
              >
                {copied ? "Скопировано ✓" : "Скопировать"}
              </button>
            </div>
            <p style={{ color: "var(--fg-3)", fontSize: 12, marginTop: 8 }}>
              Ключ одноразовый и привязывается к вашему компьютеру после активации.
              Если потеряли — нажмите{" "}
              <button
                type="button"
                onClick={() => issue.mutate()}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--accent)",
                  cursor: "pointer",
                  padding: 0,
                  textDecoration: "underline",
                }}
              >
                сгенерировать новый
              </button>
              .
            </p>
          </div>
        </>
      )}
    </>
  );
}
