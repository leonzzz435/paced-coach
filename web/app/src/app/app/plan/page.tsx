import { Suspense } from "react";
import Link from "next/link";

import PlanViewer from "@/components/plan-viewer/plan-viewer";
import { apiFetch } from "@/lib/api";
import { isApiError } from "@/lib/api_errors";
import type { UiAnalysis, UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";

type ActivePlansBundle = {
  analysis?: { analysis: UiAnalysis; version: number; updated_at: string; source_job_id: string } | null;
  season?: { season_plan: UiSeasonPlan; version: number; updated_at: string; source_job_id: string } | null;
  weekly?: { weekly_plan: UiWeeklyPlan; version: number; updated_at: string; source_job_id: string } | null;
} | null;

function PlanViewerFallback() {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center text-[var(--text-muted)]">
      Loading training plan...
    </div>
  );
}

export default async function PlanPage() {
  let activePlans: ActivePlansBundle = null;
  let backendError: string | null = null;
  const renderNowIso = new Date().toISOString();

  const apiBaseUrl = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");
  const backendConfigured = apiBaseUrl !== "http://localhost:8000";

  try {
    activePlans = await apiFetch<ActivePlansBundle>("/api/plans/active");
  } catch (err) {
    if (!isApiError(err) || err.status !== 404) {
      if (err instanceof Error) {
        backendError = err.message;
      } else {
        backendError = "Failed to reach backend";
      }
    }
  }

  const analysis = activePlans?.analysis?.analysis;
  const seasonPlan = activePlans?.season?.season_plan;
  const weeklyPlan = activePlans?.weekly?.weekly_plan;

  return (
    <div className="space-y-4">
      {analysis || seasonPlan || weeklyPlan ? (
        <Suspense fallback={<PlanViewerFallback />}>
          <PlanViewer analysis={analysis} seasonPlan={seasonPlan} weeklyPlan={weeklyPlan} nowIso={renderNowIso} />
        </Suspense>
      ) : (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">No active training plan yet</h1>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-[var(--text-secondary)]">
            Generate a personal season roadmap and 28-day block from your saved profile, goals, race calendar, and one
            configured LLM key. No wearable required.
          </p>
          <Link
            className="mt-5 inline-flex rounded-xl bg-[var(--accent-primary)] px-5 py-3 text-sm font-bold text-white transition hover:brightness-110"
            href="/app/new"
          >
            Generate plan
          </Link>
        </div>
      )}

      {backendError ? (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--text-primary)]">
          <div className="font-medium">Service status</div>
          <div className="mt-1 text-[var(--text-secondary)]">
            {!backendConfigured
              ? "This app shell cannot reach the local training backend yet. Start the API, keep your local database intact, then refresh this page."
              : backendError}
          </div>
        </div>
      ) : null}
    </div>
  );
}
