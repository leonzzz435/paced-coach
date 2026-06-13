import type { CoachThreadMessage, CoachThreadResponse, CoachThreadStatus } from "@/lib/types/coach";

export type CoachThreadSource = "coach_chat" | "proactive" | "weekly_recap";
export type CoachThreadUrgency = "low" | "medium" | "high";

export type CoachThreadSignals = {
  source: CoachThreadSource;
  sourceLabel: string;
  urgency: CoachThreadUrgency | null;
  previewText: string;
  hasPendingProposal: boolean;
  hasPendingFollowUp: boolean;
  pendingCount: number;
  hasPendingWork: boolean;
  hasAthleteMessage: boolean;
  firstPendingMessageId: string | null;
  firstCoachMessageId: string | null;
  lastMessageAt: string | null;
};

export type CoachThreadBadgeEntry = {
  status: CoachThreadStatus;
  signals: CoachThreadSignals;
};

function sanitizeText(value: string | undefined): string {
  if (!value) return "";
  return value.replace(/\s+/g, " ").trim();
}

function stripMarkdown(text: string): string {
  return text
    .replace(/(\*{1,3}|_{1,3})(.*?)\1/g, "$2")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^[\s]*[-*+]\s+/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}

function snippet(text: string, maxLength = 84): string {
  const cleaned = sanitizeText(text);
  if (!cleaned) return "";
  if (cleaned.length <= maxLength) return cleaned;
  return `${cleaned.slice(0, maxLength - 1)}…`;
}

function extractFirstCoachText(messages: CoachThreadMessage[]): string {
  for (const message of messages) {
    if (message.kind === "text" && message.role === "coach" && sanitizeText(message.text)) {
      return stripMarkdown(sanitizeText(message.text));
    }
  }
  return "";
}

function containsHighUrgencyCue(text: string): boolean {
  const lowered = text.toLowerCase();
  return ["urgent", "immediately", "sharp pain", "injury", "high risk", "stop training"].some((cue) => lowered.includes(cue));
}

function hasPendingRecapFollowUp(messages: CoachThreadMessage[]): { pending: boolean; firstMessageId: string | null } {
  for (const message of messages) {
    if (message.kind !== "recap") continue;
    if (message.recap.follow_up_question && !message.recap.athlete_response) {
      return { pending: true, firstMessageId: message.id };
    }
  }
  return { pending: false, firstMessageId: null };
}

function hasPendingProposal(messages: CoachThreadMessage[], fallback: boolean): { pending: boolean; firstMessageId: string | null } {
  for (const message of messages) {
    if (message.kind === "proposal" && message.status.trim().toLowerCase() === "pending") {
      return { pending: true, firstMessageId: message.id };
    }
  }
  return { pending: fallback, firstMessageId: null };
}

export function deriveCoachThreadSignals(thread: CoachThreadResponse): CoachThreadSignals {
  const messages = thread.messages ?? [];
  const hasAthleteMessage = messages.some((message) => message.kind === "text" && message.role === "athlete");
  const hasRecapMessage = messages.some((message) => message.kind === "recap");
  const firstCoachText = extractFirstCoachText(messages);

  let source: CoachThreadSource = "coach_chat";
  if (hasRecapMessage) {
    source = "weekly_recap";
  } else if (!hasAthleteMessage && firstCoachText) {
    source = "proactive";
  }

  const recapFollowUp = hasPendingRecapFollowUp(messages);
  const proposalPending = hasPendingProposal(messages, thread.has_pending_proposal);
  const firstPendingMessageId = recapFollowUp.firstMessageId ?? proposalPending.firstMessageId;

  const previewText = hasRecapMessage
    ? "Weekly recap available"
    : source === "proactive"
      ? snippet(firstCoachText || "Proactive coaching alert")
      : snippet(firstCoachText || "Coach conversation");

  const urgency = source === "proactive" ? (containsHighUrgencyCue(firstCoachText) ? "high" : "medium") : null;
  const pendingCount = Number(recapFollowUp.pending) + Number(proposalPending.pending);
  const firstCoachMessageId = messages.find((message) => message.kind === "text" && message.role === "coach")?.id ?? null;

  return {
    source,
    sourceLabel: source === "weekly_recap" ? "Weekly recap" : source === "proactive" ? "Proactive" : "Coach chat",
    urgency,
    previewText,
    hasPendingProposal: proposalPending.pending,
    hasPendingFollowUp: recapFollowUp.pending,
    pendingCount,
    hasPendingWork: pendingCount > 0,
    hasAthleteMessage,
    firstPendingMessageId,
    firstCoachMessageId,
    lastMessageAt: messages.length > 0 ? messages[messages.length - 1].created_at : null,
  };
}

export function computeCoachInboxBadgeCount(entries: CoachThreadBadgeEntry[]): number {
  const activeEntries = entries.filter((entry) => entry.status === "active");
  return activeEntries.filter((entry) => entry.signals.hasPendingWork).length;
}
