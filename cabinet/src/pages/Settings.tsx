import { useQuery } from "@tanstack/react-query";
import { apiAuth } from "@/api/endpoints";

export function Settings() {
  const me = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => apiAuth.me(),
  });

  return (
    <>
      <div className="page__head">
        <h1 className="page__title">Настройки</h1>
        <p className="page__lead">Профиль и уведомления.</p>
      </div>

      <div className="card">
        <h2 className="card__title">Профиль</h2>
        {me.data?.user ? (
          <dl className="dl-grid">
            <dt>Email</dt>
            <dd>{me.data.user.email}</dd>
            <dt>Имя</dt>
            <dd>{me.data.user.display_name || "—"}</dd>
            <dt>Последний вход</dt>
            <dd>
              {me.data.user.last_login_at
                ? new Date(me.data.user.last_login_at).toLocaleString("ru-RU")
                : "—"}
            </dd>
          </dl>
        ) : (
          <div className="loader">Загружаем…</div>
        )}
      </div>

      <div className="card">
        <h2 className="card__title">Уведомления</h2>
        <p style={{ color: "var(--fg-2)" }}>
          Email-уведомления о платежах включены по умолчанию (чеки 54-ФЗ). Дополнительные
          уведомления о смене статуса подписки — в работе.
        </p>
        <p style={{ color: "var(--fg-3)", fontSize: 13 }}>
          Telegram-бот для быстрой поддержки — скоро.
        </p>
      </div>

      <div className="card">
        <h2 className="card__title">Поддержка</h2>
        <p style={{ color: "var(--fg-2)" }}>
          Вопросы — <a href="mailto:support@optimyzer.pro">support@optimyzer.pro</a> (приоритет
          для Pro юзеров).
        </p>
      </div>
    </>
  );
}
