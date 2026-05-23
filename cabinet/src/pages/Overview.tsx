import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiDashboard } from "@/api/endpoints";

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
              : "5 AI-объяснений / мес"}
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
        <div className="metric">
          <div className="metric__label">Устройств</div>
          <div className="metric__value">
            {data.devices_active}
            <span style={{ fontSize: 14, color: "var(--fg-3)", marginLeft: 4 }}>
              / {data.devices_limit}
            </span>
          </div>
          <div className="metric__hint">
            <Link to="/devices">Управление →</Link>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="card__title">Подсказка</h2>
        <p style={{ margin: 0, color: "var(--fg-2)" }}>
          {isPro
            ? "Вы на тарифе Pro — все функции AI Explainer'а доступны без ограничений. Скачайте Optimyzer с лендинга и используйте ключ активации из истории платежей."
            : "Хотите безлимит AI-объяснений? Перейдите на Pro — 2 990 ₽/мес, отмена в любой момент."}
        </p>
        {!isPro && (
          <div style={{ marginTop: 12 }}>
            <Link to="/subscription" className="btn btn--primary">
              Перейти на Pro
            </Link>
          </div>
        )}
      </div>
    </>
  );
}
