import type { UiWeeklyPlan } from "@/lib/types/ui-blocks";
import type { WeeklyRecapResponse } from "@/lib/types/recap";
import type { CoachQuota } from "@/lib/types/quota";

export type CoachThreadStatus = "active" | "archived";

export type CoachThreadMessage =
  | {
      id: string;
      kind: "text";
      role: "coach" | "athlete";
      created_at: string;
      text: string;
    }
  | {
      id: string;
      kind: "recap";
      role: "coach";
      created_at: string;
      recap: WeeklyRecapResponse;
    }
  | {
      id: string;
      kind: "proposal";
      role: "coach";
      created_at: string;
      proposal_id: string;
      origin: string;
      status: string;
      assistant_message: string;
      ops: Array<Record<string, unknown>>;
      base_weekly_plan?: UiWeeklyPlan | null;
      preview_weekly_plan?: UiWeeklyPlan | null;
    };

export type CoachThreadResponse = {
  thread?: {
    id: string;
    status: CoachThreadStatus;
    title: string | null;
    latest_seq: number;
    updated_at: string;
  };
  week_anchor_utc: string;
  messages: CoachThreadMessage[];
  quota: CoachQuota;
  can_send_message: boolean;
  coach_gate_message?: string | null;
  coach_gate_target?: "settings" | null;
  can_trigger_recap: boolean;
  training_provider_message?: string | null;
  recap_gate_target?: "settings" | null;
  has_pending_proposal: boolean;
  pending_proposal_ids?: string[];
  next_after_seq?: number | null;
};

export type CoachTurnUiContext = {
  source: "today_mission";
  day_id: string;
  week_id?: string | null;
  date?: string | null;
  day_label?: string | null;
  workout_title?: string | null;
};

export type CoachTurnRequest = {
  thread_id?: string;
  action: "text" | "proposal_accept" | "proposal_reject" | "recap";
  idempotency_key: string;
  message?: string;
  proposal_id?: string;
  reason?: string;
  ui_context?: CoachTurnUiContext;
};

export type CoachTurnResponse = {
  thread: {
    id: string;
    status: CoachThreadStatus;
    title: string | null;
    latest_seq: number;
    updated_at: string;
  };
  events_appended: Array<{ seq: number; event_type: string }>;
  projection: {
    messages: CoachThreadMessage[];
    quota: CoachQuota;
    can_send_message: boolean;
    coach_gate_message?: string | null;
    coach_gate_target?: "settings" | null;
    has_pending_proposal: boolean;
    can_trigger_recap: boolean;
    training_provider_message?: string | null;
    recap_gate_target?: "settings" | null;
    pending_proposal_ids: string[];
    next_after_seq?: number | null;
  };
  turn: Record<string, unknown>;
};

export type CoachThreadListItem = {
  id: string;
  status: CoachThreadStatus;
  title: string | null;
  latest_seq: number;
  created_at: string;
  updated_at: string;
  messages?: CoachThreadMessage[];
  has_pending_proposal?: boolean;
};

export type CoachThreadsResponse = {
  items: CoachThreadListItem[];
  limit: number;
  offset: number;
  has_more: boolean;
  next_offset?: number | null;
};

export type CoachArchiveThreadResponse = {
  thread: {
    id: string;
    status: CoachThreadStatus;
    title: string | null;
    latest_seq: number;
    updated_at: string;
  };
};
