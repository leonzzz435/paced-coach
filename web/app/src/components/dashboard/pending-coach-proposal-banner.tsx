"use client";

import Link from "next/link";
import { X } from "lucide-react";

import type { PendingProposalBannerState } from "@/lib/types/dashboard";

type Props = {
  banner: NonNullable<PendingProposalBannerState>;
  onDismiss: () => void;
};

function reviewHref(threadId: string | null): string {
  if (!threadId) return "/app/coach";
  return `/app/coach?thread_id=${encodeURIComponent(threadId)}`;
}

export default function PendingCoachProposalBanner({ banner, onDismiss }: Props) {
  const label = banner.origin === "weekly_recap" ? "Coach proposed a training block adjustment." : "Coach proposed a plan adjustment.";

  return (
    <div className="flex items-start justify-between gap-3 rounded-2xl border border-[var(--border)] border-l-[3px] border-l-[var(--accent-warning)] bg-[var(--accent-warning)]/8 px-4 py-3 shadow-sm">
      <div className="min-w-0">
        <div className="text-xs font-semibold text-[var(--accent-warning)]">Pending Coach Proposal</div>
        <p className="mt-1 text-sm font-medium text-[var(--text-primary)]">{label}</p>
        <Link className="mt-2 inline-flex text-sm font-semibold text-[var(--accent-warning)] hover:brightness-110" href={reviewHref(banner.thread_id)}>
          Review in Coach
        </Link>
      </div>
      <button
        aria-label="Dismiss proposal banner"
        className="rounded-full p-1 text-[var(--text-muted)] transition hover:bg-[var(--surface-elevated)] hover:text-[var(--text-primary)]"
        onClick={onDismiss}
        type="button"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
