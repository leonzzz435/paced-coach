import type { CoachThreadSignals } from "@/lib/coach/inbox";
import type { CoachThreadListItem } from "@/lib/types/coach";

import { COACH_QUICK_PROMPTS, relativeTime, threadTitle } from "./coach-inbox-parts";

type CoachInboxThreadListViewProps = {
  threadsLoading: boolean;
  activeThreads: CoachThreadListItem[];
  archivedThreads: CoachThreadListItem[];
  visibleArchivedThreads: CoachThreadListItem[];
  threadSignals: Record<string, CoachThreadSignals>;
  showAllArchived: boolean;
  onToggleArchived: () => void;
  onOpenThread: (threadId: string) => void;
  onQuickPromptSelect: (value: string) => void;
};

function sourceTheme(signals: CoachThreadSignals | undefined): {
  badge: string | null;
  badgeClassName: string;
  cardClassName: string;
} {
  if (signals?.source === "weekly_recap") {
    return {
      badge: "Weekly recap",
      badgeClassName: "border-sky-400/25 bg-sky-400/12 text-sky-100",
      cardClassName: "border-sky-400/25 bg-[linear-gradient(180deg,rgba(56,189,248,0.12),rgba(15,23,42,0.94))]",
    };
  }
  if (signals?.source === "proactive") {
    return {
      badge: "Coach alert",
      badgeClassName: "border-amber-400/25 bg-amber-400/12 text-amber-100",
      cardClassName: "border-amber-400/25 bg-[linear-gradient(180deg,rgba(245,158,11,0.12),rgba(15,23,42,0.94))]",
    };
  }
  return {
    badge: null,
    badgeClassName: "",
    cardClassName: "border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))]",
  };
}

function followUpText(signals: CoachThreadSignals | undefined): string | null {
  if (!signals?.hasPendingWork) return null;
  if (signals.hasPendingProposal && signals.hasPendingFollowUp) {
    return `${signals.pendingCount} decisions waiting on you`;
  }
  if (signals.hasPendingProposal) {
    return "A plan change is ready for approval";
  }
  if (signals.hasPendingFollowUp) {
    return "A follow-up question is waiting";
  }
  return `${signals.pendingCount} items need attention`;
}

function ThreadCard({
  item,
  signals,
  archived = false,
  onOpenThread,
}: {
  item: CoachThreadListItem;
  signals: CoachThreadSignals | undefined;
  archived?: boolean;
  onOpenThread: (threadId: string) => void;
}) {
  const theme = sourceTheme(signals);

  return (
    <button
      className={`w-full rounded-[1.35rem] border p-4 text-left shadow-[0_10px_28px_rgba(2,6,23,0.18)] transition hover:-translate-y-0.5 hover:shadow-[0_16px_34px_rgba(2,6,23,0.24)] ${theme.cardClassName} ${
        archived ? "opacity-90" : ""
      }`}
      type="button"
      onClick={() => onOpenThread(item.id)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold tracking-[-0.01em] text-[var(--text-primary)]">
            {threadTitle(item.id, item.title, signals)}
          </div>
          <div className="mt-1 text-xs text-[var(--text-muted)]">
            {archived ? "Last active" : "Updated"} {relativeTime(item.updated_at)}
          </div>
        </div>
        {signals?.hasPendingWork && !archived ? <span className="mt-1 h-2.5 w-2.5 rounded-full bg-rose-500" /> : null}
      </div>

      {(theme.badge || followUpText(signals)) ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {theme.badge ? (
            <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${theme.badgeClassName}`}>
              {theme.badge}
            </span>
          ) : null}
          {followUpText(signals) ? (
            <span className="text-[11px] font-medium text-rose-200">{followUpText(signals)}</span>
          ) : null}
        </div>
      ) : null}

      {signals?.previewText ? (
        <div className="mt-3 line-clamp-2 text-sm leading-6 text-[var(--text-secondary)]">{signals.previewText}</div>
      ) : (
        <div className="mt-3 text-sm leading-6 text-[var(--text-muted)]">Open this thread to continue the conversation.</div>
      )}
    </button>
  );
}

export default function CoachInboxThreadListView({
  threadsLoading,
  activeThreads,
  archivedThreads,
  visibleArchivedThreads,
  threadSignals,
  showAllArchived,
  onToggleArchived,
  onOpenThread,
  onQuickPromptSelect,
}: CoachInboxThreadListViewProps) {
  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      {threadsLoading ? <div className="px-1 text-xs text-[var(--text-muted)]">Loading conversations...</div> : null}

      {!threadsLoading && activeThreads.length === 0 && archivedThreads.length === 0 ? (
        <div className="rounded-[1.6rem] border border-emerald-400/25 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.12),transparent_40%),linear-gradient(180deg,rgba(16,185,129,0.06),rgba(15,23,42,0.92))] p-5 shadow-[0_16px_40px_rgba(2,6,23,0.22)]">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-300">Start here</div>
          <div className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[var(--text-primary)]">Open a focused coaching thread.</div>
          <div className="mt-2 max-w-xl text-sm leading-6 text-[var(--text-secondary)]">
            Use a prompt below or type your own question about recovery, schedule changes, or race planning.
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {COACH_QUICK_PROMPTS.slice(0, 3).map((prompt) => (
              <button
                key={prompt}
                className="rounded-full border border-emerald-400/25 bg-emerald-400/12 px-3 py-1.5 text-xs font-medium text-emerald-100 shadow-[0_10px_20px_rgba(2,6,23,0.14)] transition hover:bg-emerald-400/18"
                type="button"
                onClick={() => onQuickPromptSelect(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {activeThreads.length > 0 ? (
        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3 px-1">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Active threads</div>
            <div className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] text-[var(--text-secondary)]">
              {activeThreads.length} open
            </div>
          </div>
          <div className="space-y-3">
            {activeThreads.map((item) => (
              <ThreadCard
                key={item.id}
                item={item}
                signals={threadSignals[item.id]}
                onOpenThread={onOpenThread}
              />
            ))}
          </div>
        </section>
      ) : null}

      {archivedThreads.length > 0 ? (
        <section className={`${activeThreads.length > 0 ? "mt-6" : ""} space-y-3`}>
          <div className="flex items-center justify-between gap-3 border-t border-white/10 px-1 pt-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">Past threads</div>
            <div className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] text-[var(--text-secondary)]">
              {archivedThreads.length} archived
            </div>
          </div>

          <div className="space-y-3">
            {visibleArchivedThreads.map((item) => (
              <ThreadCard
                key={item.id}
                archived
                item={item}
                signals={threadSignals[item.id]}
                onOpenThread={onOpenThread}
              />
            ))}
          </div>

          {archivedThreads.length > 3 ? (
            <button
              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-[var(--text-primary)] shadow-[0_10px_20px_rgba(2,6,23,0.14)] transition hover:bg-white/[0.08]"
              type="button"
              onClick={onToggleArchived}
            >
              {showAllArchived ? "Show fewer past threads" : `Show ${archivedThreads.length - 3} more past threads`}
            </button>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
