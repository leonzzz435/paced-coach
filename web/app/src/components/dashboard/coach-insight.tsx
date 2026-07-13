"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

import type { DashboardCoachSurfaceState } from "@/lib/types/dashboard";

type Props = {
  surface: DashboardCoachSurfaceState;
  onOpenWeeklyRecap?: () => void;
  allowPlanLink?: boolean;
};

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
});

function sourceLabel(source: DashboardCoachSurfaceState["source"]): string | null {
  if (source === "daily_sync") return "Daily Sync";
  if (source === "weekly_recap") return "Weekly Recap";
  if (source === "analysis") return "Plan Analysis";
  return null;
}

function formatFreshness(updatedAt: string | null): string | null {
  if (!updatedAt) return null;
  const parsed = new Date(updatedAt);
  if (Number.isNaN(parsed.getTime())) return null;

  const diffMs = Date.now() - parsed.getTime();
  if (diffMs < 90_000) return "Updated just now";
  if (diffMs < 60 * 60 * 1000) {
    return `Updated ${Math.max(1, Math.round(diffMs / 60_000))} min ago`;
  }
  if (diffMs < 24 * 60 * 60 * 1000) {
    return `Updated ${Math.max(1, Math.round(diffMs / (60 * 60 * 1000)))}h ago`;
  }
  return `Updated ${DATE_FORMATTER.format(parsed)}`;
}

function sourceBadgeClasses(source: DashboardCoachSurfaceState["source"]): string {
  if (source === "daily_sync") {
    return "border-emerald-400/20 bg-emerald-400/10 text-emerald-100";
  }
  if (source === "weekly_recap") {
    return "border-sky-400/20 bg-sky-400/10 text-sky-100";
  }
  if (source === "analysis") {
    return "border-violet-400/20 bg-violet-400/10 text-violet-100";
  }
  return "border-white/10 bg-white/[0.04] text-[var(--text-muted)]";
}

export default function CoachInsight({ surface, onOpenWeeklyRecap, allowPlanLink = true }: Props) {
  const source = sourceLabel(surface.source);
  const freshness = formatFreshness(surface.updated_at);
  const hasGuidance = Boolean(surface.primary_text || surface.secondary_text);

  if (!hasGuidance) {
    return (
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm">
        <div className="mb-3 flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full border border-[var(--accent-coach)]/20 bg-[var(--accent-coach)]/10 text-[var(--accent-coach)] shadow-sm">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <span className="text-xs font-semibold text-[var(--accent-coach)]">Coach Guidance</span>
        </div>
        <p className="text-base font-semibold leading-snug tracking-tight text-[var(--text-primary)]">
          Ready to plan your next block?
        </p>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Generate a plan or ask the coach about your current calendar to get guidance here.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full border border-[var(--accent-coach)]/20 bg-[var(--accent-coach)]/10 text-[var(--accent-coach)] shadow-sm">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <div>
            <div className="text-xs font-semibold text-[var(--accent-coach)]">Coach Guidance</div>
            {freshness ? <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">{freshness}</div> : null}
          </div>
        </div>

        {source ? (
          <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${sourceBadgeClasses(surface.source)}`}>
            {source}
          </span>
        ) : null}
      </div>

      {surface.primary_text ? (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-elevated)] px-4 py-3 shadow-sm">
          {surface.primary_label ? (
            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
              {surface.primary_label}
            </div>
          ) : null}
          <p className="mt-1 text-sm font-semibold leading-relaxed text-[var(--text-primary)]">
            {surface.primary_text}
          </p>
        </div>
      ) : null}

      {surface.secondary_text ? (
        <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
          {surface.secondary_text}
        </p>
      ) : null}

      {surface.source === "weekly_recap" && onOpenWeeklyRecap ? (
        <div className="mt-4">
          <button
            className="inline-flex items-center gap-2 text-sm font-semibold text-sky-200 transition hover:text-sky-100"
            onClick={onOpenWeeklyRecap}
            type="button"
          >
            Open recap
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      ) : null}

      {surface.source === "analysis" && allowPlanLink ? (
        <div className="mt-4">
          <Link
            className="inline-flex items-center gap-2 text-sm font-semibold text-violet-200 transition hover:text-violet-100"
            href="/app/plan"
          >
            Open plan
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      ) : null}
    </section>
  );
}
