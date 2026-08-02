import type { CoachTurnResponse } from "@/lib/types/coach";
import type { SeasonPlanV3, SemanticBlockV3, WeeklyPlanV3 } from "@/components/plan-viewer/types";
import { semanticBlockText, semanticBlockTitle } from "@/lib/semantic-block";
import type { WeeklyRecapPendingAction, WeeklyRecapResponse } from "@/lib/types/recap";
import type { UiAnalysis, UiDayPlan, UiHtmlBlock, UiKpi, UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";
import { extractContentText } from "@/lib/types/ask-about";

export type DashboardAnalysisState = {
  analysis: UiAnalysis;
  version: number;
  updated_at: string;
  source_job_id: string;
};

export type DashboardCoachSurfaceSource = "daily_sync" | "weekly_recap" | "analysis" | "none";
export type DashboardCoachSurfaceScope = "today" | "this_week" | "training_block" | "none";

export type DashboardCoachSurface = {
  source: DashboardCoachSurfaceSource;
  scope: DashboardCoachSurfaceScope;
  primary_label: string | null;
  primary_text: string | null;
  secondary_text: string | null;
  updated_at: string | null;
};

export type DashboardFirstRunAction = {
  label: string;
  href: string;
};

export type DashboardFirstRunStep = "llm_key" | "profile" | "goal" | "generate" | "generated";

export type DashboardFirstRunState = {
  mode: "manual" | "connected";
  evidence_level: "declared_only" | "connected";
  llm_ready: boolean;
  profile_completeness: number;
  profile_ready: boolean;
  goal_ready: boolean;
  has_competitions: boolean;
  has_active_plan: boolean;
  has_connected_source: boolean;
  next_step: DashboardFirstRunStep;
  title: string;
  body: string;
  primary_action: DashboardFirstRunAction | null;
  secondary_actions: DashboardFirstRunAction[];
  blockers: string[];
};

export type DashboardStateResponse = {
  athlete_time: {
    timezone: string;
    timezone_source: "profile" | "fallback_utc";
    today_local_date: string;
    now_local_iso: string;
  };
  analysis?: DashboardAnalysisState | null;
  status_surface: {
    kpis: UiKpi[];
    source: "daily_update" | "analysis" | "none";
    label: string | null;
    updated_at: string | null;
    target_date: string | null;
  };
  coach_surface: DashboardCoachSurface;
  season?: { season_plan: UiSeasonPlan | SeasonPlanV3; version: number; updated_at: string; source_job_id: string } | null;
  weekly?: { weekly_plan: UiWeeklyPlan | WeeklyPlanV3; version: number; updated_at: string; source_job_id: string } | null;
  first_run: DashboardFirstRunState;
  today_mission: {
    warnings: string[];
    day_override: UiDayPlan | null;
  };
  daily_sync: {
    visible: boolean;
    status: "idle" | "pending" | "completed" | "failed";
    run_id: string | null;
    verdict_preview: string | null;
    sources_used: string[];
    proposal_id: string | null;
    thread_id: string | null;
    error_message: string | null;
    can_run: boolean;
    attention_message: string | null;
    gate_target: "settings" | null;
  };
  weekly_recap: {
    visible: boolean;
    allowed: boolean;
    status: "hidden" | "ready" | "completed_this_window";
    thread_id: string | null;
    proposal_id: string | null;
    follow_up_question: string | null;
    summary_preview: string | null;
    pending_action: WeeklyRecapPendingAction;
    can_run: boolean;
    attention_message: string | null;
    gate_target: "settings" | null;
  };
  pending_proposal_banner: {
    proposal_id: string;
    thread_id: string;
    origin: string;
    assistant_message: string;
  } | null;
};

export type DailyRunResponse = {
  status: "success";
  run_id: string;
  sources_used: string[];
  proposal_id: string | null;
  thread_id: string | null;
  preview_weekly_plan: UiWeeklyPlan | WeeklyPlanV3 | null;
  narrative: {
    dashboard_kpis: UiKpi[];
    today_focus_blocks: SemanticBlockV3[];
    optional_proposal_ops: Array<Record<string, unknown>>;
  };
  today_override: UiDayPlan | null;
};

export type DashboardDailySyncState = DashboardStateResponse["daily_sync"];
export type DashboardCoachSurfaceState = DashboardStateResponse["coach_surface"];
export type DashboardWeeklyRecapState = DashboardStateResponse["weekly_recap"];
export type PendingProposalBannerState = DashboardStateResponse["pending_proposal_banner"];

function normalizeText(value: string | null | undefined): string | null {
  const normalized = value?.trim() ?? "";
  return normalized || null;
}

export function emptyCoachSurface(): DashboardCoachSurface {
  return {
    source: "none",
    scope: "none",
    primary_label: null,
    primary_text: null,
    secondary_text: null,
    updated_at: null,
  };
}

export function truncatePreviewText(preview: string, maxChars = 180): string {
  if (preview.length <= maxChars) {
    return preview;
  }

  const sentenceMinChars = Math.max(48, Math.floor(maxChars * 0.35));
  const sentenceBreaks = Array.from(preview.slice(0, maxChars + 1).matchAll(/[.!?](?=\s|$)/g))
    .map((match) => (match.index ?? 0) + match[0].length)
    .filter((offset) => offset >= sentenceMinChars);
  if (sentenceBreaks.length > 0) {
    return preview.slice(0, sentenceBreaks[sentenceBreaks.length - 1]).trimEnd();
  }

  const clauseMinChars = Math.max(72, Math.floor(maxChars * 0.45));
  const clauseBreaks = Array.from(preview.slice(0, maxChars + 1).matchAll(/[,;:](?=\s|$)/g))
    .map((match) => match.index ?? 0)
    .filter((offset) => offset >= clauseMinChars);
  if (clauseBreaks.length > 0) {
    return `${preview.slice(0, clauseBreaks[clauseBreaks.length - 1]).trimEnd()}...`;
  }

  let candidate = preview.slice(0, maxChars + 1);
  const wordBreak = candidate.lastIndexOf(" ");
  if (wordBreak >= Math.max(32, Math.floor(maxChars * 0.6))) {
    candidate = candidate.slice(0, wordBreak);
  } else {
    candidate = preview.slice(0, maxChars);
  }
  return `${candidate.replace(/[ ,;:]+$/u, "").trimEnd()}...`;
}

function splitPreviewText(preview: string | null): { primary: string | null; secondary: string | null } {
  const normalized = normalizeText(preview);
  if (!normalized) {
    return { primary: null, secondary: null };
  }

  for (const match of normalized.matchAll(/[.!?](?=\s|$)/g)) {
    const offset = (match.index ?? 0) + match[0].length;
    if (offset < 10) continue;
    const primary = normalizeText(normalized.slice(0, offset));
    const secondary = normalizeText(normalized.slice(offset));
    return { primary, secondary };
  }

  return { primary: normalized, secondary: null };
}

function buildCoachSurface(input: {
  source: DashboardCoachSurfaceSource;
  scope: DashboardCoachSurfaceScope;
  primaryLabel: string;
  primaryText: string | null;
  secondaryText: string | null;
  updatedAt: string | null;
}): DashboardCoachSurface | null {
  let primaryText = normalizeText(input.primaryText);
  let secondaryText = normalizeText(input.secondaryText);

  if (!primaryText && secondaryText) {
    primaryText = secondaryText;
    secondaryText = null;
  }

  if (!primaryText) {
    return null;
  }

  return {
    source: input.source,
    scope: input.scope,
    primary_label: input.primaryLabel,
    primary_text: primaryText,
    secondary_text: secondaryText,
    updated_at: input.updatedAt,
  };
}

export function resolveDailySyncVerdictPreview(
  dailySync: DashboardDailySyncState,
  dayOverride: DashboardStateResponse["today_mission"]["day_override"],
): string | null {
  const focusBlockHtml = dayOverride?.blocks[0]?.content_html;
  if (typeof focusBlockHtml === "string") {
    const extracted = extractContentText(focusBlockHtml);
    if (extracted) {
      return extracted;
    }
  }
  return dailySync.verdict_preview;
}

type RecapTurnPayload = {
  kind: "recap";
  recap: WeeklyRecapResponse;
};

type RecapBlock = SemanticBlockV3 | UiHtmlBlock;

function recapBlockTitle(block: RecapBlock): string | null {
  return block.type === "html" ? block.title?.trim() || null : semanticBlockTitle(block);
}

function recapBlockText(block: RecapBlock): string {
  return block.type === "html" ? extractContentText(block.content_html) : semanticBlockText(block);
}

export function resolveWeeklyRecapPendingAction(input: {
  proposalId?: string | null;
  followUpQuestion?: string | null;
  athleteResponse?: string | null;
}): WeeklyRecapPendingAction {
  const hasPendingProposal = Boolean(input.proposalId);
  const hasPendingFollowUp = Boolean(input.followUpQuestion && !input.athleteResponse);

  if (hasPendingProposal && hasPendingFollowUp) return "follow_up_and_proposal";
  if (hasPendingFollowUp) return "follow_up";
  if (hasPendingProposal) return "proposal";
  return "none";
}

export function resolveRecapSummaryPreview(payload: RecapTurnPayload["recap"] | null | undefined): string | null {
  if (!payload?.narrative) return null;

  for (const section of [payload.narrative.this_week_blocks, payload.narrative.looking_ahead_blocks]) {
    if (!Array.isArray(section)) continue;
    for (const block of section) {
      const title = recapBlockTitle(block);
      if (title?.trim()) return title.trim();
      const extracted = recapBlockText(block).trim();
      if (extracted) return truncatePreviewText(extracted, 220);
    }
  }
  return null;
}

export function resolveRecapGuidancePreview(payload: RecapTurnPayload["recap"] | null | undefined): string | null {
  if (!payload?.narrative) return null;

  const summaryPreview = resolveRecapSummaryPreview(payload);
  for (const section of [payload.narrative.looking_ahead_blocks, payload.narrative.this_week_blocks]) {
    if (!Array.isArray(section)) continue;
    for (const block of section) {
      const title = recapBlockTitle(block);
      if (title?.trim() && title.trim() !== summaryPreview) return title.trim();
      const extracted = recapBlockText(block).trim();
      if (!extracted) continue;
      const preview = truncatePreviewText(extracted, 220);
      if (preview !== summaryPreview) {
        return preview;
      }
    }
  }
  return null;
}

export function buildCoachSurfaceFromAnalysis(
  analysisPayload: DashboardAnalysisState | null | undefined,
): DashboardCoachSurface {
  const analysis = analysisPayload?.analysis;
  const surface =
    analysis &&
    buildCoachSurface({
      source: "analysis",
      scope: "training_block",
      primaryLabel: "Block Focus",
      primaryText: analysis.coach_action ?? null,
      secondaryText: analysis.headline_brief ?? null,
      updatedAt: analysisPayload?.updated_at ?? null,
    });
  return surface ?? emptyCoachSurface();
}

export function buildCoachSurfaceFromDailySyncResult(
  response: DailyRunResponse,
  updatedAt = new Date().toISOString(),
): DashboardCoachSurface | null {
  const firstFocusBlock = response.narrative.today_focus_blocks[0];
  const preview = firstFocusBlock ? semanticBlockText(firstFocusBlock) : null;
  const { primary, secondary } = splitPreviewText(preview);

  return buildCoachSurface({
    source: "daily_sync",
    scope: "today",
    primaryLabel: "Today's Action",
    primaryText: primary,
    secondaryText: secondary,
    updatedAt,
  });
}

export function buildCoachSurfaceFromWeeklyRecap(
  recap: WeeklyRecapResponse | null | undefined,
): DashboardCoachSurface | null {
  return buildCoachSurface({
    source: "weekly_recap",
    scope: "this_week",
    primaryLabel: "This Week's Priority",
    primaryText: resolveRecapSummaryPreview(recap),
    secondaryText: resolveRecapGuidancePreview(recap),
    updatedAt: recap?.updated_at ?? null,
  });
}

export function getRecapTurnPayload(payload: CoachTurnResponse | null): RecapTurnPayload | null {
  const turn = payload?.turn;
  if (!turn || typeof turn !== "object") return null;
  const candidate = turn as Record<string, unknown>;
  if (candidate.kind !== "recap") return null;
  const recap = candidate.recap;
  if (!recap || typeof recap !== "object") return null;
  return candidate as unknown as RecapTurnPayload;
}
