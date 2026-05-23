import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { apiLicense } from "@/api/endpoints";

/**
 * Страница активации desktop приложения (device flow).
 *
 * Юзер попадает сюда после OAuth login. Cabinet получает session_id из URL
 * (`?session=XXX`) и сразу POST'ит на /v1/license/desktop-confirm. Desktop
 * приложение тем временем polling'ом ждёт confirm — как только сработало,
 * заходит в основной UI.
 *
 * Юзеру тут ничего делать не надо — просто показываем «Готово, вернитесь
 * в Optimyzer».
 */
export function DesktopActivate() {
  const [params] = useSearchParams();
  const sessionId = params.get("session");

  const confirm = useMutation({
    mutationFn: () => {
      if (!sessionId) throw new Error("no session");
      return apiLicense.desktopConfirm(sessionId);
    },
  });

  useEffect(() => {
    if (sessionId && !confirm.data && !confirm.isPending && !confirm.error) {
      confirm.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  if (!sessionId) {
    return (
      <>
        <div className="page__head">
          <h1 className="page__title">Активация desktop приложения</h1>
        </div>
        <div className="card">
          <p style={{ margin: 0, color: "var(--fg-2)" }}>
            Откройте Optimyzer и нажмите «Войти через Yandex». Вы автоматически
            попадёте на эту страницу с правильной ссылкой активации.
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="page__head">
        <h1 className="page__title">Активация desktop приложения</h1>
      </div>

      {confirm.isPending && (
        <div className="card">
          <div className="loader">Активируем…</div>
        </div>
      )}

      {confirm.error && (
        <div className="error-banner">
          Не удалось активировать: {confirm.error.message}.{" "}
          <button
            type="button"
            className="btn"
            style={{ marginTop: 8 }}
            onClick={() => confirm.mutate()}
          >
            Попробовать ещё раз
          </button>
        </div>
      )}

      {confirm.data && (
        <div className="card">
          <h2 className="card__title" style={{ color: "var(--accent)" }}>
            ✓ Готово!
          </h2>
          <p style={{ margin: "0 0 16px", color: "var(--fg)" }}>
            Optimyzer активирован на устройстве <strong>{confirm.data.device_name}</strong>.
          </p>
          <p style={{ margin: 0, color: "var(--fg-2)" }}>
            Вернитесь в Optimyzer — приложение само поймёт что вы вошли,
            и откроет основной экран. Эту вкладку можно закрыть.
          </p>
        </div>
      )}
    </>
  );
}
