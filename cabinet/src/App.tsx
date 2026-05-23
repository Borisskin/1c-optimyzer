import { Navigate, Route, Routes } from "react-router-dom";
import { CabinetLayout } from "@/components/layout/CabinetLayout";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { Login } from "@/pages/Login";
import { OAuthCallback } from "@/pages/OAuthCallback";
import { Overview } from "@/pages/Overview";
import { Credits } from "@/pages/Credits";
import { Payments } from "@/pages/Payments";
// В pre-launch sidebar показывает только: Обзор / Кредиты / Платежи.
// Subscription / Settings / Devices / Usage / desktop-activate скрыты —
// route'ы редиректят на главную, чтобы старые URL'ы не вели в 404.

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />
      <Route
        element={
          <ProtectedRoute>
            <CabinetLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Overview />} />
        <Route path="/credits" element={<Credits />} />
        <Route path="/payments" element={<Payments />} />
        {/* Скрытые в pre-launch — нечего показывать, редирект на главную */}
        <Route path="/subscription" element={<Navigate to="/" replace />} />
        <Route path="/settings" element={<Navigate to="/" replace />} />
        <Route path="/devices" element={<Navigate to="/" replace />} />
        <Route path="/usage" element={<Navigate to="/" replace />} />
        <Route path="/desktop-activate" element={<Navigate to="/" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
