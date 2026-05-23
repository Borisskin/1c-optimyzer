import { useQuery } from "@tanstack/react-query";
import { apiCredits } from "@/api/endpoints";

export function Payments() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["credits", "history"],
    queryFn: () => apiCredits.history(),
  });

  return (
    <>
      <div className="page__head">
        <h1 className="page__title">История платежей</h1>
        <p className="page__lead">
          История покупок. Чеки приходят на email.
        </p>
      </div>

      <div className="card">
        {isLoading && <div className="loader">Загружаем…</div>}
        {error && <div className="error-banner">Не удалось загрузить историю</div>}
        {data && data.items.length === 0 && (
          <div className="empty">Платежей пока нет.</div>
        )}
        {data && data.items.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Пакет</th>
                <th>Операций</th>
                <th>Истекает</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((p) => (
                <tr key={p.id}>
                  <td>{new Date(p.purchased_at).toLocaleDateString("ru-RU")}</td>
                  <td>{p.package}</td>
                  <td>
                    {p.operations_used} / {p.operations_total}
                  </td>
                  <td>{new Date(p.expires_at).toLocaleDateString("ru-RU")}</td>
                  <td>
                    <span className={`pill ${p.is_active ? "" : "pill--warn"}`}>
                      {p.is_active ? "активен" : "истёк"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
