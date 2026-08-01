import { Suspense } from "react";
import Link from "next/link";

import PlanViewer from "@/components/plan-viewer/plan-viewer";
import type { SeasonPlanV3, WeeklyPlanV3 } from "@/components/plan-viewer/types";
import { apiFetch } from "@/lib/api";
import { isApiError } from "@/lib/api_errors";
import type { UiAnalysis, UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";

type ActivePlansBundle = {
  analysis?: { analysis: UiAnalysis; version: number; updated_at: string; source_job_id: string } | null;
  season?: { season_plan: UiSeasonPlan | SeasonPlanV3; version: number; updated_at: string; source_job_id: string } | null;
  weekly?: { weekly_plan: UiWeeklyPlan | WeeklyPlanV3; version: number; updated_at: string; source_job_id: string } | null;
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
  let renderNowIso: string | undefined;

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

  if (activePlans && !backendError) {
    try {
      const dashboardClock = await apiFetch<{ athlete_time?: { now_local_iso?: string } }>("/api/dashboard/state");
      renderNowIso = dashboardClock.athlete_time?.now_local_iso;
    } catch {
      // The plan remains readable using the browser-local clock when the
      // richer dashboard state is temporarily unavailable.
    }
  }

  const analysis = activePlans?.analysis?.analysis;
  const seasonPlan = activePlans?.season?.season_plan;
  const weeklyPlan = activePlans?.weekly?.weekly_plan;

  return (
    <div className="space-y-4">
      {backendError ? (
        <section
          className="rounded-2xl border border-rose-400/25 bg-rose-500/[0.07] p-6 text-[var(--text-primary)] sm:p-8"
          role="alert"
        >
          <div className="text-xs font-bold uppercase tracking-[0.16em] text-rose-300">Plan service unavailable</div>
          <h1 className="mt-2 text-xl font-semibold tracking-tight">Your saved plan could not be loaded</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">
            {!backendConfigured
              ? "The app cannot reach the local training backend. Start the API and refresh this page. Your saved profile and plans are unchanged."
              : `${backendError} Your saved profile and plans are unchanged.`}
          </p>
        </section>
      ) : analysis || seasonPlan || weeklyPlan ? (
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
    </div>
  );
}
