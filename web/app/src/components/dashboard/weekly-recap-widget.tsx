"use client";

import Link from "next/link";
import { ExternalLink, History, MessageSquareQuote, Sparkles } from "lucide-react";
import { useTransition } from "react";

import type { CoachTurnResponse } from "@/lib/types/coach";
import type { DashboardWeeklyRecapState } from "@/lib/types/dashboard";
import { openCoachThread } from "@/lib/types/ask-about";
import { weeklyRecapActionDescription, weeklyRecapActionLabel, weeklyRecapCoachCta } from "@/lib/types/recap";

type Props = {
  state: DashboardWeeklyRecapState;
  errorMessage?: string | null;
  onRun: () => Promise<CoachTurnResponse | null>;
  onOpenReport: () => void;
};

export default function WeeklyRecapWidget({ state, errorMessage = null, onRun, onOpenReport }: Props) {
  const [isPending, startTransition] = useTransition();
  const showAttention = Boolean(state.attention_message);
  const gateHref = "/app/settings";
  const gateLabel = "Open integration settings";
  const needsFirstConnection = state.attention_message?.startsWith("No training data source connected") ?? false;
  const blockedButtonLabel = needsFirstConnection ? "Connect Source To Run" : "Reconnect To Run";

  if (!state.visible) {
    return null;
  }

  const handleRecap = () => {
    startTransition(async () => {
      await onRun();
    });
  };

  if (state.status === "completed_this_window") {
    return (
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <MessageSquareQuote className="mt-0.5 h-5 w-5 text-[var(--accent-info)]" />
            <div>
              <p className="text-sm font-semibold text-[var(--accent-info)]">Latest Weekly Recap</p>
              <p className="mt-1 text-sm leading-relaxed text-[var(--text-secondary)]">
                {weeklyRecapActionDescription(state.pending_action)}
              </p>
            </div>
          </div>
          <span className="rounded-full border border-sky-400/25 bg-sky-400/12 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-sky-100">
            {weeklyRecapActionLabel(state.pending_action)}
          </span>
        </div>

        {state.summary_preview ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm leading-6 text-[var(--text-primary)]">
            {state.summary_preview}
          </div>
        ) : null}

        {state.follow_up_question && (state.pending_action === "follow_up" || state.pending_action === "follow_up_and_proposal") ? (
          <div className="mt-4 rounded-xl border border-sky-400/20 bg-sky-400/10 px-4 py-3">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-sky-100">Coach follow-up</div>
            <p className="mt-2 text-sm font-medium leading-relaxed text-[var(--text-primary)]">{state.follow_up_question}</p>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent-primary)] px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-110"
            onClick={onOpenReport}
            type="button"
          >
            Open recap
            <ExternalLink className="h-4 w-4" />
          </button>
          {state.thread_id ? (
            <button
              className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--accent-info)] hover:brightness-110"
              onClick={() => {
                if (state.thread_id) {
                  openCoachThread(state.thread_id);
                }
              }}
              type="button"
            >
              {weeklyRecapCoachCta(state.pending_action)}
            </button>
          ) : null}
        </div>
      </section>
    );
  }

  return (
    <section className="relative flex flex-col justify-between overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
      <div className="relative z-10 flex flex-1 flex-col justify-center">
        <div className="mt-2 flex flex-col gap-2">
          <p className="mb-2 text-xs font-semibold text-[var(--text-muted)]">Weekly Tactical Review</p>
          <p className="text-xl font-semibold leading-snug tracking-tight text-[var(--text-primary)] sm:text-2xl">
            It&apos;s time for your Weekly Recap.
          </p>
          <p className="mb-4 text-sm font-medium text-[var(--text-secondary)]">
            Look back at the last 7 days of compliance and adjust the upcoming week&apos;s plan.
          </p>

          {showAttention ? (
            <div className="mb-1 rounded-xl border border-[var(--accent-warning)]/30 bg-[var(--accent-warning)]/8 p-3 text-sm">
              <p className="font-semibold text-[var(--accent-warning)]">{state.attention_message}</p>
              <p className="mt-1 text-[var(--text-secondary)]">
                {state.can_run
                  ? "Weekly recap can still run from your other active training source."
                  : needsFirstConnection
                    ? "Weekly recap is optional for Manual Mode. Connect Strava or WHOOP when you want data-backed reviews."
                    : "Reconnect your training source in Settings before running weekly recap."}
              </p>
              <Link className="mt-2 inline-flex font-semibold text-[var(--accent-warning)] hover:brightness-110" href={gateHref}>
                {gateLabel}
              </Link>
            </div>
          ) : null}

          <button
            className="flex w-full items-center justify-center gap-2 self-start rounded-xl bg-[var(--accent-primary)] px-5 py-3 text-sm font-bold text-white transition hover:brightness-110 disabled:opacity-50 sm:w-auto"
            disabled={isPending || !state.can_run}
            onClick={handleRecap}
            type="button"
          >
            {isPending ? <History className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {isPending ? "Generating Recap..." : !state.can_run ? blockedButtonLabel : "Run Weekly Recap"}
          </button>

          {errorMessage ? <p className="mt-3 text-sm font-medium text-[var(--accent-danger)]">{errorMessage}</p> : null}
        </div>
      </div>
    </section>
  );
}
