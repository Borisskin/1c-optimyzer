import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

/**
 * После /v1/auth/yandex/callback backend выставляет cookies и редиректит сюда.
 * Дальше — на главную /. ProtectedRoute подхватит auth по cookie.
 */
export function OAuthCallback() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate("/", { replace: true });
  }, [navigate]);
  return <div className="loader">Завершаем вход…</div>;
}
