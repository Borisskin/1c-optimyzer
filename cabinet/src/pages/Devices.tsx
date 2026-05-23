import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDevices } from "@/api/endpoints";

export function Devices() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["devices"],
    queryFn: () => apiDevices.list(),
  });
  const deactivate = useMutation({
    mutationFn: (id: string) => apiDevices.deactivate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["devices"] }),
  });

  return (
    <>
      <div className="page__head">
        <h1 className="page__title">Устройства</h1>
        <p className="page__lead">
          Активные desktop-установки. Лимит зависит от тарифа: Free — 1, Pro — 5.
        </p>
      </div>

      <div className="card">
        {isLoading && <div className="loader">Загружаем…</div>}
        {error && <div className="error-banner">Не удалось загрузить устройства</div>}
        {data && data.devices.length === 0 && (
          <div className="empty">
            Нет активированных устройств. Скачайте Optimyzer и активируйте лицензию по ключу.
          </div>
        )}
        {data && data.devices.length > 0 && (
          <>
            <p style={{ marginTop: 0, color: "var(--fg-2)" }}>
              Использовано {data.devices.length} из {data.limit}
            </p>
            <table className="table">
              <thead>
                <tr>
                  <th>Устройство</th>
                  <th>Платформа</th>
                  <th>Версия</th>
                  <th>Последний раз</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.devices.map((d) => (
                  <tr key={d.id}>
                    <td>{d.name}</td>
                    <td>{d.platform}</td>
                    <td>{d.app_version}</td>
                    <td>{new Date(d.last_seen_at).toLocaleString("ru-RU")}</td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        type="button"
                        className="btn btn--danger"
                        onClick={() => deactivate.mutate(d.id)}
                        disabled={deactivate.isPending}
                      >
                        Деактивировать
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </>
  );
}
