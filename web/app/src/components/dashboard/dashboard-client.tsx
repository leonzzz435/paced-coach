"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import CoachInsight from "@/components/dashboard/coach-insight";
import PendingCoachProposalBanner from "@/components/dashboard/pending-coach-proposal-banner";
import SeasonProgress from "@/components/dashboard/season-progress";
import StatusGauges from "@/components/dashboard/status-gauges";
import TodayMission from "@/components/dashboard/today-mission";
import WeekStrip from "@/components/dashboard/week-strip";
import type { DashboardStateResponse } from "@/lib/types/dashboard";

type Props = {
  initialState: DashboardStateResponse;
};

function FirstRunPanel({ state }: { state: DashboardStateResponse["first_run"] }) {
  const modeLabel = state.mode === "manual" ? "Manual Mode" : "Connected Mode";
  const evidenceLabel = state.evidence_level === "declared_only" ? "Declared context only" : "Connected data available";

  return (
    <section className="relative flex h-full min-h-[420px] overflow-hidden rounded-2xl border border-[var(--border)] bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.16),transparent_34%),linear-gradient(135deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))] p-6 shadow-sm">
      <div className="relative z-10 flex max-w-2xl flex-col justify-center">
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-emerald-400/25 bg-emerald-400/12 px-3 py-1 text-xs font-semibold text-emerald-200">
            {modeLabel}
          </span>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-semibold text-[var(--text-muted)]">
            {evidenceLabel}
          </span>
        </div>

        <h2 className="mt-5 text-3xl font-semibold tracking-[-0.04em] text-[var(--text-primary)] sm:text-4xl">
          {state.title}
        </h2>
        <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--text-secondary)]">{state.body}</p>

        <div className="mt-5 grid gap-2 text-sm text-[var(--text-secondary)] sm:grid-cols-3">
          <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">LLM key</div>
            <div className="mt-1 font-semibold text-[var(--text-primary)]">{state.llm_ready ? "Ready" : "Missing"}</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">Profile</div>
            <div className="mt-1 font-semibold text-[var(--text-primary)]">{state.profile_completeness}% complete</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">Goal</div>
            <div className="mt-1 font-semibold text-[var(--text-primary)]">{state.goal_ready ? "Set" : "Needed"}</div>
          </div>
        </div>

        {state.blockers.length > 0 ? (
          <div className="mt-5 rounded-xl border border-amber-400/25 bg-amber-400/10 p-3 text-sm text-amber-100">
            <div className="font-semibold">Before generation</div>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {state.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="mt-6 flex flex-wrap items-center gap-3">
          {state.primary_action ? (
            <Link
              className="inline-flex rounded-xl bg-[var(--accent-primary)] px-5 py-3 text-sm font-bold text-white transition hover:brightness-110"
              href={state.primary_action.href}
            >
              {state.primary_action.label}
            </Link>
          ) : null}
          {state.secondary_actions.map((action) => (
            <Link
              className="inline-flex rounded-xl border border-[var(--border)] px-4 py-3 text-sm font-semibold text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]"
              href={action.href}
              key={`${action.href}-${action.label}`}
            >
              {action.label}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function DashboardClient({ initialState }: Props) {
  const [dashboardState, setDashboardState] = useState(initialState);
  const [dismissedProposalId, setDismissedProposalId] = useState<string | null>(null);

  useEffect(() => {
    setDashboardState(initialState);
  }, [initialState]);

  const coachSurface = dashboardState.coach_surface;
  const statusSurface = dashboardState.status_surface;
  const seasonPlan = dashboardState.season?.season_plan;
  const weeklyPlan = dashboardState.weekly?.weekly_plan;

  const visibleProposalBanner = useMemo(() => {
    const banner = dashboardState.pending_proposal_banner;
    if (!banner) return null;
    if (dismissedProposalId && banner.proposal_id === dismissedProposalId) return null;
    return banner;
  }, [dashboardState.pending_proposal_banner, dismissedProposalId]);

  return (
    <div className="space-y-4">
      {visibleProposalBanner ? (
        <PendingCoachProposalBanner
          banner={visibleProposalBanner}
          onDismiss={() => setDismissedProposalId(visibleProposalBanner.proposal_id)}
        />
      ) : null}

      <div className="flex h-full min-h-[500px] flex-col gap-4 lg:grid lg:grid-cols-5 lg:grid-rows-[auto_1fr_auto]">
        <div className="flex flex-col lg:col-span-5">
          <StatusGauges surface={statusSurface} />
        </div>

        <div className="flex flex-col lg:col-span-3 lg:row-start-2 lg:overflow-hidden">
          {weeklyPlan ? (
            <TodayMission
              weeklyPlan={weeklyPlan}
              warnings={dashboardState.today_mission.warnings}
              dayOverride={dashboardState.today_mission.day_override ?? undefined}
              dailySyncCompleted={false}
            />
          ) : (
            <FirstRunPanel state={dashboardState.first_run} />
          )}
        </div>

        <div className="flex flex-col gap-4 lg:col-span-2 lg:col-start-4 lg:row-start-2 lg:overflow-hidden">
          <SeasonProgress seasonPlan={seasonPlan} nowIso={dashboardState.athlete_time.now_local_iso} />
          <CoachInsight surface={coachSurface} />
        </div>

        <div className="lg:col-span-5 lg:row-start-3">
          <WeekStrip weeklyPlan={weeklyPlan} />
        </div>
      </div>
    </div>
  );
}
