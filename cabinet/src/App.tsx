import { Navigate, Route, Routes } from "react-router-dom";
import { CabinetLayout } from "@/components/layout/CabinetLayout";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { Login } from "@/pages/Login";
import { OAuthCallback } from "@/pages/OAuthCallback";
import { Overview } from "@/pages/Overview";
import { Subscription } from "@/pages/Subscription";
import { Credits } from "@/pages/Credits";
import { Payments } from "@/pages/Payments";
import { Settings } from "@/pages/Settings";
import { DesktopActivate } from "@/pages/DesktopActivate";
// Devices/Usage пока не показываем — нечего отображать в pre-launch.
// Файлы pages/Devices.tsx и pages/Usage.tsx оставлены для будущего.

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
        <Route path="/desktop-activate" element={<DesktopActivate />} />
        <Route path="/subscription" element={<Subscription />} />
        <Route path="/credits" element={<Credits />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/settings" element={<Settings />} />
        {/* Dead routes — редиректим на главную чтобы старые ссылки не вели в 404 */}
        <Route path="/devices" element={<Navigate to="/" replace />} />
        <Route path="/usage" element={<Navigate to="/" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
