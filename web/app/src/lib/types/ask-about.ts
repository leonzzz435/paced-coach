import type { UiHtmlBlockVariant } from "@/lib/types/ui-blocks";
import type { CoachTurnUiContext } from "@/lib/types/coach";

export type AskAboutContext = {
  source_tab: "analysis" | "season" | "weekly";
  block_key: string;
  block_variant: UiHtmlBlockVariant;
  block_title: string | null;
  content_preview: string;
  parent_label?: string;
};

export type OnAskAboutBlock = (ctx: AskAboutContext) => void;

export type CoachPrefillPayload = {
  message: string;
  uiContext?: CoachTurnUiContext | null;
};

const SOURCE_TAB_LABELS: Record<AskAboutContext["source_tab"], string> = {
  analysis: "Analysis",
  season: "Season roadmap",
  weekly: "Training block",
};

const HTML_TAG_PATTERN = /<[^>]*>/g;
const SENTENCE_BREAK_PATTERN = /[.!?](?=\s|$)/g;
const CLAUSE_BREAK_PATTERN = /[,;:](?=\s|$)/g;

function decodeHtmlEntities(value: string): string {
  return value
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, "\"")
    .replace(/&#39;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">");
}

function truncatePreviewText(preview: string, maxChars: number): string {
  if (preview.length <= maxChars) {
    return preview;
  }

  const sentenceMinChars = Math.max(48, Math.floor(maxChars * 0.35));
  const sentenceCandidate = preview.slice(0, maxChars + 1);
  const sentenceBreaks = Array.from(sentenceCandidate.matchAll(SENTENCE_BREAK_PATTERN))
    .map((match) => match.index != null ? match.index + match[0].length : -1)
    .filter((index) => index >= sentenceMinChars);
  if (sentenceBreaks.length > 0) {
    return preview.slice(0, sentenceBreaks[sentenceBreaks.length - 1]).trimEnd();
  }

  const clauseMinChars = Math.max(72, Math.floor(maxChars * 0.45));
  const clauseCandidate = preview.slice(0, maxChars + 1);
  const clauseBreaks = Array.from(clauseCandidate.matchAll(CLAUSE_BREAK_PATTERN))
    .map((match) => match.index ?? -1)
    .filter((index) => index >= clauseMinChars);
  if (clauseBreaks.length > 0) {
    return `${preview.slice(0, clauseBreaks[clauseBreaks.length - 1]).trimEnd()}...`;
  }

  let candidate = preview.slice(0, maxChars + 1);
  const minWordBreak = Math.max(32, Math.floor(maxChars * 0.6));
  const wordBreak = candidate.lastIndexOf(" ");
  if (wordBreak >= minWordBreak) {
    candidate = candidate.slice(0, wordBreak);
  } else {
    candidate = preview.slice(0, maxChars);
  }
  return `${candidate.replace(/[ ,;:]+$/u, "").trimEnd()}...`;
}

export function extractContentText(contentHtml: string): string {
  return decodeHtmlEntities(contentHtml.replace(HTML_TAG_PATTERN, " ").replace(/\s+/g, " ").trim());
}

export function buildContentPreview(contentHtml: string, maxChars = 180): string {
  return truncatePreviewText(extractContentText(contentHtml), maxChars);
}

export function buildAskAboutPrefill(ctx: AskAboutContext): string {
  const contextLabel = ctx.parent_label?.trim() || SOURCE_TAB_LABELS[ctx.source_tab];
  const fallbackTitle = ctx.content_preview || "this block";
  const rawTitle = ctx.block_title?.trim() || fallbackTitle;
  const title = rawTitle.length > 80 ? `${rawTitle.slice(0, 80).trimEnd()}...` : rawTitle;
  return `About "${title}" (${contextLabel}): `;
}

const COACH_PREFILL_EVENT = "coach:prefill";
const COACH_OPEN_THREAD_EVENT = "coach:open-thread";

type CoachPrefillEventDetail = {
  payload: CoachPrefillPayload;
};

type CoachOpenThreadEventDetail = {
  threadId: string;
};

export function openCoachWithPrefill(payload: string | CoachPrefillPayload) {
  if (typeof window === "undefined") {
    return;
  }
  const resolvedPayload = typeof payload === "string" ? { message: payload } : payload;
  window.dispatchEvent(new CustomEvent<CoachPrefillEventDetail>(COACH_PREFILL_EVENT, { detail: { payload: resolvedPayload } }));
}

export function openCoachThread(threadId: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent<CoachOpenThreadEventDetail>(COACH_OPEN_THREAD_EVENT, { detail: { threadId } }));
}

export function subscribeCoachPrefill(listener: (payload: CoachPrefillPayload) => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handleEvent = (event: Event) => {
    const customEvent = event as CustomEvent<CoachPrefillEventDetail>;
    const payload = customEvent.detail?.payload;
    if (payload && typeof payload.message === "string") {
      listener(payload);
    }
  };

  window.addEventListener(COACH_PREFILL_EVENT, handleEvent as EventListener);
  return () => window.removeEventListener(COACH_PREFILL_EVENT, handleEvent as EventListener);
}

export function subscribeCoachOpenThread(listener: (threadId: string) => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handleEvent = (event: Event) => {
    const customEvent = event as CustomEvent<CoachOpenThreadEventDetail>;
    const threadId = customEvent.detail?.threadId;
    if (typeof threadId === "string") {
      listener(threadId);
    }
  };

  window.addEventListener(COACH_OPEN_THREAD_EVENT, handleEvent as EventListener);
  return () => window.removeEventListener(COACH_OPEN_THREAD_EVENT, handleEvent as EventListener);
}
