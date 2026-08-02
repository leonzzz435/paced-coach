import DashboardClient from "@/components/dashboard/dashboard-client";
import { apiFetch } from "@/lib/api";
import type { DashboardStateResponse } from "@/lib/types/dashboard";

export default async function DashboardPage() {
  let dashboardState: DashboardStateResponse | null = null;
  let backendError: string | null = null;

  const apiBaseUrl = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");
  const backendConfigured = apiBaseUrl !== "http://localhost:8000";

  try {
    dashboardState = await apiFetch<DashboardStateResponse>("/api/dashboard/state");
  } catch (error) {
    backendError = error instanceof Error ? error.message : "Failed to reach backend";
  }

  if (!dashboardState) {
    return (
      <div className="rounded-2xl border border-rose-400/20 bg-[var(--surface)] p-6 text-sm text-[var(--text-primary)]">
        <div className="font-semibold">Dashboard could not load</div>
        <div className="mt-2 max-w-2xl text-[var(--text-secondary)]">
          {!backendConfigured
            ? "The local API returned an error. Your saved profile and plans are unchanged. Check the API logs, then refresh this page."
            : backendError}
        </div>
      </div>
    );
  }

  return <DashboardClient initialState={dashboardState} />;
}
