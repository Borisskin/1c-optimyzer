import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiSubscriptions } from "@/api/endpoints";

export function Subscription() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["subscriptions", "current"],
    queryFn: () => apiSubscriptions.current(),
  });

  const cancel = useMutation({
    mutationFn: () => apiSubscriptions.cancel(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  });
  const reactivate = useMutation({
    mutationFn: () => apiSubscriptions.reactivate(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  });
  const purchase = useMutation({
    mutationFn: () => apiSubscriptions.purchase(),
    onSuccess: (resp) => {
      if (resp.confirmation_url) {
        window.location.assign(resp.confirmation_url);
      }
    },
  });

  if (isLoading) return <div className="loader">Загружаем подписку…</div>;
  if (error || !data) return <div className="error-banner">Не удалось загрузить подписку</div>;

  const sub = data.subscription;
  const isPro = sub.plan === "pro";
  const endsAt = new Date(sub.ends_at).toLocaleDateString("ru-RU");

  return (
    <>
      <div className="page__head">
        <h1 className="page__title">Подписка</h1>
        <p className="page__lead">
          {isPro ? "Тариф Pro · безлимит AI-объяснений" : "Тариф Free · 5 AI-объяснений в месяц"}
        </p>
      </div>

      <div className="card">
        <h2 className="card__title">Текущий тариф</h2>
        <dl className="dl-grid">
          <dt>Тариф</dt>
          <dd>
            <span className={`pill ${isPro ? "pill--pro" : "pill--free"}`}>
              {isPro ? "PRO" : "FREE"}
            </span>
          </dd>
          <dt>Статус</dt>
          <dd>{statusLabel(sub.status)}</dd>
          {isPro && (
            <>
              <dt>Активна до</dt>
              <dd>{endsAt}</dd>
              <dt>Цена</dt>
              <dd>{(sub.price_locked_kopecks / 100).toLocaleString("ru-RU")} ₽/мес</dd>
              <dt>Авто-продление</dt>
              <dd>{sub.auto_renew ? "включено" : "отключено"}</dd>
            </>
          )}
        </dl>

        <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
          {!isPro && (
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => purchase.mutate()}
              disabled={purchase.isPending}
            >
              {purchase.isPending ? "Создаём платёж…" : "Перейти на Pro · 2 990 ₽/мес"}
            </button>
          )}
          {isPro && sub.auto_renew && (
            <button
              type="button"
              className="btn btn--danger"
              onClick={() => cancel.mutate()}
              disabled={cancel.isPending}
            >
              {cancel.isPending ? "Отменяем…" : "Отменить авто-продление"}
            </button>
          )}
          {isPro && !sub.auto_renew && sub.status !== "expired" && (
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => reactivate.mutate()}
              disabled={reactivate.isPending}
            >
              {reactivate.isPending ? "Включаем…" : "Возобновить авто-продление"}
            </button>
          )}
        </div>

        {(cancel.error || reactivate.error || purchase.error) && (
          <div className="error-banner" style={{ marginTop: 12 }}>
            {(cancel.error || reactivate.error || purchase.error)?.message}
          </div>
        )}
      </div>
    </>
  );
}

function statusLabel(status: string): string {
  return (
    {
      active: "активна",
      cancelled: "отменена (доступ сохраняется до конца периода)",
      past_due: "просрочена — попытаемся продлить ещё несколько дней",
      expired: "истекла",
    }[status] || status
  );
}
