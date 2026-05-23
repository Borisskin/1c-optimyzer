import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

/**
 * После /v1/auth/yandex/callback backend выставляет cookies и редиректит сюда.
 * Здесь мы просто перенаправляем на /. ProtectedRoute сам подхватит auth.
 */
export function OAuthCallback() {
  const navigate = useNavigate();
  useEffect(() => {
    // Уберём «?just_logged_in=1» из URL, если есть.
    navigate("/", { replace: true });
  }, [navigate]);
  return <div className="loader">Завершаем вход…</div>;
}
