import type { MutableRefObject, RefObject } from "react";

import MarkdownSnippet from "@/components/markdown_snippet";
import type { CoachThreadSignals } from "@/lib/coach/inbox";
import type { CoachThreadMessage, CoachThreadResponse } from "@/lib/types/coach";

import {
  type BusyAction,
  type CoachTurnStatusEvent,
  COACH_DESCRIPTION,
  COACH_NAME,
  COACH_QUICK_PROMPTS,
  CoachAvatar,
  ProposalCard,
  RecapMessage,
  describeCoachStatus,
  fullTime,
  relativeTime,
} from "./coach-inbox-parts";

type CoachInboxConversationViewProps = {
  loading: boolean;
  thread: CoachThreadResponse | null;
  selectedSignals: CoachThreadSignals | null;
  quotaBlocked: boolean;
  composerDisabled: boolean;
  busyAction: BusyAction | null;
  busyProposalId: string | null;
  liveStatusEvent: CoachTurnStatusEvent | null;
  optimisticAthleteMessage: {
    id: string;
    created_at: string;
    text: string;
  } | null;
  proposalRejectReasons: Record<string, string>;
  messageRefs: MutableRefObject<Record<string, HTMLDivElement | null>>;
  messagesEndRef: RefObject<HTMLDivElement | null>;
  onAcceptProposal: (proposalId: string) => void;
  onRejectProposal: (proposalId: string) => void;
  onRejectReasonChange: (proposalId: string, value: string) => void;
  onQuickPromptSelect: (value: string) => void;
};

function CoachMessageMeta({ createdAt, sourceBadge }: { createdAt: string; sourceBadge?: string | null }) {
  return (
    <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
      <CoachAvatar />
      <span>{COACH_NAME}</span>
      <span title={fullTime(createdAt)}>{relativeTime(createdAt)}</span>
      {sourceBadge ? (
        <span className="rounded-full border border-amber-400/25 bg-amber-400/12 px-1.5 py-0.5 text-[10px] font-semibold text-amber-100">
          {sourceBadge}
        </span>
      ) : null}
    </div>
  );
}

function AthleteMessageBubble({
  createdAt,
  text,
  pending = false,
}: {
  createdAt: string;
  text: string;
  pending?: boolean;
}) {
  return (
    <div className={`ml-auto max-w-[92%] ${pending ? "opacity-95" : ""}`}>
      <div className="text-right text-[11px] text-[var(--text-muted)]" title={fullTime(createdAt)}>
        You · {pending ? "Sending..." : relativeTime(createdAt)}
      </div>
      <div className="mt-1 rounded-[1.45rem] rounded-tr-md bg-[linear-gradient(135deg,#111827,#1f2937)] px-4 py-3 text-sm leading-6 text-white shadow-[0_12px_28px_rgba(15,23,42,0.18)]">
        {text}
      </div>
    </div>
  );
}

export default function CoachInboxConversationView({
  loading,
  thread,
  selectedSignals,
  quotaBlocked,
  composerDisabled,
  busyAction,
  busyProposalId,
  liveStatusEvent,
  optimisticAthleteMessage,
  proposalRejectReasons,
  messageRefs,
  messagesEndRef,
  onAcceptProposal,
  onRejectProposal,
  onRejectReasonChange,
  onQuickPromptSelect,
}: CoachInboxConversationViewProps) {
  const statusDisplay = liveStatusEvent ? describeCoachStatus(liveStatusEvent) : null;

  return (
    <div className="flex-1 space-y-4 overflow-y-auto bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.07),transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01))] px-4 py-4">
      {loading ? <div className="text-xs text-[var(--text-muted)]">Loading coach conversation...</div> : null}

      {thread && thread.messages.length === 0 && !optimisticAthleteMessage && !loading ? (
        <div className="rounded-[1.6rem] border border-emerald-400/25 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.12),transparent_42%),linear-gradient(180deg,rgba(16,185,129,0.06),rgba(15,23,42,0.92))] p-5 shadow-[0_18px_48px_rgba(2,6,23,0.22)]">
          <div className="flex items-start gap-3">
            <CoachAvatar size="md" />
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-300">{COACH_NAME}</div>
              <div className="mt-1 text-xl font-semibold tracking-[-0.03em] text-[var(--text-primary)]">Ask something specific.</div>
              <div className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">{COACH_DESCRIPTION}</div>
            </div>
          </div>

          {selectedSignals?.source === "proactive" ? (
            <div className="mt-4 rounded-2xl border border-amber-400/25 bg-amber-400/12 px-4 py-3 text-sm text-amber-100">
              This thread started from a coaching alert. You can ask for context, alternatives, or a plan adjustment here.
            </div>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-2">
            {COACH_QUICK_PROMPTS.slice(0, 3).map((prompt) => (
              <button
                key={prompt}
                className="rounded-full border border-emerald-400/25 bg-emerald-400/12 px-3 py-1.5 text-xs font-medium text-emerald-100 shadow-[0_10px_20px_rgba(2,6,23,0.14)] transition hover:bg-emerald-400/18"
                disabled={composerDisabled}
                type="button"
                onClick={() => onQuickPromptSelect(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {thread?.messages.map((message, index) => {
        const previous = index > 0 ? thread.messages[index - 1] : null;
        const compactSpacing =
          previous !== null &&
          previous.kind === "text" &&
          message.kind === "text" &&
          previous.role === message.role;

        if (message.kind === "recap") {
          return (
            <div
              key={message.id}
              ref={(node) => {
                messageRefs.current[message.id] = node;
              }}
              className={compactSpacing ? "space-y-2" : "pt-2 space-y-2"}
            >
              <CoachMessageMeta createdAt={message.created_at} />
              <RecapMessage
                message={message}
                quotaBlocked={quotaBlocked}
                busyAction={busyAction}
                onAcceptProposal={(proposalId) => onAcceptProposal(proposalId)}
                onRejectProposal={(proposalId) => onRejectProposal(proposalId)}
                baseWeeklyPlan={message.recap.base_weekly_plan}
                previewWeeklyPlan={message.recap.preview_weekly_plan}
                proposalStatus={
                  message.recap.proposal_id
                    ? (
                        thread.messages.find(
                          (candidate) => candidate.kind === "proposal" && candidate.proposal_id === message.recap.proposal_id
                        ) as Extract<CoachThreadMessage, { kind: "proposal" }> | undefined
                      )?.status ??
                      (thread.pending_proposal_ids?.includes(message.recap.proposal_id) ? "pending" : "resolved")
                    : "pending"
                }
                rejectReason={message.recap.proposal_id ? (proposalRejectReasons[message.recap.proposal_id] ?? "") : ""}
                onRejectReasonChange={(value) => {
                  if (!message.recap.proposal_id) return;
                  onRejectReasonChange(message.recap.proposal_id, value);
                }}
              />
            </div>
          );
        }

        if (message.kind === "proposal") {
          const isRecapProposal = thread.messages.some(
            (candidate) => candidate.kind === "recap" && candidate.recap.proposal_id === message.proposal_id
          );
          if (message.origin === "weekly_recap" && isRecapProposal) {
            return null;
          }
          return (
            <div
              key={message.id}
              ref={(node) => {
                messageRefs.current[message.id] = node;
              }}
              className={compactSpacing ? "space-y-2" : "pt-2 space-y-2"}
            >
              <CoachMessageMeta createdAt={message.created_at} />
              <div className="max-w-[94%] rounded-[1.45rem] rounded-tl-md border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] px-4 py-3 shadow-[0_12px_28px_rgba(2,6,23,0.18)]">
                <MarkdownSnippet className="text-sm leading-6 text-[var(--text-primary)]" markdown={message.assistant_message} />
              </div>
              <ProposalCard
                proposalId={message.proposal_id}
                ops={message.ops}
                status={message.status}
                beforePlan={message.base_weekly_plan}
                afterPlan={message.preview_weekly_plan}
                busyAction={busyProposalId === message.proposal_id ? busyAction : null}
                disabled={composerDisabled}
                rejectReason={proposalRejectReasons[message.proposal_id] ?? ""}
                onRejectReasonChange={(value) => onRejectReasonChange(message.proposal_id, value)}
                onAccept={() => onAcceptProposal(message.proposal_id)}
                onReject={() => onRejectProposal(message.proposal_id)}
              />
            </div>
          );
        }

        if (message.role === "athlete") {
          return (
            <div
              key={message.id}
              ref={(node) => {
                messageRefs.current[message.id] = node;
              }}
              className="contents"
            >
              <AthleteMessageBubble createdAt={message.created_at} text={message.text} />
            </div>
          );
        }

        const sourceBadge = selectedSignals?.source === "proactive" && index === 0 ? "Coach alert" : null;
        return (
          <div
            key={message.id}
            ref={(node) => {
              messageRefs.current[message.id] = node;
            }}
            className="max-w-[94%]"
          >
            <CoachMessageMeta createdAt={message.created_at} sourceBadge={sourceBadge} />
            <div className="mt-1 rounded-[1.45rem] rounded-tl-md border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] px-4 py-3 text-sm leading-6 text-[var(--text-primary)] shadow-[0_12px_28px_rgba(2,6,23,0.18)]">
              <MarkdownSnippet className="text-sm leading-6 text-[var(--text-primary)]" markdown={message.text} />
            </div>
          </div>
        );
      })}

      {optimisticAthleteMessage ? (
        <AthleteMessageBubble
          createdAt={optimisticAthleteMessage.created_at}
          pending
          text={optimisticAthleteMessage.text}
        />
      ) : null}

      {busyAction === "send" && statusDisplay ? (
        <div className="max-w-[94%] transition-opacity duration-300">
          <CoachMessageMeta createdAt={new Date().toISOString()} />
          <div className="mt-1 rounded-[1.45rem] rounded-tl-md border border-sky-400/25 bg-[linear-gradient(180deg,rgba(56,189,248,0.12),rgba(15,23,42,0.92))] px-4 py-3 text-sm text-sky-100 shadow-[0_12px_28px_rgba(14,165,233,0.10)]">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-2.5 w-2.5 animate-pulse rounded-full bg-sky-500" />
              <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-100">{statusDisplay.title}</span>
            </div>
            <div className="mt-2 text-sm leading-6 text-[var(--text-primary)]">{statusDisplay.detail}</div>
          </div>
        </div>
      ) : null}

      <div ref={messagesEndRef} />
    </div>
  );
}
