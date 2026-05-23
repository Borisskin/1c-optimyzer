import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const FROM_KEY = "optimyzer.oauth.from";

/**
 * После /v1/auth/yandex/callback backend выставляет cookies и редиректит сюда.
 * Здесь решаем куда дальше:
 *   - если юзер пришёл из desktop'а (флаг в sessionStorage) — на /desktop-activate
 *   - иначе — на главную /
 */
export function OAuthCallback() {
  const navigate = useNavigate();
  useEffect(() => {
    const from = sessionStorage.getItem(FROM_KEY);
    sessionStorage.removeItem(FROM_KEY); // одноразовое использование
    navigate(from === "desktop" ? "/desktop-activate" : "/", { replace: true });
  }, [navigate]);
  return <div className="loader">Завершаем вход…</div>;
}
