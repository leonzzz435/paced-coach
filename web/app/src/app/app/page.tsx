import DashboardClient from "@/components/dashboard/dashboard-client";
import { apiFetch } from "@/lib/api";
import { emptyCoachSurface, type DashboardStateResponse } from "@/lib/types/dashboard";

function buildEmptyDashboardState(): DashboardStateResponse {
  return {
    athlete_time: {
      timezone: "UTC",
      timezone_source: "fallback_utc",
      today_local_date: new Date().toISOString().slice(0, 10),
      now_local_iso: new Date().toISOString(),
    },
    analysis: null,
    status_surface: {
      kpis: [],
      source: "none",
      label: null,
      updated_at: null,
      target_date: null,
    },
    coach_surface: emptyCoachSurface(),
    season: null,
    weekly: null,
    first_run: {
      mode: "manual",
      evidence_level: "declared_only",
      llm_ready: false,
      profile_completeness: 0,
      profile_ready: false,
      goal_ready: false,
      has_competitions: false,
      has_active_plan: false,
      has_connected_source: false,
      next_step: "llm_key",
      title: "Connect the local backend",
      body: "Start the API and add one supported LLM key before generating a local training plan.",
      primary_action: null,
      secondary_actions: [],
      blockers: ["Set API_BASE_URL if your backend is not running on localhost:8000."],
    },
    today_mission: {
      warnings: [],
      day_override: null,
    },
    daily_sync: {
      visible: false,
      status: "idle",
      run_id: null,
      verdict_preview: null,
      sources_used: [],
      proposal_id: null,
      thread_id: null,
      error_message: null,
      can_run: false,
      attention_message: null,
      gate_target: null,
    },
    weekly_recap: {
      visible: false,
      allowed: false,
      status: "hidden",
      thread_id: null,
      proposal_id: null,
      follow_up_question: null,
      summary_preview: null,
      pending_action: "none",
      can_run: false,
      attention_message: null,
      gate_target: null,
    },
    pending_proposal_banner: null,
  };
}

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

  const initialState = dashboardState ?? buildEmptyDashboardState();

  return (
    <>
      <DashboardClient initialState={initialState} />

      {backendError ? (
        <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--text-primary)]">
          <div className="font-medium">Service status</div>
          <div className="mt-1 text-[var(--text-secondary)]">
            {!backendConfigured
              ? "This app shell cannot reach the local training backend yet. Start the API, keep your local database intact, then refresh this page."
              : backendError}
          </div>
        </div>
      ) : null}
    </>
  );
}
