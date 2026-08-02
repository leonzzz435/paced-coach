import type { CoachQuota } from "@/lib/types/quota";

import {
  type BusyAction,
  COACH_NAME,
  COACH_QUICK_PROMPTS,
  remainingText,
  showLowQuotaWarning,
} from "./coach-inbox-parts";

type CoachInboxComposerBarProps = {
  error: string | null;
  quota: CoachQuota | null;
  quotaBlocked: boolean;
  canSendMessage: boolean;
  coachGateMessage: string | null;
  coachGateTarget: "settings" | null;
  isConversationView: boolean;
  selectedThreadStatus: "active" | "archived";
  busyAction: BusyAction | null;
  composerDisabled: boolean;
  listComposerDisabled: boolean;
  input: string;
  onInputChange: (value: string) => void;
  onSendMessage: (forceNewThread?: boolean) => void;
  onQuickPromptSelect: (value: string) => void;
};

export default function CoachInboxComposerBar({
  error,
  quota,
  quotaBlocked,
  canSendMessage,
  coachGateMessage,
  coachGateTarget,
  isConversationView,
  selectedThreadStatus,
  busyAction,
  composerDisabled,
  listComposerDisabled,
  input,
  onInputChange,
  onSendMessage,
  onQuickPromptSelect,
}: CoachInboxComposerBarProps) {
  const composerLocked = isConversationView ? composerDisabled : listComposerDisabled;
  const blockedSendLabel = coachGateTarget === "settings" ? "Coach unavailable" : "Try Tomorrow";

  return (
    <footer className="border-t border-white/10 bg-white/[0.03] px-4 py-3 backdrop-blur">
      {error ? <div className="mb-3 rounded-2xl border border-red-400/25 bg-red-500/10 px-3 py-2 text-xs text-red-200">{error}</div> : null}
      {quotaBlocked ? (
        <div className="mb-3 rounded-2xl border border-amber-400/25 bg-amber-400/12 px-3 py-2 text-xs text-amber-100">
          Daily coach message limit reached. The local safety window resets tomorrow.
        </div>
      ) : null}
      {isConversationView && selectedThreadStatus === "archived" ? (
        <div className="mb-3 rounded-2xl border border-white/10 bg-white/[0.05] px-3 py-2 text-xs text-[var(--text-secondary)]">
          This thread is archived. Return to your thread list to start a new conversation.
        </div>
      ) : null}
      {coachGateMessage ? (
        <div className="mb-3 rounded-2xl border border-amber-400/25 bg-amber-400/12 px-3 py-2 text-xs text-amber-100">
          <div>{coachGateMessage}</div>
        </div>
      ) : null}

      {showLowQuotaWarning(quota) ? (
        <div className="mb-2 text-right">
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] text-[var(--text-secondary)]">{remainingText(quota)}</span>
        </div>
      ) : null}

      {isConversationView ? (
        <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-2 shadow-[0_8px_24px_rgba(2,6,23,0.18)]">
          <textarea
            className="min-h-[68px] w-full resize-none rounded-[1.1rem] border border-white/10 bg-[var(--surface-elevated)]/88 px-4 py-3 text-sm leading-6 text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-emerald-400/35 focus:ring-2 focus:ring-emerald-400/10"
            disabled={composerDisabled}
            placeholder={`Ask ${COACH_NAME} about training, recovery, scheduling, or race prep...`}
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                onSendMessage();
              }
            }}
          />
          <div className="flex items-center justify-between gap-2 pt-1">
            <div className="text-[10px] text-[var(--text-muted)]">Enter sends · Shift+Enter new line</div>
            <div className="flex gap-2">
              <button
                className="rounded-2xl bg-[linear-gradient(135deg,rgba(56,189,248,0.92),rgba(16,185,129,0.88))] px-4 py-2 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:opacity-60"
                disabled={composerDisabled || !canSendMessage || !input.trim()}
                type="button"
                onClick={() => onSendMessage()}
              >
                {busyAction === "send" ? "Sending..." : !canSendMessage ? blockedSendLabel : "Send message"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-2 shadow-[0_8px_24px_rgba(2,6,23,0.18)]">
          <div className="flex flex-wrap gap-1.5 px-2 pb-2">
            {COACH_QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] font-medium text-[var(--text-primary)] shadow-[0_8px_18px_rgba(2,6,23,0.14)] transition hover:bg-white/[0.08] disabled:opacity-50"
                disabled={composerLocked}
                type="button"
                onClick={() => onQuickPromptSelect(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
          <textarea
            className="min-h-[52px] w-full resize-none rounded-[1.1rem] border border-white/10 bg-[var(--surface-elevated)]/88 px-4 py-3 text-sm leading-6 text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-emerald-400/35 focus:ring-2 focus:ring-emerald-400/10"
            disabled={listComposerDisabled}
            placeholder={`Start a conversation with ${COACH_NAME}...`}
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                onSendMessage(true);
              }
            }}
          />
          <div className="flex items-center justify-between gap-2 pt-1">
            <div className="text-[10px] text-[var(--text-muted)]">Enter sends</div>
            <button
              className="rounded-2xl bg-[linear-gradient(135deg,rgba(56,189,248,0.92),rgba(16,185,129,0.88))] px-4 py-2 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:opacity-60"
              disabled={listComposerDisabled || !canSendMessage || !input.trim()}
              type="button"
              onClick={() => onSendMessage(true)}
            >
              {busyAction === "send" ? "Sending..." : !canSendMessage ? blockedSendLabel : "Start thread"}
            </button>
          </div>
        </div>
      )}
    </footer>
  );
}
