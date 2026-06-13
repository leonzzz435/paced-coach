"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { runWeeklyRecapAction } from "@/app/actions/recap";
import CoachInsight from "@/components/dashboard/coach-insight";
import DailySyncWidget from "@/components/dashboard/daily-sync-widget";
import PendingCoachProposalBanner from "@/components/dashboard/pending-coach-proposal-banner";
import SeasonProgress from "@/components/dashboard/season-progress";
import StatusGauges from "@/components/dashboard/status-gauges";
import TodayMission from "@/components/dashboard/today-mission";
import WeeklyRecapReportPanel from "@/components/dashboard/weekly-recap-report-panel";
import WeeklyRecapWidget from "@/components/dashboard/weekly-recap-widget";
import WeekStrip from "@/components/dashboard/week-strip";
import { extractContentText } from "@/lib/types/ask-about";
import type { CoachTurnResponse } from "@/lib/types/coach";
import type { DashboardStateResponse, DailyRunResponse, PendingProposalBannerState } from "@/lib/types/dashboard";
import type { WeeklyRecapReportResponse } from "@/lib/types/recap";
import {
  buildCoachSurfaceFromDailySyncResult,
  buildCoachSurfaceFromWeeklyRecap,
  getRecapTurnPayload,
  resolveDailySyncVerdictPreview,
  resolveRecapSummaryPreview,
  resolveWeeklyRecapPendingAction,
} from "@/lib/types/dashboard";

const DASHBOARD_PENDING_POLL_INTERVAL_MS = 5_000;

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
  const [weeklyRecapError, setWeeklyRecapError] = useState<string | null>(null);
  const [weeklyRecapReport, setWeeklyRecapReport] = useState<WeeklyRecapReportResponse | null>(null);
  const [weeklyRecapReportLoading, setWeeklyRecapReportLoading] = useState(false);
  const [weeklyRecapReportError, setWeeklyRecapReportError] = useState<string | null>(null);
  const [weeklyRecapReportOpen, setWeeklyRecapReportOpen] = useState(false);
  const [dismissedProposalId, setDismissedProposalId] = useState<string | null>(null);

  useEffect(() => {
    setDashboardState(initialState);
  }, [initialState]);

  useEffect(() => {
    if (dashboardState.daily_sync.status !== "pending") {
      return;
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const pollDashboardState = async () => {
      try {
        const response = await fetch("/app/api/dashboard/state", {
          method: "GET",
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`Dashboard polling failed with ${response.status}`);
        }
        const nextState = (await response.json()) as DashboardStateResponse;
        if (cancelled) {
          return;
        }
        setDashboardState(nextState);
        if (nextState.daily_sync.status === "pending") {
          timeoutId = setTimeout(pollDashboardState, DASHBOARD_PENDING_POLL_INTERVAL_MS);
        }
      } catch {
        if (!cancelled) {
          timeoutId = setTimeout(pollDashboardState, DASHBOARD_PENDING_POLL_INTERVAL_MS);
        }
      }
    };

    void pollDashboardState();

    return () => {
      cancelled = true;
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    };
  }, [dashboardState.daily_sync.run_id, dashboardState.daily_sync.status]);

  const coachSurface = dashboardState.coach_surface;
  const statusSurface = dashboardState.status_surface;
  const seasonPlan = dashboardState.season?.season_plan;
  const weeklyPlan = dashboardState.weekly?.weekly_plan;
  const dailySyncState = {
    ...dashboardState.daily_sync,
    verdict_preview: resolveDailySyncVerdictPreview(
      dashboardState.daily_sync,
      dashboardState.today_mission.day_override,
    ),
  };

  const visibleProposalBanner = useMemo(() => {
    const banner = dashboardState.pending_proposal_banner;
    if (!banner) return null;
    if (dismissedProposalId && banner.proposal_id === dismissedProposalId) return null;
    return banner;
  }, [dashboardState.pending_proposal_banner, dismissedProposalId]);

  const updatePendingProposalBanner = (banner: PendingProposalBannerState) => {
    setDashboardState((previous) => ({
      ...previous,
      pending_proposal_banner: banner,
    }));
    if (banner?.proposal_id) {
      setDismissedProposalId(null);
    }
  };

  const buildWeeklyRecapReport = (response: CoachTurnResponse): WeeklyRecapReportResponse | null => {
    const recapTurn = getRecapTurnPayload(response);
    if (!recapTurn) return null;

    return {
      recap: recapTurn.recap,
      thread_id: response.thread.id,
      summary_preview: resolveRecapSummaryPreview(recapTurn.recap),
      pending_action: resolveWeeklyRecapPendingAction({
        proposalId: recapTurn.recap.proposal_id ?? null,
        followUpQuestion: recapTurn.recap.follow_up_question ?? null,
        athleteResponse: recapTurn.recap.athlete_response ?? null,
      }),
    };
  };

  const parseApiError = (raw: string, fallback: string): string => {
    if (!raw.trim()) return fallback;
    try {
      const payload = JSON.parse(raw) as { detail?: unknown; message?: unknown };
      if (typeof payload.detail === "string" && payload.detail.trim()) return payload.detail;
      if (typeof payload.message === "string" && payload.message.trim()) return payload.message;
    } catch {
      // ignore invalid JSON and fall back to raw text
    }
    return raw || fallback;
  };

  const parseRecapReportError = (raw: string): string => {
    return parseApiError(raw, "Unable to load weekly recap.");
  };

  const openWeeklyRecapReport = async (prefill: WeeklyRecapReportResponse | null = null) => {
    setWeeklyRecapReportOpen(true);
    setWeeklyRecapReportError(null);

    if (prefill) {
      setWeeklyRecapReport(prefill);
      setWeeklyRecapReportLoading(false);
      return;
    }

    setWeeklyRecapReportLoading(true);
    try {
      const response = await fetch("/app/api/weekly-recap/latest", { method: "GET", cache: "no-store" });
      if (!response.ok) {
        const raw = await response.text().catch(() => "");
        throw new Error(parseRecapReportError(raw));
      }
      const payload = (await response.json()) as WeeklyRecapReportResponse;
      setWeeklyRecapReport(payload);
    } catch (error) {
      setWeeklyRecapReport(null);
      setWeeklyRecapReportError(error instanceof Error ? error.message : "Unable to load weekly recap.");
    } finally {
      setWeeklyRecapReportLoading(false);
    }
  };

  const handleDailyRun = async (athleteCheckIn?: string): Promise<DailyRunResponse | null> => {
    try {
      const runResponse = await fetch("/app/api/daily/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(athleteCheckIn ? { athlete_check_in: athleteCheckIn } : {}),
        cache: "no-store",
      });
      if (!runResponse.ok) {
        const raw = await runResponse.text().catch(() => "");
        throw new Error(parseApiError(raw, "Daily sync failed"));
      }
      const response = (await runResponse.json()) as DailyRunResponse;
      const firstFocusBlock = response.narrative.today_focus_blocks[0];
      const verdictPreview = firstFocusBlock ? extractContentText(firstFocusBlock.content_html) : null;
      const coachSurfaceUpdate = buildCoachSurfaceFromDailySyncResult(response);

      setDashboardState((previous) => ({
        ...previous,
        status_surface:
          response.narrative.dashboard_kpis.length > 0
            ? {
                kpis: response.narrative.dashboard_kpis,
                source: "daily_update",
                label: "Morning sync",
                updated_at: new Date().toISOString(),
                target_date: previous.athlete_time.today_local_date,
              }
            : previous.status_surface,
        coach_surface: coachSurfaceUpdate ?? previous.coach_surface,
        today_mission: {
          ...previous.today_mission,
          day_override: response.today_override ?? previous.today_mission.day_override,
        },
        daily_sync: {
          ...previous.daily_sync,
          visible: true,
          status: "completed",
          run_id: response.run_id,
          verdict_preview: verdictPreview,
          sources_used: response.sources_used,
          proposal_id: response.proposal_id,
          thread_id: response.thread_id,
          error_message: null,
          gate_target: null,
        },
      }));

      if (response.proposal_id && response.thread_id) {
        updatePendingProposalBanner({
          proposal_id: response.proposal_id,
          thread_id: response.thread_id,
          origin: "daily_update",
          assistant_message: "Coach proposed a plan adjustment.",
        });
      }

      return response;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Daily sync failed";
      try {
        const response = await fetch("/app/api/dashboard/state", {
          method: "GET",
          cache: "no-store",
        });
        if (response.ok) {
          const nextState = (await response.json()) as DashboardStateResponse;
          setDashboardState(nextState);
          return null;
        }
      } catch {
        // Fall back to the local error state when the reconciliation request also fails.
      }
      setDashboardState((previous) => ({
        ...previous,
        daily_sync: {
          ...previous.daily_sync,
          visible: true,
          status: "failed",
          sources_used: [],
          error_message: message,
        },
      }));
      return null;
    }
  };

  const handleWeeklyRecapRun = async (): Promise<CoachTurnResponse | null> => {
    try {
      setWeeklyRecapError(null);
      const response = await runWeeklyRecapAction();
      const report = buildWeeklyRecapReport(response);
      const recapTurn = getRecapTurnPayload(response);
      const threadId = response.thread.id;
      const coachSurfaceUpdate = buildCoachSurfaceFromWeeklyRecap(recapTurn?.recap);

      setDashboardState((previous) => ({
        ...previous,
        coach_surface: coachSurfaceUpdate ?? previous.coach_surface,
        weekly_recap: {
          visible: recapTurn !== null,
          allowed: false,
          status: "completed_this_window",
          thread_id: threadId,
          proposal_id: recapTurn?.recap.proposal_id ?? null,
          follow_up_question: recapTurn?.recap.follow_up_question ?? null,
          summary_preview: resolveRecapSummaryPreview(recapTurn?.recap),
          pending_action: resolveWeeklyRecapPendingAction({
            proposalId: recapTurn?.recap.proposal_id ?? null,
            followUpQuestion: recapTurn?.recap.follow_up_question ?? null,
            athleteResponse: recapTurn?.recap.athlete_response ?? null,
          }),
          can_run: false,
          attention_message: previous.weekly_recap.attention_message,
          gate_target: previous.weekly_recap.gate_target,
        },
      }));

      if (recapTurn?.recap.proposal_id) {
        updatePendingProposalBanner({
          proposal_id: recapTurn.recap.proposal_id,
          thread_id: threadId,
          origin: "weekly_recap",
          assistant_message: "Coach proposed a plan adjustment.",
        });
      }

      if (report) {
        await openWeeklyRecapReport(report);
      }

      return response;
    } catch (error) {
      setWeeklyRecapError(error instanceof Error ? error.message : "Weekly recap failed");
      return null;
    }
  };

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
              dailySyncCompleted={dailySyncState.status === "completed"}
            />
          ) : (
            <FirstRunPanel state={dashboardState.first_run} />
          )}
        </div>

        <div className="flex flex-col gap-4 lg:col-span-2 lg:col-start-4 lg:row-start-2 lg:overflow-hidden">
          <WeeklyRecapWidget
            errorMessage={weeklyRecapError}
            onOpenReport={() => {
              void openWeeklyRecapReport();
            }}
            onRun={handleWeeklyRecapRun}
            state={dashboardState.weekly_recap}
          />
          <DailySyncWidget onRun={handleDailyRun} state={dailySyncState} />
          <SeasonProgress seasonPlan={seasonPlan} nowIso={dashboardState.athlete_time.now_local_iso} />
          <CoachInsight
            onOpenWeeklyRecap={() => {
              void openWeeklyRecapReport();
            }}
            surface={coachSurface}
          />
        </div>

        <div className="lg:col-span-5 lg:row-start-3">
          <WeekStrip weeklyPlan={weeklyPlan} />
        </div>
      </div>

      <WeeklyRecapReportPanel
        errorMessage={weeklyRecapReportError}
        loading={weeklyRecapReportLoading}
        onClose={() => setWeeklyRecapReportOpen(false)}
        open={weeklyRecapReportOpen}
        report={weeklyRecapReport}
      />
    </div>
  );
}
