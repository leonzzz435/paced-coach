"use client";

import Link from "next/link";
import { CheckCircle2, RefreshCw, Zap } from "lucide-react";
import { useState, useTransition } from "react";

import type { DailyRunResponse, DashboardDailySyncState } from "@/lib/types/dashboard";
import { formatDailySyncSources } from "@/lib/types/dashboard";
import { openCoachThread } from "@/lib/types/ask-about";

type Props = {
  state: DashboardDailySyncState;
  onRun: (athleteCheckIn?: string) => Promise<DailyRunResponse | null>;
};

const CHECK_IN_MAX_LENGTH = 800;

function reviewHref(threadId: string | null): string {
  if (!threadId) return "/app/coach";
  return `/app/coach?thread_id=${encodeURIComponent(threadId)}`;
}

export default function DailySyncWidget({ state, onRun }: Props) {
  const [athleteCheckIn, setAthleteCheckIn] = useState("");
  const [isPending, startTransition] = useTransition();
  const sourcesUsedLabel = formatDailySyncSources(state.sources_used);
  const showAttention = Boolean(state.attention_message);
  const gateHref = "/app/settings";
  const gateLabel = "Open integration settings";
  const needsFirstConnection = state.attention_message?.startsWith("No training data source connected") ?? false;
  const blockedButtonLabel = needsFirstConnection ? "Connect Source To Sync" : "Reconnect To Sync";

  if (!state.visible) {
    return null;
  }

  const handleSync = () => {
    if (!state.can_run) {
      return;
    }
    startTransition(async () => {
      const response = await onRun(athleteCheckIn.trim() || undefined);
      if (response?.proposal_id && response.thread_id) {
        openCoachThread(response.thread_id);
      }
      if (response) {
        setAthleteCheckIn("");
      }
    });
  };

  if (state.status === "completed") {
    return (
      <section className="rounded-2xl border border-[var(--border)] border-l-[3px] border-l-[var(--accent-success)] bg-[var(--surface)] p-5 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--accent-success)]" />
            <p className="text-sm font-semibold text-[var(--accent-success)]">Synced</p>
            {sourcesUsedLabel ? <span className="text-xs text-[var(--text-muted)]">via {sourcesUsedLabel}</span> : null}
          </div>
          {state.proposal_id ? (
            <Link className="shrink-0 text-sm font-semibold text-[var(--accent-success)] hover:brightness-110" href={reviewHref(state.thread_id)}>
              Review in Coach
            </Link>
          ) : null}
        </div>
        {state.verdict_preview ? (
          <p className="mt-2 text-sm font-medium leading-relaxed text-[var(--text-primary)]">{state.verdict_preview}</p>
        ) : null}
      </section>
    );
  }

  return (
    <section className="relative flex flex-col justify-between overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
      <div className="relative z-10 flex flex-1 flex-col justify-center">
        <div className="mt-2 flex flex-col gap-2">
          <p className="text-xl font-semibold leading-snug tracking-tight text-[var(--text-primary)] sm:text-2xl">
            Ready for today&apos;s training?
          </p>
          <p className="mb-4 text-sm font-medium text-[var(--text-secondary)]">
            Run your daily sync to check latest recovery metrics and get today&apos;s tactical adjustments.
          </p>

          <label className="flex flex-col gap-2 text-sm font-semibold text-[var(--text-primary)]">
            Quick check-in <span className="font-normal text-[var(--text-muted)]">(optional)</span>
            <textarea
              className="min-h-24 rounded-xl border border-[var(--border)] bg-[var(--surface-elevated)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--accent-primary)] disabled:opacity-60"
              disabled={!state.can_run || isPending || state.status === "pending"}
              maxLength={CHECK_IN_MAX_LENGTH}
              onChange={(event) => setAthleteCheckIn(event.target.value)}
              placeholder="Sleep, soreness, motivation, pain/illness, available time, desk load..."
              value={athleteCheckIn}
            />
          </label>

          {showAttention ? (
            <div className="mb-1 rounded-xl border border-[var(--accent-warning)]/30 bg-[var(--accent-warning)]/8 p-3 text-sm">
              <p className="font-semibold text-[var(--accent-warning)]">
                {state.attention_message}
              </p>
              <p className="mt-1 text-[var(--text-secondary)]">
                {state.can_run
                  ? "Daily sync can still run from your other active training source."
                  : needsFirstConnection
                    ? "Daily sync is optional for Manual Mode. Connect Strava or WHOOP when you want data-backed adjustments."
                    : "Reconnect your training source in Settings before running daily sync."}
              </p>
              <Link className="mt-2 inline-flex font-semibold text-[var(--accent-warning)] hover:brightness-110" href={gateHref}>
                {gateLabel}
              </Link>
            </div>
          ) : null}

          <button
            className="flex w-full items-center justify-center gap-2 self-start rounded-xl bg-[var(--accent-primary)] px-5 py-3 text-sm font-bold text-white transition hover:brightness-110 disabled:opacity-50 sm:w-auto"
            disabled={!state.can_run || isPending || state.status === "pending"}
            onClick={handleSync}
            type="button"
          >
            {isPending || state.status === "pending" ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Zap className="h-4 w-4" />
            )}
            {isPending || state.status === "pending"
              ? "Syncing metrics..."
              : !state.can_run
                ? blockedButtonLabel
                : state.status === "failed"
                  ? "Retry Daily Sync"
                  : "Run Daily Sync"}
          </button>

          {state.status === "failed" && state.error_message ? (
            <p className="mt-3 text-sm font-medium text-[var(--accent-danger)]">{state.error_message}</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
