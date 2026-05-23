import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiAuth } from "@/api/endpoints";

/** Гейт для роутов кабинета — пускает только если /v1/auth/me даёт 200. */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const me = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => apiAuth.me(),
    retry: false,
  });

  if (me.isLoading) {
    return <div className="loader">Загружаем кабинет…</div>;
  }

  if (me.isError || !me.data?.user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
