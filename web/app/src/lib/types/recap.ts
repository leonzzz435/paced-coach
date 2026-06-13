import type { UiHtmlBlock, UiWeeklyPlan } from "@/lib/types/ui-blocks";
import type { CoachQuota } from "@/lib/types/quota";

export type WeeklyRecapPendingAction = "none" | "follow_up" | "proposal" | "follow_up_and_proposal";

export type WeeklyRecapNarrative = {
  this_week_blocks: UiHtmlBlock[];
  looking_ahead_blocks: UiHtmlBlock[];
};

export type WeeklyRecapResponse = {
  run_id: string;
  user_id: string;
  week_anchor_utc: string;
  status: "pending" | "completed" | "failed" | string;
  trigger_source: string;
  proposal_id?: string | null;
  created_at: string;
  updated_at: string;
  narrative: WeeklyRecapNarrative;
  base_weekly_plan?: UiWeeklyPlan | null;
  preview_weekly_plan?: UiWeeklyPlan | null;
  ops?: Array<Record<string, unknown>>;
  follow_up_question?: string | null;
  athlete_response?: string | null;
  quota?: CoachQuota;
};

export type WeeklyRecapReportResponse = {
  recap: WeeklyRecapResponse;
  thread_id: string | null;
  summary_preview: string | null;
  pending_action: WeeklyRecapPendingAction;
};

export function weeklyRecapActionLabel(action: WeeklyRecapPendingAction): string {
  if (action === "follow_up_and_proposal") return "Reply + review";
  if (action === "follow_up") return "Reply needed";
  if (action === "proposal") return "Plan review";
  return "Completed";
}

export function weeklyRecapActionDescription(action: WeeklyRecapPendingAction): string {
  if (action === "follow_up_and_proposal") {
    return "Coach has a follow-up question and a plan adjustment waiting on this recap.";
  }
  if (action === "follow_up") {
    return "Coach is waiting on one follow-up answer before the recap is fully closed out.";
  }
  if (action === "proposal") {
    return "Coach finished the recap and suggested a plan adjustment for review.";
  }
  return "This week's recap is complete and available as a report.";
}

export function weeklyRecapCoachCta(action: WeeklyRecapPendingAction): string {
  if (action === "follow_up_and_proposal") return "Reply in Coach";
  if (action === "follow_up") return "Reply in Coach";
  if (action === "proposal") return "Review in Coach";
  return "Discuss in Coach";
}
