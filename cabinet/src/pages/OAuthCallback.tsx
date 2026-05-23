import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const FROM_KEY = "optimyzer.oauth.from";
const SESSION_KEY = "optimyzer.oauth.desktop_session";

/**
 * После /v1/auth/yandex/callback backend выставляет cookies и редиректит сюда.
 * Решаем куда дальше:
 *   - если есть desktop session_id — на /desktop-activate?session=... (device flow)
 *   - если просто from=desktop без session — на /desktop-activate (юзер увидит подсказку)
 *   - иначе — на главную /
 */
export function OAuthCallback() {
  const navigate = useNavigate();
  useEffect(() => {
    const from = sessionStorage.getItem(FROM_KEY);
    const session = sessionStorage.getItem(SESSION_KEY);
    sessionStorage.removeItem(FROM_KEY);
    sessionStorage.removeItem(SESSION_KEY);
    if (session) {
      navigate(`/desktop-activate?session=${encodeURIComponent(session)}`, { replace: true });
    } else if (from === "desktop") {
      navigate("/desktop-activate", { replace: true });
    } else {
      navigate("/", { replace: true });
    }
  }, [navigate]);
  return <div className="loader">Завершаем вход…</div>;
}
