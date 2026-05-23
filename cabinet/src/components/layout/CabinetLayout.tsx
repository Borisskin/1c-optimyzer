import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiAuth } from "@/api/endpoints";

export function CabinetLayout() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const me = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => apiAuth.me(),
  });
  const logout = useMutation({
    mutationFn: () => apiAuth.logout(),
    onSuccess: () => {
      qc.removeQueries();
      navigate("/login", { replace: true });
    },
  });

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <PulseLogo />
          <span className="sidebar__name">Optimyzer</span>
        </div>
        <nav className="sidebar__nav">
          <NavLink to="/" end className={navLinkClass}>
            Обзор
          </NavLink>
          <NavLink to="/subscription" className={navLinkClass}>
            Подписка
          </NavLink>
          <NavLink to="/credits" className={navLinkClass}>
            Кредиты
          </NavLink>
          <NavLink to="/devices" className={navLinkClass}>
            Устройства
          </NavLink>
          <NavLink to="/payments" className={navLinkClass}>
            Платежи
          </NavLink>
          <NavLink to="/usage" className={navLinkClass}>
            Использование
          </NavLink>
          <NavLink to="/settings" className={navLinkClass}>
            Настройки
          </NavLink>
        </nav>
        <div className="sidebar__bottom">
          {me.data?.user && (
            <div style={{ fontSize: 13, color: "var(--fg-2)", marginBottom: 8 }}>
              {me.data.user.email}
            </div>
          )}
          <button
            type="button"
            className="btn"
            style={{ width: "100%" }}
            onClick={() => logout.mutate()}
          >
            Выйти
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return isActive ? "sidebar__link active" : "sidebar__link";
}

function PulseLogo() {
  return (
    <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" className="sidebar__logo" aria-hidden="true">
      <circle cx="32" cy="32" r="26" fill="none" stroke="#0EA5A4" strokeWidth="6" />
      <rect x="19" y="36" width="6" height="12" rx="1.5" fill="#0F1B2D" />
      <rect x="29" y="28" width="6" height="20" rx="1.5" fill="#0F1B2D" />
      <rect x="39" y="20" width="6" height="28" rx="1.5" fill="#0EA5A4" />
    </svg>
  );
}
