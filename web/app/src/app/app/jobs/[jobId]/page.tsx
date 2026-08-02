"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import PlanViewer from "@/components/plan-viewer/plan-viewer";
import type { SeasonPlanV3, WeeklyPlanV3 } from "@/components/plan-viewer/types";
import CoachClarificationCard from "@/components/jobs/coach-clarification-card";
import type { UiAnalysis, UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";

type JobStatus = {
  progress_steps?: ProgressStep[];
  current_step?: string | null;
  job_id: string;
  status: string;
  created_at: string;
  completed_at?: string | null;
  cost_usd?: number | null;
  tokens_used?: number | null;
  interrupt?: {
    question: string;
    reason_markdown: string;
    requested_field: string;
  } | null;
};

type ProgressStep = {
  node: string;
  label: string;
  status: "pending" | "active" | "completed";
  started_at?: string | null;
  completed_at?: string | null;
};

type StageStatus = "pending" | "active" | "completed" | "failed";

type ProgressStage = {
  key: string;
  label: string;
  description: string;
  nodes: string[];
};

type ProgressStageView = ProgressStage & {
  status: StageStatus;
  completedCount: number;
  detail: string;
};

type JobResults = {
  job_id: string;
  status: string;
  result?: {
    analysis_blocks?: UiAnalysis | null;
    weekly_plan_blocks?: UiWeeklyPlan | WeeklyPlanV3 | null;
    season_plan_blocks?: UiSeasonPlan | SeasonPlanV3 | null;
  } | null;
  error_message?: string | null;
};

const PROGRESS_STAGES: ProgressStage[] = [
  {
    key: "context",
    label: "Understand You",
    description: "Reading your profile, goals, calendar, constraints, and coaching memory.",
    nodes: ["head_coach_understanding_context"],
  },
  {
    key: "strategy",
    label: "Design Strategy",
    description: "Building the season direction around what you declared.",
    nodes: ["head_coach_designing_strategy"],
  },
  {
    key: "review",
    label: "Review Constraints",
    description: "Checking that the plan is coherent, safe, and realistic.",
    nodes: ["head_coach_reviewing_constraints", "head_coach_awaiting_input"],
  },
  {
    key: "execution",
    label: "Build 28 Days",
    description: "Turning the strategy into a complete daily execution block.",
    nodes: ["head_coach_building_execution_block"],
  },
  {
    key: "save",
    label: "Save Plan",
    description: "Publishing the roadmap and execution block to your local app.",
    nodes: ["head_coach_saving_plan"],
  },
];

function stageStatusLabel(stageStatus: StageStatus): string {
  if (stageStatus === "active") return "In progress";
  if (stageStatus === "completed") return "Completed";
  if (stageStatus === "failed") return "Failed";
  return "Pending";
}

function summarizeProgressStages(progressSteps: ProgressStep[], jobStatus: string | null | undefined): ProgressStageView[] {
  const stepsByNode = new Map(progressSteps.map((step) => [step.node, step]));
  const stages: ProgressStageView[] = PROGRESS_STAGES.map((stage) => {
    const matchedSteps = stage.nodes
      .map((nodeName) => stepsByNode.get(nodeName))
      .filter((step): step is ProgressStep => Boolean(step));
    const completedCount = matchedSteps.filter((step) => step.status === "completed").length;
    const activeStep = matchedSteps.find((step) => step.status === "active");
    const totalCount = stage.nodes.length;

    let status: StageStatus = "pending";
    if (completedCount === totalCount && totalCount > 0) status = "completed";
    else if (activeStep || completedCount > 0) status = "active";

    let detail = `${completedCount}/${totalCount} tasks complete`;
    if (activeStep) detail = activeStep.label;
    if (status === "pending") detail = "Queued";
    if (status === "completed") detail = "Done";

    return {
      ...stage,
      status,
      completedCount,
      detail,
    };
  });

  if (jobStatus === "pending" || jobStatus === "running" || jobStatus === "cancellation_requested") {
    const hasActive = stages.some((stage) => stage.status === "active");
    if (!hasActive) {
      const firstPendingIndex = stages.findIndex((stage) => stage.status !== "completed");
      if (firstPendingIndex >= 0) {
        stages[firstPendingIndex] = {
          ...stages[firstPendingIndex],
          status: "active",
          detail: "In progress",
        };
      }
    }
  }

  if (jobStatus === "failed") {
    let failedIndex = stages.findIndex((stage) => stage.status === "active");
    if (failedIndex < 0) {
      failedIndex = stages.findIndex(
        (stage) => stage.completedCount > 0 && stage.completedCount < stage.nodes.length,
      );
    }
    if (failedIndex < 0) {
      failedIndex = stages.findIndex((stage) => stage.status === "pending");
    }
    if (failedIndex >= 0) {
      stages[failedIndex] = {
        ...stages[failedIndex],
        status: "failed",
        detail: "Generation stopped before this stage completed.",
      };
    }
  }

  return stages;
}

function overallProgressPercent(stages: ProgressStageView[]): number {
  if (stages.length === 0) return 0;
  const completedStages = stages.filter((stage) => stage.status === "completed").length;
  const hasActiveStage = stages.some((stage) => stage.status === "active");
  const partialStageCredit = hasActiveStage ? 0.5 : 0;
  const ratio = (completedStages + partialStageCredit) / stages.length;
  return Math.max(0, Math.min(100, Math.round(ratio * 100)));
}

function stageToneClasses(stageStatus: StageStatus): {
  card: string;
  dot: string;
  badge: string;
} {
  switch (stageStatus) {
    case "failed":
      return {
        card: "border-rose-400/30 bg-rose-500/10 shadow-[0_18px_40px_rgba(244,63,94,0.10)]",
        dot: "border border-rose-400/35 bg-rose-500/18 text-rose-100",
        badge: "border border-rose-400/25 bg-rose-500/15 text-rose-200",
      };
    case "completed":
      return {
        card: "border-emerald-400/25 bg-emerald-500/10 shadow-[0_18px_40px_rgba(34,197,94,0.08)]",
        dot: "border border-emerald-400/35 bg-emerald-500/20 text-emerald-100",
        badge: "border border-emerald-400/25 bg-emerald-500/15 text-emerald-200",
      };
    case "active":
      return {
        card: "border-sky-400/30 bg-sky-500/10 shadow-[0_18px_40px_rgba(59,130,246,0.12)] ring-1 ring-sky-400/15",
        dot: "border border-sky-400/35 bg-sky-500/18 text-sky-100",
        badge: "border border-sky-400/25 bg-sky-500/15 text-sky-200",
      };
    default:
      return {
        card: "border-[var(--border)] bg-[var(--surface)]/88",
        dot: "border border-[var(--border-accent)] bg-[var(--surface-elevated)] text-[var(--text-secondary)]",
        badge: "border border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--text-secondary)]",
      };
  }
}

export default function JobPage({ params }: { params: { jobId: string } }) {
  const routeParams = useParams<{ jobId: string }>();
  const jobId = routeParams?.jobId ?? params.jobId;
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [results, setResults] = useState<JobResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelState, setCancelState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [cancelMessage, setCancelMessage] = useState<string | null>(null);
  const [pollGeneration, setPollGeneration] = useState(0);
  const resumeRecoveryUntilRef = useRef(0);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;
    let authRetries = 0;
    const MAX_AUTH_RETRIES = 3;

    async function poll() {
      try {
        const res = await fetch(`/app/api/analysis/${jobId}`, { cache: "no-store" });
        if (res.status === 401) {
          authRetries++;
          if (authRetries > MAX_AUTH_RETRIES) {
            throw new Error("Session expired. Please refresh the page to continue.");
          }
          if (!cancelled) timer = setTimeout(poll, 2000);
          return;
        }
        if (!res.ok) throw new Error(await res.text());
        authRetries = 0;
        const s = (await res.json()) as JobStatus;
        if (cancelled) return;
        setError(null);
        setStatus(s);

        if (s.status === "completed" || s.status === "failed") {
          const r = await fetch(`/app/api/analysis/${jobId}/results`, { cache: "no-store" });
          if (r.status === 401) {
            authRetries++;
            if (authRetries > MAX_AUTH_RETRIES) {
              throw new Error("Session expired. Please refresh the page to continue.");
            }
            if (!cancelled) timer = setTimeout(poll, 2000);
            return;
          }
          if (!r.ok) throw new Error(await r.text());
          const data = (await r.json()) as JobResults;
          if (!cancelled) setResults(data);
          return;
        }

        if (s.status === "cancelled") {
          return;
        }

        if (s.status === "awaiting_input") {
          if (Date.now() < resumeRecoveryUntilRef.current) {
            timer = setTimeout(poll, 1000);
          }
          return;
        }

        resumeRecoveryUntilRef.current = 0;

        timer = setTimeout(poll, 2000);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to fetch status");
          if (Date.now() < resumeRecoveryUntilRef.current) {
            timer = setTimeout(poll, 2000);
          }
        }
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId, pollGeneration]);

  const canCancel =
    status?.status === "pending" ||
    status?.status === "running" ||
    status?.status === "awaiting_input" ||
    status?.status === "cancellation_requested";

  async function onCancel() {
    setCancelState("sending");
    setCancelMessage(null);
    try {
      const res = await fetch(`/app/api/analysis/${jobId}/cancel`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const cancelledStatus = (await res.json()) as Partial<JobStatus>;
      setStatus((current) =>
        current
          ? {
              ...current,
              ...cancelledStatus,
              status: cancelledStatus.status ?? "cancellation_requested",
              interrupt: null,
            }
          : current,
      );
      setCancelState("sent");
      setCancelMessage("Cancellation requested.");
    } catch (e) {
      setCancelState("error");
      setCancelMessage(e instanceof Error ? e.message : "Failed to request cancellation");
    }
  }

  const hasBlocks =
    results?.result?.analysis_blocks ||
    results?.result?.season_plan_blocks ||
    results?.result?.weekly_plan_blocks;
  const progressSteps = useMemo(() => status?.progress_steps ?? [], [status?.progress_steps]);
  const stageViews = useMemo(
    () => summarizeProgressStages(progressSteps, status?.status),
    [progressSteps, status?.status],
  );
  const showProgress = progressSteps.length > 0 || stageViews.some((stage) => stage.status !== "pending");
  const progressPercent = useMemo(() => overallProgressPercent(stageViews), [stageViews]);
  const completedStages = stageViews.filter((stage) => stage.status === "completed").length;
  const barColorClass =
    status?.status === "failed"
      ? "bg-rose-500"
      : status?.status === "cancelled" || status?.status === "cancellation_requested"
        ? "bg-amber-500"
        : "bg-gradient-to-r from-sky-500 to-emerald-500";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Job</h1>
        <Link className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]" href="/app">
          Back
        </Link>
      </div>

      {error ? (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-red-400">{error}</div>
      ) : null}

      {status?.status === "awaiting_input" && status.interrupt ? (
        <CoachClarificationCard
          jobId={jobId}
          clarification={status.interrupt}
          onResumed={() => {
            setStatus((current) => (current ? { ...current, status: "pending", interrupt: null } : current));
          }}
          onStatusRecovery={() => {
            setError(null);
            resumeRecoveryUntilRef.current = Date.now() + 10_000;
            setPollGeneration((current) => current + 1);
          }}
        />
      ) : null}

      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--text-primary)] space-y-1">
        <div>
          <span className="font-medium">ID:</span> {jobId}
        </div>
        <div>
          <span className="font-medium">Status:</span> {status?.status ?? "loading..."}
        </div>
        {status?.current_step ? (
          <div>
            <span className="font-medium">Current step:</span> {status.current_step}
          </div>
        ) : null}
        {status?.cost_usd != null ? (
          <div>
            <span className="font-medium">Cost:</span> ${status.cost_usd}
          </div>
        ) : null}
        {status?.tokens_used != null ? (
          <div>
            <span className="font-medium">Tokens:</span> {status.tokens_used}
          </div>
        ) : null}
        <div className="pt-2 flex items-center gap-3">
          <button
            className="rounded-xl border border-[var(--border)] bg-[var(--surface-elevated)] px-3 py-1.5 text-sm font-medium text-[var(--text-primary)] transition hover:border-[var(--border-accent)] hover:bg-white/[0.04] disabled:opacity-60"
            disabled={!canCancel || cancelState === "sending"}
            type="button"
            onClick={() => onCancel()}
          >
            {cancelState === "sending" ? "Cancelling..." : "Cancel generation"}
          </button>
          {cancelMessage ? <span className="text-sm text-[var(--text-secondary)]">{cancelMessage}</span> : null}
        </div>
      </div>

      {showProgress ? (
        <div className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[linear-gradient(180deg,rgba(26,31,46,0.96),rgba(14,19,32,0.98))] p-4 shadow-[0_20px_60px_rgba(2,6,23,0.22)] sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-sm font-semibold text-[var(--text-primary)]">Job progress</div>
              <div className="text-xs text-[var(--text-secondary)]">{stageViews.length} clear coaching stages</div>
            </div>
            <div className="rounded-full border border-[var(--border)] bg-[var(--surface-elevated)] px-2.5 py-1 text-xs font-semibold text-[var(--text-primary)] shadow-sm">
              {completedStages}/{stageViews.length} complete
            </div>
          </div>

          <div className="mt-4 h-2 overflow-hidden rounded-full border border-white/6 bg-[var(--surface-elevated)]">
            <div
              className={`h-full transition-all duration-500 ease-out shadow-[0_0_20px_rgba(56,189,248,0.25)] ${barColorClass}`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {stageViews.map((stage, index) => {
              const isCompleted = stage.status === "completed";
              const tone = stageToneClasses(stage.status);

              return (
                <div key={stage.key} className={`rounded-2xl border p-4 ${tone.card}`}>
                  <div className="flex items-start gap-3">
                    <span className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold shadow-sm ${tone.dot}`}>
                      {isCompleted ? "OK" : index + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-[var(--text-primary)]">{stage.label}</p>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${tone.badge}`}
                        >
                          {stageStatusLabel(stage.status)}
                        </span>
                      </div>
                      <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">{stage.description}</p>
                      <p className="mt-2 text-xs font-medium text-[var(--text-primary)]">{stage.detail}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {results?.error_message ? (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-red-400">
          {results.error_message}
        </div>
      ) : null}

      {status?.status === "cancelled" ? (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--text-primary)]">
          This plan generation was cancelled.
        </div>
      ) : null}

      {status?.status === "completed" && results && !hasBlocks && !results.error_message ? (
        <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 p-4 text-sm text-amber-100" role="status">
          Generation completed, but no renderable plan artifact was returned. Your previously saved plan is unchanged.
        </div>
      ) : null}

      {hasBlocks ? (
        <PlanViewer
          analysis={results?.result?.analysis_blocks ?? undefined}
          seasonPlan={results?.result?.season_plan_blocks ?? undefined}
          weeklyPlan={results?.result?.weekly_plan_blocks ?? undefined}
        />
      ) : null}
    </div>
  );
}
