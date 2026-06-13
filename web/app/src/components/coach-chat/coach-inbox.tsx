"use client";

import { useCallback } from "react";

import type { CoachThreadSignals } from "@/lib/coach/inbox";
import type { CoachTurnUiContext } from "@/lib/types/coach";

import CoachInboxComposerBar from "./coach-inbox-composer-bar";
import CoachInboxConversationView from "./coach-inbox-conversation-view";
import {
  COACH_LABEL,
  COACH_NAME,
  CoachAvatar,
  remainingText,
} from "./coach-inbox-parts";
import CoachInboxThreadListView from "./coach-inbox-thread-list-view";
import { useCoachInbox } from "./use-coach-inbox";

type CoachInboxProps = {
  mode?: "panel" | "embedded";
  active?: boolean;
  onBadgeCountChange?: (count: number) => void;
  prefillMessage?: string | null;
  prefillContext?: CoachTurnUiContext | null;
  onPrefillConsumed?: () => void;
  initialThreadId?: string | null;
  onRequestClose?: () => void;
};

function pendingActionLabel(selectedSignals: CoachThreadSignals | null): string | null {
  if (!selectedSignals?.hasPendingWork) return null;
  if (selectedSignals.hasPendingProposal && selectedSignals.hasPendingFollowUp) return "Reply + review";
  if (selectedSignals.hasPendingProposal) return "Plan adjustment pending";
  if (selectedSignals.hasPendingFollowUp) return "Reply needed";
  return "Awaiting action";
}

export default function CoachInbox({
  mode = "panel",
  active = true,
  onBadgeCountChange,
  prefillMessage = null,
  prefillContext = null,
  onPrefillConsumed,
  initialThreadId = null,
  onRequestClose,
}: CoachInboxProps) {
  const {
    loading,
    threadsLoading,
    thread,
    threadSignals,
    selectedThreadId,
    selectedThreadStatus,
    selectedSignals,
    selectedThreadTitle,
    activeThreads,
    archivedThreads,
    visibleArchivedThreads,
    setView,
    showAllArchived,
    setShowAllArchived,
    confirmingArchive,
    setConfirmingArchive,
    error,
    input,
    setInput,
    busyAction,
    busyProposalId,
    liveStatusEvent,
    optimisticAthleteMessage,
    proposalRejectReasons,
    setProposalRejectReason,
    quota,
    quotaBlocked,
    canSendMessage,
    coachGateMessage,
    coachGateTarget,
    threadCanTriggerRecap,
    trainingProviderMessage,
    recapGateTarget,
    composerDisabled,
    listComposerDisabled,
    isConversationView,
    messagesEndRef,
    messageRefs,
    startNewTopic,
    openThread,
    closeSelectedThread,
    sendMessage,
    triggerRecap,
    acceptProposal,
    rejectProposal,
    trackCoachEvent,
  } = useCoachInbox({
    active,
    onBadgeCountChange,
    prefillMessage,
    prefillContext,
    onPrefillConsumed,
    initialThreadId,
  });

  const panelClassName =
    mode === "embedded"
      ? "h-full overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.94),rgba(15,23,42,0.9))] shadow-[0_24px_72px_rgba(2,6,23,0.24)] backdrop-blur"
      : "h-full w-full overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.16),transparent_36%),radial-gradient(circle_at_bottom_right,_rgba(14,165,233,0.16),transparent_32%),linear-gradient(180deg,rgba(15,23,42,0.98),rgba(15,23,42,0.94))]";

  const applyQuickPrompt = useCallback(
    (prompt: string) => {
      setInput(prompt);
    },
    [setInput]
  );

  return (
    <div className={panelClassName}>
      <div className="flex h-full flex-col">
        {isConversationView ? (
          <header className="border-b border-white/10 bg-white/[0.03] px-4 py-3 backdrop-blur">
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-start gap-3">
                <button
                  className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-sm font-semibold text-[var(--text-primary)] shadow-[0_10px_24px_rgba(2,6,23,0.18)] transition hover:bg-white/[0.08]"
                  disabled={busyAction !== null}
                  type="button"
                  onClick={() => setView("thread_list")}
                >
                  ←
                </button>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3">
                    <CoachAvatar size="md" />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="min-w-0 truncate text-base font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
                          {selectedThreadTitle}
                        </div>
                        {selectedSignals?.source === "weekly_recap" ? (
                          <span className="rounded-full border border-sky-400/25 bg-sky-400/12 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-sky-100">
                            Weekly recap
                          </span>
                        ) : null}
                        {selectedSignals?.source === "proactive" ? (
                          <span className="rounded-full border border-amber-400/25 bg-amber-400/12 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-100">
                            Coach alert
                          </span>
                        ) : null}
                        {pendingActionLabel(selectedSignals) ? (
                          <span className="rounded-full border border-rose-400/25 bg-rose-400/12 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-rose-100">
                            {pendingActionLabel(selectedSignals)}
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-1 truncate text-xs text-[var(--text-muted)]">
                        {COACH_NAME} · {COACH_LABEL}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {onRequestClose ? (
                  <button
                    className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-lg text-[var(--text-secondary)] shadow-[0_10px_24px_rgba(2,6,23,0.18)] transition hover:bg-white/[0.08] hover:text-[var(--text-primary)]"
                    type="button"
                    aria-label="Close coach"
                    onClick={onRequestClose}
                  >
                    ×
                  </button>
                ) : null}

                <details className="relative">
                  <summary className="inline-flex h-10 w-10 cursor-pointer list-none items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-lg text-[var(--text-secondary)] shadow-[0_10px_24px_rgba(2,6,23,0.18)] transition hover:bg-white/[0.08] hover:text-[var(--text-primary)]">
                    ⋮
                  </summary>
                  <div className="absolute right-0 top-12 z-10 min-w-48 rounded-2xl border border-white/10 bg-[var(--surface-elevated)] p-1.5 shadow-[0_18px_40px_rgba(2,6,23,0.26)]">
                    {confirmingArchive ? (
                      <>
                        <span className="block px-2.5 py-1.5 text-xs text-[var(--text-secondary)]">Archive this thread?</span>
                        <button
                          className="w-full rounded-xl px-2.5 py-2 text-left text-xs font-semibold text-red-300 hover:bg-red-500/10 disabled:opacity-50"
                          disabled={busyAction !== null}
                          type="button"
                          onClick={() => {
                            setConfirmingArchive(false);
                            void closeSelectedThread();
                          }}
                        >
                          {busyAction === "archive" ? "Closing..." : "Archive thread"}
                        </button>
                        <button
                          className="w-full rounded-xl px-2.5 py-2 text-left text-xs text-[var(--text-primary)] hover:bg-white/[0.06]"
                          type="button"
                          onClick={() => setConfirmingArchive(false)}
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        className="w-full rounded-xl px-2.5 py-2 text-left text-xs text-[var(--text-primary)] hover:bg-white/[0.06] disabled:opacity-50"
                        disabled={!selectedThreadId || selectedThreadStatus !== "active" || busyAction !== null}
                        type="button"
                        onClick={() => setConfirmingArchive(true)}
                      >
                        Archive thread
                      </button>
                    )}
                  </div>
                </details>
              </div>
            </div>
          </header>
        ) : (
          <header className="border-b border-white/10 bg-white/[0.03] px-4 py-3 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <CoachAvatar size="md" />
                <div className="min-w-0">
                  <div className="text-sm font-semibold tracking-[-0.01em] text-[var(--text-primary)]">{COACH_NAME}</div>
                  <div className="text-[11px] text-[var(--text-muted)]">{remainingText(quota)}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-semibold text-[var(--text-primary)] shadow-[0_10px_24px_rgba(2,6,23,0.18)] transition hover:bg-white/[0.08]"
                  disabled={busyAction !== null}
                  type="button"
                  onClick={startNewTopic}
                >
                  + New topic
                </button>
                {onRequestClose ? (
                  <button
                    className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-lg text-[var(--text-secondary)] shadow-[0_10px_24px_rgba(2,6,23,0.18)] transition hover:bg-white/[0.08] hover:text-[var(--text-primary)]"
                    type="button"
                    aria-label="Close coach"
                    onClick={onRequestClose}
                  >
                    ×
                  </button>
                ) : null}
              </div>
            </div>
          </header>
        )}

        {isConversationView ? (
          <CoachInboxConversationView
            loading={loading}
            thread={thread}
            selectedSignals={selectedSignals}
            quotaBlocked={quotaBlocked}
            composerDisabled={composerDisabled}
            busyAction={busyAction}
            busyProposalId={busyProposalId}
            liveStatusEvent={liveStatusEvent}
            optimisticAthleteMessage={optimisticAthleteMessage}
            proposalRejectReasons={proposalRejectReasons}
            messageRefs={messageRefs}
            messagesEndRef={messagesEndRef}
            onAcceptProposal={(proposalId) => void acceptProposal(proposalId)}
            onRejectProposal={(proposalId) => void rejectProposal(proposalId)}
            onRejectReasonChange={setProposalRejectReason}
            onQuickPromptSelect={applyQuickPrompt}
          />
        ) : (
          <CoachInboxThreadListView
            threadsLoading={threadsLoading}
            activeThreads={activeThreads}
            archivedThreads={archivedThreads}
            visibleArchivedThreads={visibleArchivedThreads}
            threadSignals={threadSignals}
            showAllArchived={showAllArchived}
            onToggleArchived={() => setShowAllArchived((previous) => !previous)}
            onOpenThread={(threadId) => void openThread(threadId)}
            onQuickPromptSelect={applyQuickPrompt}
          />
        )}

        <CoachInboxComposerBar
          error={error}
          quota={quota}
          quotaBlocked={quotaBlocked}
          canSendMessage={canSendMessage}
          coachGateMessage={coachGateMessage}
          coachGateTarget={coachGateTarget}
          isConversationView={isConversationView}
          selectedThreadStatus={selectedThreadStatus}
          threadCanTriggerRecap={threadCanTriggerRecap}
          trainingProviderMessage={trainingProviderMessage}
          recapGateTarget={recapGateTarget}
          busyAction={busyAction}
          composerDisabled={composerDisabled}
          listComposerDisabled={listComposerDisabled}
          input={input}
          onInputChange={setInput}
          onQuickPromptSelect={applyQuickPrompt}
          onSendMessage={(forceNewThread) => {
            void sendMessage(forceNewThread);
          }}
          onTriggerRecap={() => {
            trackCoachEvent("coach_weekly_recap_requested", { thread_id: selectedThreadId });
            void triggerRecap();
          }}
        />
      </div>
    </div>
  );
}
