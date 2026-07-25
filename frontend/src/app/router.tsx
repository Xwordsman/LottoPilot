import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { DashboardPage } from "@/features/auth/DashboardPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { SetupPage } from "@/features/auth/SetupPage";
import { BacktestsPage } from "@/features/backtests/BacktestsPage";
import { DrawsPage } from "@/features/draws/DrawsPage";
import { RecommendationsPage } from "@/features/recommendations/RecommendationsPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { JobsPage } from "@/features/jobs/JobsPage";
import { StrategiesPage } from "@/features/strategies/StrategiesPage";
import { useAuthStore } from "@/lib/auth-store";

function ProtectedLayout() {
  const user = useAuthStore((s) => s.user);
  const initialized = useAuthStore((s) => s.initialized);

  if (initialized === false) {
    return <Navigate to="/setup" replace />;
  }
  if (initialized === true && !user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/setup" element={<SetupPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/draws" element={<DrawsPage />} />
        <Route path="/history" element={<DrawsPage />} />
        <Route path="/data" element={<DrawsPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/analysis" element={<AnalyticsPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
        <Route path="/backtests" element={<BacktestsPage />} />
        <Route path="/strategies" element={<StrategiesPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/ai" element={<SettingsPage />} />
        <Route path="/settings/system" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}