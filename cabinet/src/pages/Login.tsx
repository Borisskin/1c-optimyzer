import { useState } from "react";
import { apiAuth } from "@/api/endpoints";
import { ApiError } from "@/api/client";

export function Login() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startYandexLogin() {
    setBusy(true);
    setError(null);
    try {
      const resp = await apiAuth.yandexLoginUrl();
      // Сохраним state в localStorage (на случай если cookie не подтянется).
      localStorage.setItem("optimyzer.oauth.state", resp.state);
      window.location.assign(resp.authorize_url);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? `${e.message} (HTTP ${e.status})`
          : "Не удалось получить URL для Yandex входа",
      );
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <div className="login__card">
        <svg
          viewBox="0 0 64 64"
          className="login__logo"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <circle cx="32" cy="32" r="26" fill="none" stroke="#0EA5A4" strokeWidth="6" />
          <rect x="19" y="36" width="6" height="12" rx="1.5" fill="#0F1B2D" />
          <rect x="29" y="28" width="6" height="20" rx="1.5" fill="#0F1B2D" />
          <rect x="39" y="20" width="6" height="28" rx="1.5" fill="#0EA5A4" />
        </svg>
        <h1 className="login__title">Optimyzer</h1>
        <p className="login__sub">Личный кабинет — подписка, кредиты, устройства</p>

        <button
          type="button"
          className="login__yandex"
          onClick={startYandexLogin}
          disabled={busy}
        >
          {busy ? "Перенаправляем…" : "Войти через Yandex"}
        </button>

        {error && (
          <p className="login__footnote" style={{ color: "var(--danger)" }}>
            {error}
          </p>
        )}

        <p className="login__footnote">
          Нажимая «Войти через Yandex», вы соглашаетесь с{" "}
          <a
            href={
              (import.meta.env.VITE_LANDING_URL || "http://localhost:8000") +
              "/docs/billing/payment-methods"
            }
            target="_blank"
            rel="noreferrer"
          >
            условиями использования
          </a>
          .
        </p>
      </div>
    </div>
  );
}
