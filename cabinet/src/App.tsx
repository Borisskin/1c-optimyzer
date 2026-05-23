import { Navigate, Route, Routes } from "react-router-dom";
import { CabinetLayout } from "@/components/layout/CabinetLayout";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { Login } from "@/pages/Login";
import { OAuthCallback } from "@/pages/OAuthCallback";
import { Overview } from "@/pages/Overview";
import { Subscription } from "@/pages/Subscription";
import { Credits } from "@/pages/Credits";
import { Devices } from "@/pages/Devices";
import { Payments } from "@/pages/Payments";
import { Usage } from "@/pages/Usage";
import { Settings } from "@/pages/Settings";

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
        <Route path="/subscription" element={<Subscription />} />
        <Route path="/credits" element={<Credits />} />
        <Route path="/devices" element={<Devices />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/usage" element={<Usage />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
