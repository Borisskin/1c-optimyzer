import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiCredits } from "@/api/endpoints";

const PACKAGES = [
  { id: "mini" as const, label: "Mini", operations: 30, priceRub: 299, hint: "разово, до 30 дней" },
  { id: "standard" as const, label: "Standard", operations: 100, priceRub: 990, hint: "до 30 дней" },
  { id: "bulk" as const, label: "Bulk", operations: 300, priceRub: 2490, hint: "до 30 дней" },
];

export function Credits() {
  const qc = useQueryClient();
  const balance = useQuery({
    queryKey: ["credits", "balance"],
    queryFn: () => apiCredits.balance(),
  });
  const purchase = useMutation({
    mutationFn: (pkg: "mini" | "standard" | "bulk") => apiCredits.purchase(pkg),
    onSuccess: (resp) => {
      qc.invalidateQueries({ queryKey: ["credits"] });
      if (resp.confirmation_url) {
        window.location.assign(resp.confirmation_url);
      }
    },
  });

  return (
    <>
      <div className="page__head">
        <h1 className="page__title">Кредиты</h1>
        <p className="page__lead">
          1 кредит = 1 AI-операция. Кредиты сгорают через 30 дней после покупки.
        </p>
      </div>

      <div className="card">
        <h2 className="card__title">Текущий баланс</h2>
        {balance.isLoading ? (
          <div className="loader">Загружаем…</div>
        ) : balance.error ? (
          <div className="error-banner">Не удалось загрузить баланс</div>
        ) : (
          <div style={{ fontSize: 36, fontWeight: 700 }}>
            {balance.data?.operations_remaining || 0}{" "}
            <span style={{ fontSize: 14, color: "var(--fg-3)", fontWeight: 500 }}>операций</span>
          </div>
        )}
        {balance.data && balance.data.active_packages.length > 0 && (
          <table className="table" style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>Пакет</th>
                <th>Остаток</th>
                <th>Истекает</th>
              </tr>
            </thead>
            <tbody>
              {balance.data.active_packages.map((p) => (
                <tr key={p.id}>
                  <td>{p.package}</td>
                  <td>
                    {p.operations_remaining} / {p.operations_total}
                  </td>
                  <td>{new Date(p.expires_at).toLocaleDateString("ru-RU")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="grid-cards">
        {PACKAGES.map((pkg) => (
          <div key={pkg.id} className="card" style={{ marginBottom: 0 }}>
            <div className="metric__label">{pkg.label}</div>
            <div style={{ fontSize: 32, fontWeight: 700 }}>{pkg.operations}</div>
            <div className="metric__hint">{pkg.hint}</div>
            <div style={{ fontSize: 24, fontWeight: 700, margin: "12px 0" }}>{pkg.priceRub} ₽</div>
            <button
              type="button"
              className="btn btn--primary"
              style={{ width: "100%" }}
              onClick={() => purchase.mutate(pkg.id)}
              disabled={purchase.isPending}
            >
              {purchase.isPending && purchase.variables === pkg.id
                ? "Создаём платёж…"
                : "Купить"}
            </button>
          </div>
        ))}
      </div>

      {purchase.error && (
        <div className="error-banner">{purchase.error.message}</div>
      )}
    </>
  );
}
