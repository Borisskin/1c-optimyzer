import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiDashboard, apiLicense } from "@/api/endpoints";

export function Overview() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => apiDashboard.summary(),
  });

  if (isLoading) return <div className="loader">Загружаем сводку…</div>;
  if (error || !data) return <div className="error-banner">Не удалось загрузить сводку</div>;

  const isPro = data.pro_active;
  return (
    <>
      <div className="page__head">
        <h1 className="page__title">
          Здравствуйте, {data.user.display_name || data.user.email}
        </h1>
        <p className="page__lead">
          Сводка по аккаунту на {new Date(data.server_time).toLocaleString("ru-RU")}
        </p>
      </div>

      <div className="grid-cards">
        <div className="metric">
          <div className="metric__label">Тариф</div>
          <div className="metric__value">
            <span className={`pill ${isPro ? "pill--pro" : "pill--free"}`}>
              {isPro ? "PRO" : "FREE"}
            </span>
          </div>
          <div className="metric__hint">
            {isPro
              ? `действует до ${new Date(data.subscription.ends_at).toLocaleDateString("ru-RU")}`
              : "5 AI-консультаций / мес"}
          </div>
        </div>
        <div className="metric">
          <div className="metric__label">AI-операций в этом месяце</div>
          <div className="metric__value">{data.ai_operations_this_month}</div>
          <div className="metric__hint">
            {isPro
              ? "без лимита (soft cap 1000)"
              : `${data.ai_operations_free_remaining} осталось бесплатно`}
          </div>
        </div>
        <div className="metric">
          <div className="metric__label">Кредитов</div>
          <div className="metric__value">{data.credits_remaining}</div>
          <div className="metric__hint">
            <Link to="/credits">Купить ещё →</Link>
          </div>
        </div>
      </div>

      <ActivationKeyCard />
      <DownloadCard />

      {!isPro && (
        <div className="card">
          <h2 className="card__title">Хотите безлимит AI-консультаций?</h2>
          <p style={{ margin: "0 0 12px", color: "var(--fg-2)" }}>
            Pro — 2 990 ₽/мес, отмена в любой момент.
          </p>
          <Link to="/subscription" className="btn btn--primary">
            Перейти на Pro
          </Link>
        </div>
      )}
    </>
  );
}

// Персональный ключ активации для desktop. Один ключ на user, постоянный.
// Auto-load при mount. Кнопка «Перегенерировать» отзывает старый и выдаёт новый.
function ActivationKeyCard() {
  const queryClient = useQueryClient();
  const keyQuery = useQuery({
    queryKey: ["license", "my-key"],
    queryFn: () => apiLicense.myKey(),
  });
  const regenerate = useMutation({
    mutationFn: () => apiLicense.regenerate(),
    onSuccess: (data) => {
      queryClient.setQueryData(["license", "my-key"], data);
    },
  });
  const [copied, setCopied] = useState(false);

  async function copyKey() {
    const key = keyQuery.data?.key;
    if (!key) return;
    try {
      await navigator.clipboard.writeText(key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // fallback — select all
    }
  }

  function onRegenerate() {
    if (window.confirm("Старый ключ перестанет работать. Устройства, активированные на нём, нужно будет переактивировать. Продолжить?")) {
      regenerate.mutate();
    }
  }

  return (
    <div className="card">
      <h2 className="card__title">Ваш ключ активации</h2>
      <p style={{ margin: "0 0 16px", color: "var(--fg-2)" }}>
        Скачайте Optimyzer (см. ниже), запустите, в Настройках вставьте этот
        ключ — приложение узнает вас и применит ваш тариф.
      </p>

      {keyQuery.isLoading && <div className="loader">Загружаем…</div>}

      {keyQuery.error && (
        <div className="error-banner">
          Не удалось загрузить ключ: {keyQuery.error.message}
        </div>
      )}

      {keyQuery.data && (
        <>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <code
              style={{
                flex: 1,
                fontFamily: "var(--font-mono)",
                fontSize: 16,
                padding: "12px 16px",
                background: "var(--bg-3, #f1f5f9)",
                borderRadius: "var(--r)",
                letterSpacing: "0.05em",
                userSelect: "all",
              }}
            >
              {keyQuery.data.key}
            </code>
            <button type="button" className="btn" onClick={copyKey}>
              {copied ? "Скопировано ✓" : "Скопировать"}
            </button>
          </div>
          <p style={{ marginTop: 12, fontSize: 13, color: "var(--fg-3)" }}>
            Ключ постоянный — работает на нескольких устройствах. Если хотите
            заменить (например при компрометации) —{" "}
            <button
              type="button"
              onClick={onRegenerate}
              disabled={regenerate.isPending}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--accent)",
                cursor: "pointer",
                padding: 0,
                textDecoration: "underline",
                fontSize: "inherit",
              }}
            >
              {regenerate.isPending ? "перегенерируем…" : "перегенерировать"}
            </button>
            .
          </p>
        </>
      )}
    </div>
  );
}

// Заглушка для скачивания desktop приложения. До первого Release
// показываем «скоро» вместо мёртвых ссылок.
function DownloadCard() {
  return (
    <div className="card">
      <h2 className="card__title">Скачать Optimyzer</h2>
      <p style={{ margin: "0 0 16px", color: "var(--fg-2)" }}>
        Desktop приложение для анализа архивов технологического журнала 1С.
        После установки введите свой ключ активации из истории платежей.
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <DownloadButton label="Windows" subtitle=".msi · скоро" />
        <DownloadButton label="macOS" subtitle=".dmg · скоро" />
        <DownloadButton label="Linux" subtitle=".AppImage · скоро" />
      </div>
      <p style={{ marginTop: 12, fontSize: 12, color: "var(--fg-3)" }}>
        Сборки появятся в первом релизе. Пока тестируем приватно у пилотных юзеров.
      </p>
    </div>
  );
}

function DownloadButton({ label, subtitle }: { label: string; subtitle: string }) {
  return (
    <button
      type="button"
      className="btn"
      disabled
      style={{
        flexDirection: "column",
        alignItems: "flex-start",
        padding: "10px 16px",
        gap: 2,
      }}
    >
      <span style={{ fontWeight: 700 }}>{label}</span>
      <span style={{ fontSize: 11, color: "var(--fg-3)", fontWeight: 500 }}>
        {subtitle}
      </span>
    </button>
  );
}
