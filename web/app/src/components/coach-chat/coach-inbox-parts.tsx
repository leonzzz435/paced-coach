import { useMemo } from "react";

import HtmlSnippet from "@/components/html_snippet";
import type { CoachThreadSignals } from "@/lib/coach/inbox";
import type { CoachThreadMessage, CoachTurnResponse } from "@/lib/types/coach";
import type { CoachQuota } from "@/lib/types/quota";
import type { UiDayPlan, UiHtmlBlock, UiWeekPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";

export type BusyAction = "accept" | "reject" | "send" | "archive";
export type InboxView = "thread_list" | "conversation";

export type CoachTurnStatusEvent = {
  step: string;
  tool_name?: string;
  message: string;
  iteration?: number;
};

export const DEFAULT_COACH_STATUS_MESSAGE = "Preparing coaching context...";
export const COACH_STREAM_READ_TIMEOUT_MS = 30000;
export const COACH_STREAM_TOTAL_TIMEOUT_MS: number | null = null;
export const COACH_STREAM_DONE_READ_TIMEOUT_MS = 5000;
export const COACH_NAME = "Paced Coach";
export const COACH_LABEL = "Adaptive endurance guidance";
export const COACH_DESCRIPTION =
  "Ask for block adjustments, scheduling guidance, and race strategy — grounded in your declared context and active plan.";
export const COACH_INITIALS = "PC";
export const COACH_QUICK_PROMPTS = [
  "Help me reflect on this training week.",
  "Can I swap tomorrow's workout?",
  "Am I on track for my next race?",
  "What should I prioritize this week?",
] as const;

const RELATIVE_TIME_FORMATTER = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const FULL_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "short", day: "numeric" });
const TOOL_LABELS: Record<string, string> = {
  get_training_snapshot: "training snapshot",
  get_recent_activities: "recent activities",
  get_activity_detail: "activity details",
  get_training_load_history: "training load trends",
  get_recovery_readiness_signals: "recovery readiness",
  get_expert_analysis_summary: "analysis summary",
  get_expert_output: "expert insights",
  get_current_analysis: "current analysis",
  get_current_weekly_plan: "training block",
  get_current_season_plan: "season roadmap",
  get_upcoming_competitions: "race calendar",
};
const REJECT_REASON_SUGGESTIONS = [
  "Load feels too high for this week",
  "I need to move sessions around my schedule",
  "Recovery is lower than expected",
  "I prefer a different workout option",
] as const;

export class CoachStreamServerError extends Error {}
export type CoachTurnSseReadOptions = {
  readTimeoutMs?: number;
  totalTimeoutMs?: number | null;
  doneReadTimeoutMs?: number;
};

export function parseApiError(raw: string): string {
  if (!raw) return "Request failed";
  try {
    const payload = JSON.parse(raw) as { detail?: unknown; message?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim()) return payload.detail;
    if (typeof payload.message === "string" && payload.message.trim()) return payload.message;
  } catch {
    // non-JSON responses are surfaced as-is
  }
  return raw;
}

export async function readErrorMessage(response: Response): Promise<string> {
  const raw = await response.text().catch(() => "");
  return parseApiError(raw);
}

export function isThreadNotFoundError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  return error.message.trim().toLowerCase() === "thread not found";
}

export function parseSseFrame(frame: string): { event: string; data: string } | null {
  const lines = frame.split(/\r?\n/);
  let eventName = "message";
  const dataLines: string[] = [];

  for (const rawLine of lines) {
    if (!rawLine || rawLine.startsWith(":")) continue;
    if (rawLine.startsWith("event:")) {
      eventName = rawLine.slice("event:".length).trim();
      continue;
    }
    if (rawLine.startsWith("data:")) {
      dataLines.push(rawLine.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0 && eventName === "message") return null;
  return { event: eventName, data: dataLines.join("\n") };
}

export function asStatusEvent(payload: unknown): CoachTurnStatusEvent | null {
  if (!payload || typeof payload !== "object") return null;
  const candidate = payload as Record<string, unknown>;
  const messageValue = candidate["message"];
  if (typeof messageValue !== "string") return null;
  return {
    step: typeof candidate["step"] === "string" ? candidate["step"] : "status",
    tool_name: typeof candidate["tool_name"] === "string" ? candidate["tool_name"] : undefined,
    message: messageValue,
    iteration: typeof candidate["iteration"] === "number" ? candidate["iteration"] : undefined,
  };
}

type CoachStatusDisplay = {
  title: string;
  detail: string;
};

function prettifyToolLabel(toolName: string | undefined): string {
  if (!toolName) return "training context";
  return TOOL_LABELS[toolName] ?? toolName.replaceAll("_", " ");
}

export function describeCoachStatus(statusEvent: CoachTurnStatusEvent): CoachStatusDisplay {
  const iterationLabel = statusEvent.iteration && statusEvent.iteration > 1 ? ` (pass ${statusEvent.iteration})` : "";

  if (statusEvent.step === "preparing") {
    return {
      title: "Gathering your latest context",
      detail: statusEvent.message || DEFAULT_COACH_STATUS_MESSAGE,
    };
  }
  if (statusEvent.step === "thinking") {
    return {
      title: `Reasoning through your request${iterationLabel}`,
      detail: statusEvent.message || "Building your coaching answer...",
    };
  }
  if (statusEvent.step === "tool_call_start") {
    const toolLabel = prettifyToolLabel(statusEvent.tool_name);
    return {
      title: `Reviewing ${toolLabel}${iterationLabel}`,
      detail: statusEvent.message || "Pulling deeper detail...",
    };
  }
  if (statusEvent.step === "tool_call_end") {
    return {
      title: `Updating recommendations${iterationLabel}`,
      detail: statusEvent.message || "Applying retrieved context...",
    };
  }

  return {
    title: "Working on your response",
    detail: statusEvent.message || DEFAULT_COACH_STATUS_MESSAGE,
  };
}

function parseSseEventData(data: string, eventName: string): unknown {
  if (!data) return null;
  try {
    return JSON.parse(data) as unknown;
  } catch {
    throw new Error(`Malformed ${eventName} event payload`);
  }
}

export async function readCoachTurnSse(
  response: Response,
  onStatus: (statusEvent: CoachTurnStatusEvent) => void,
  options: CoachTurnSseReadOptions = {},
): Promise<CoachTurnResponse> {
  if (!response.body) {
    throw new Error("Live stream unavailable");
  }

  const readTimeoutMs = options.readTimeoutMs ?? COACH_STREAM_READ_TIMEOUT_MS;
  const totalTimeoutMs = options.totalTimeoutMs ?? COACH_STREAM_TOTAL_TIMEOUT_MS;
  const doneReadTimeoutMs = options.doneReadTimeoutMs ?? COACH_STREAM_DONE_READ_TIMEOUT_MS;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let resultPayload: CoachTurnResponse | null = null;
  let doneEventSeen = false;
  let streamClosed = false;
  const startedAt = Date.now();

  async function readNextChunkWithTimeout(timeoutMs: number): Promise<ReadableStreamReadResult<Uint8Array>> {
    return await new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error("Coach stream stalled"));
      }, timeoutMs);

      reader
        .read()
        .then((chunk) => {
          clearTimeout(timeoutId);
          resolve(chunk);
        })
        .catch((error: unknown) => {
          clearTimeout(timeoutId);
          reject(error);
        });
    });
  }

  try {
    while (true) {
      const elapsedMs = Date.now() - startedAt;
      if (totalTimeoutMs !== null && elapsedMs > totalTimeoutMs) {
        throw new Error("Coach response timed out");
      }

      const chunkReadTimeoutMs = doneEventSeen ? doneReadTimeoutMs : readTimeoutMs;
      const readResult = await readNextChunkWithTimeout(chunkReadTimeoutMs);
      const { done, value } = readResult;
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const parsed = parseSseFrame(frame);
        if (!parsed) continue;
        const eventData = parseSseEventData(parsed.data, parsed.event);

        if (parsed.event === "status") {
          const statusEvent = asStatusEvent(eventData);
          if (statusEvent) onStatus(statusEvent);
          continue;
        }
        if (parsed.event === "result") {
          if (!isCoachTurnResponse(eventData)) {
            throw new Error("Invalid coach turn payload");
          }
          resultPayload = eventData;
          continue;
        }
        if (parsed.event === "error") {
          const detail =
            eventData && typeof eventData === "object" && typeof (eventData as Record<string, unknown>)["detail"] === "string"
              ? String((eventData as Record<string, unknown>)["detail"])
              : "Coach stream failed";
          throw new CoachStreamServerError(detail);
        }
        if (parsed.event === "done") {
          doneEventSeen = true;
        }
      }

      if (done) {
        streamClosed = true;
        if (buffer.trim()) {
          const trailingFrame = parseSseFrame(buffer);
          if (trailingFrame?.event === "result" && trailingFrame.data) {
            const trailingPayload = parseSseEventData(trailingFrame.data, trailingFrame.event);
            if (isCoachTurnResponse(trailingPayload)) {
              resultPayload = trailingPayload;
            }
          }
        }
        break;
      }
    }
  } finally {
    if (!streamClosed) {
      await reader.cancel().catch(() => undefined);
    }
  }

  if (!resultPayload) {
    throw new Error("No result returned from coach stream");
  }
  return resultPayload;
}

export function remainingText(quota: CoachQuota | null): string {
  if (!quota || !quota.is_limited || quota.limit == null || quota.remaining == null) {
    return "Unlimited coaching";
  }
  return `${quota.remaining} of ${quota.limit} remaining this week`;
}

type DiffItem = {
  scope: "day" | "week" | "plan";
  target: string;
  action: string;
  detail: string;
};

type ProposalDiffSummary = {
  dayIds: string[];
  weekIds: string[];
  items: DiffItem[];
};

type LocatedDay = {
  week: UiWeekPlan;
  day: UiDayPlan;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function compactLabelList(labels: string[], limit = 3): string {
  if (labels.length <= limit) return labels.join(", ");
  return `${labels.slice(0, limit).join(", ")} +${labels.length - limit} more`;
}

function hasOwnField(value: Record<string, unknown>, field: string): boolean {
  return Object.prototype.hasOwnProperty.call(value, field);
}

function describeBlock(value: unknown): string {
  const block = asRecord(value);
  if (!block) return "block";
  const title = asString(block["title"]);
  const variant = asString(block["variant"]);
  const key = asString(block["key"]);

  if (title && variant) return `"${title}" (${variant})`;
  if (title) return `"${title}"`;
  if (variant) return `${variant} block`;
  if (key) return `block "${key}"`;
  return "block";
}

function formatDayDateLabel(dateValue: string | undefined): string | null {
  if (!dateValue) return null;
  const parsed = new Date(dateValue);
  if (Number.isNaN(parsed.getTime())) return null;
  return FULL_DATE_FORMATTER.format(parsed);
}

function summarizeProposalOps(ops: Array<Record<string, unknown>> | undefined): ProposalDiffSummary {
  if (!ops || ops.length === 0) return { dayIds: [], weekIds: [], items: [] };

  const daySet = new Set<string>();
  const weekSet = new Set<string>();
  const items: DiffItem[] = [];

  for (const op of ops) {
    const opType = asString(op["op"]) ?? "unknown";

    if (opType === "upsert_day_block") {
      const dayId = asString(op["day_id"]) ?? "unknown day";
      daySet.add(dayId);
      items.push({
        scope: "day",
        target: dayId,
        action: "Add or update session",
        detail: describeBlock(op["block"]),
      });
      continue;
    }

    if (opType === "delete_day_block") {
      const dayId = asString(op["day_id"]) ?? "unknown day";
      daySet.add(dayId);
      const key = asString(op["key"]) ?? "unknown block";
      items.push({
        scope: "day",
        target: dayId,
        action: "Remove session",
        detail: `block "${key}"`,
      });
      continue;
    }

    if (opType === "replace_day_blocks") {
      const dayId = asString(op["day_id"]) ?? "unknown day";
      daySet.add(dayId);
      const blockCount = Array.isArray(op["blocks"]) ? op["blocks"].length : 0;
      items.push({
        scope: "day",
        target: dayId,
        action: "Replace day schedule",
        detail: `${blockCount} block${blockCount === 1 ? "" : "s"}`,
      });
      continue;
    }

    if (opType === "update_day_fields") {
      const dayId = asString(op["day_id"]) ?? "unknown day";
      daySet.add(dayId);
      const changes: string[] = [];
      if (hasOwnField(op, "day_label")) changes.push("label");
      if (hasOwnField(op, "workout_title")) changes.push("title");
      if (hasOwnField(op, "focus_type") || hasOwnField(op, "focus_color")) changes.push("focus");
      if (hasOwnField(op, "estimated_duration_min")) changes.push("duration");
      if (hasOwnField(op, "estimated_intensity")) changes.push("intensity");
      if (hasOwnField(op, "readiness_note")) changes.push("readiness");
      items.push({
        scope: "day",
        target: dayId,
        action: "Update day fields",
        detail: changes.length > 0 ? changes.join(", ") : "metadata",
      });
      continue;
    }

    if (opType === "upsert_week_notes_block") {
      const weekId = asString(op["week_id"]) ?? "unknown week";
      weekSet.add(weekId);
      items.push({
        scope: "week",
        target: weekId,
        action: "Add or update week note",
        detail: describeBlock(op["block"]),
      });
      continue;
    }

    if (opType === "delete_week_notes_block") {
      const weekId = asString(op["week_id"]) ?? "unknown week";
      weekSet.add(weekId);
      const key = asString(op["key"]) ?? "unknown block";
      items.push({
        scope: "week",
        target: weekId,
        action: "Remove week note",
        detail: `block "${key}"`,
      });
      continue;
    }

    items.push({
      scope: "plan",
      target: "overall",
      action: "Apply custom adjustment",
      detail: opType,
    });
  }

  return {
    dayIds: Array.from(daySet),
    weekIds: Array.from(weekSet),
    items,
  };
}

function findDay(plan: UiWeeklyPlan | null | undefined, dayId: string): LocatedDay | null {
  if (!plan) return null;
  for (const week of plan.weeks ?? []) {
    for (const day of week.days ?? []) {
      if (day.day_id === dayId) {
        return { week, day };
      }
    }
  }
  return null;
}

function findWeek(plan: UiWeeklyPlan | null | undefined, weekId: string): UiWeekPlan | null {
  if (!plan) return null;
  for (const week of plan.weeks ?? []) {
    if (week.week_id === weekId) return week;
  }
  return null;
}

function BlockStack({ blocks }: { blocks: UiHtmlBlock[] }) {
  if (blocks.length === 0) {
    return <div className="rounded-md border border-dashed border-white/10 bg-white/[0.03] px-2 py-2 text-[11px] text-[var(--text-muted)]">No blocks</div>;
  }
  return (
    <div className="space-y-2">
      {blocks.map((block) => (
        <div key={block.key} className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-2">
          {block.title ? <div className="text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">{block.title}</div> : null}
          <HtmlSnippet className="pv-content text-xs text-[var(--text-secondary)]" html={block.content_html} />
        </div>
      ))}
    </div>
  );
}

function truncateValue(value: string | null | undefined, maxLength = 120): string {
  const trimmed = value?.trim() ?? "";
  if (!trimmed) return "—";
  if (trimmed.length <= maxLength) return trimmed;
  return `${trimmed.slice(0, Math.max(0, maxLength - 1))}…`;
}

function formatDurationMinutes(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${value} min`;
}

function DayMetadataLines({ day }: { day: UiDayPlan | null | undefined }) {
  const label = truncateValue(day?.day_label ?? null, 48);
  const focusType = truncateValue(day?.focus_type ?? null, 24);
  const focusColor = day?.focus_color?.trim() ?? "";
  const duration = formatDurationMinutes(day?.estimated_duration_min ?? null);
  const intensity = truncateValue(day?.estimated_intensity ?? null, 24);
  const readiness = truncateValue(day?.readiness_note ?? null, 120);

  return (
    <div className="mb-2 space-y-0.5 text-[11px] text-[var(--text-secondary)]">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-[var(--text-muted)]">Label</span>
        <span className="text-right text-[var(--text-primary)]">{label}</span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-[var(--text-muted)]">Focus</span>
        <span className="flex items-center gap-1 text-right text-[var(--text-primary)]">
          <span>{focusType}</span>
          {focusColor ? <span className="h-2 w-2 rounded-full border border-white/10" style={{ backgroundColor: focusColor }} /> : null}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-[var(--text-muted)]">Duration</span>
        <span className="text-right text-[var(--text-primary)]">{duration}</span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-[var(--text-muted)]">Intensity</span>
        <span className="text-right text-[var(--text-primary)]">{intensity}</span>
      </div>
      <div className="flex items-start justify-between gap-2">
        <span className="mt-0.5 font-semibold text-[var(--text-muted)]">Readiness</span>
        <span className="text-right text-[var(--text-primary)]">{readiness}</span>
      </div>
    </div>
  );
}

function DayBeforeAfterCard({
  dayId,
  beforePlan,
  afterPlan,
}: {
  dayId: string;
  beforePlan: UiWeeklyPlan;
  afterPlan: UiWeeklyPlan;
}) {
  const before = findDay(beforePlan, dayId);
  const after = findDay(afterPlan, dayId);
  const displayLabel =
    after?.day.day_label ??
    before?.day.day_label ??
    after?.day.date ??
    before?.day.date ??
    dayId;
  const displayDate = after?.day.date ?? before?.day.date ?? "";
  const displayWeek = after?.week.week_label ?? before?.week.week_label ?? after?.week.week_id ?? before?.week.week_id ?? "";

  return (
    <div className="rounded-lg border border-emerald-400/25 bg-[linear-gradient(180deg,rgba(16,185,129,0.10),rgba(15,23,42,0.92))] p-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs font-semibold text-emerald-100">{displayLabel}</div>
        <div className="text-[11px] text-emerald-200/90">
          {displayWeek ? `${displayWeek} · ` : ""}
          {displayDate}
        </div>
      </div>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        <div>
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">Before</div>
          {before ? (
            <>
              <DayMetadataLines day={before.day} />
              <BlockStack blocks={before.day.blocks ?? []} />
            </>
          ) : (
            <div className="rounded-md border border-dashed border-white/10 bg-white/[0.03] px-2 py-2 text-[11px] text-[var(--text-muted)]">
              Day not found in base plan
            </div>
          )}
        </div>
        <div>
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">After</div>
          {after ? (
            <>
              <DayMetadataLines day={after.day} />
              <BlockStack blocks={after.day.blocks ?? []} />
            </>
          ) : (
            <div className="rounded-md border border-dashed border-white/10 bg-white/[0.03] px-2 py-2 text-[11px] text-[var(--text-muted)]">
              Day removed in preview
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WeekNotesBeforeAfterCard({
  weekId,
  beforePlan,
  afterPlan,
}: {
  weekId: string;
  beforePlan: UiWeeklyPlan;
  afterPlan: UiWeeklyPlan;
}) {
  const before = findWeek(beforePlan, weekId);
  const after = findWeek(afterPlan, weekId);
  const displayLabel = after?.week_label ?? before?.week_label ?? weekId;

  return (
    <div className="rounded-lg border border-emerald-400/25 bg-[linear-gradient(180deg,rgba(16,185,129,0.10),rgba(15,23,42,0.92))] p-2">
      <div className="text-xs font-semibold text-emerald-100">Week notes · {displayLabel}</div>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        <div>
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">Before</div>
          <BlockStack blocks={before?.notes_blocks ?? []} />
        </div>
        <div>
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">After</div>
          <BlockStack blocks={after?.notes_blocks ?? []} />
        </div>
      </div>
    </div>
  );
}

export function CoachAvatar({ size = "sm" }: { size?: "sm" | "md" }) {
  const sizeClassName = size === "md" ? "h-10 w-10 text-[11px]" : "h-7 w-7 text-[10px]";
  return (
    <span
      className={`inline-flex ${sizeClassName} items-center justify-center rounded-2xl border border-white/70 bg-gradient-to-br from-emerald-500 via-teal-500 to-sky-600 font-semibold tracking-[0.18em] text-white shadow-[0_10px_24px_rgba(14,116,144,0.28)]`}
      aria-label={COACH_NAME}
      title={COACH_NAME}
    >
      {COACH_INITIALS}
    </span>
  );
}

export function relativeTime(createdAt: string): string {
  const then = new Date(createdAt).getTime();
  if (Number.isNaN(then)) return "";
  const deltaMs = then - Date.now();
  const seconds = Math.round(deltaMs / 1000);
  const absSeconds = Math.abs(seconds);

  if (absSeconds < 60) return RELATIVE_TIME_FORMATTER.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return RELATIVE_TIME_FORMATTER.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return RELATIVE_TIME_FORMATTER.format(hours, "hour");
  const days = Math.round(hours / 24);
  return RELATIVE_TIME_FORMATTER.format(days, "day");
}

export function fullTime(createdAt: string): string {
  const d = new Date(createdAt);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function idempotencyKey(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}:${crypto.randomUUID()}`;
  }
  return `${prefix}:${Date.now()}`;
}

export function isCoachTurnResponse(value: unknown): value is CoachTurnResponse {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate["thread"] === "object" &&
    candidate["thread"] !== null &&
    typeof candidate["projection"] === "object" &&
    candidate["projection"] !== null
  );
}

export function trackCoachEvent(eventName: string, payload: Record<string, unknown> = {}) {
  if (typeof window === "undefined") return;

  const detail = { event: eventName, ...payload };
  window.dispatchEvent(new CustomEvent("coach-telemetry", { detail }));

  const withDataLayer = window as typeof window & { dataLayer?: Array<Record<string, unknown>> };
  if (Array.isArray(withDataLayer.dataLayer)) {
    withDataLayer.dataLayer.push({ event: eventName, ...payload });
  }
}

function labelDayTarget(dayId: string, beforePlan?: UiWeeklyPlan | null, afterPlan?: UiWeeklyPlan | null): string {
  const before = findDay(beforePlan, dayId);
  const after = findDay(afterPlan, dayId);
  const dayLabel = after?.day.day_label ?? before?.day.day_label ?? null;
  const dateLabel = formatDayDateLabel(after?.day.date ?? before?.day.date ?? dayId) ?? null;
  if (dayLabel && dateLabel) return `${dayLabel} (${dateLabel})`;
  if (dayLabel) return dayLabel;
  if (dateLabel) return dateLabel;
  return dayId;
}

function labelWeekTarget(weekId: string, beforePlan?: UiWeeklyPlan | null, afterPlan?: UiWeeklyPlan | null): string {
  const before = findWeek(beforePlan, weekId);
  const after = findWeek(afterPlan, weekId);
  return after?.week_label ?? before?.week_label ?? weekId;
}

export function ProposalCard({
  proposalId,
  ops,
  status,
  beforePlan,
  afterPlan,
  changesInitiallyOpen = true,
  visualDiffInitiallyOpen = true,
  busyAction,
  disabled,
  rejectReason,
  onRejectReasonChange,
  onAccept,
  onReject,
}: {
  proposalId: string;
  ops: Array<Record<string, unknown>>;
  status: string;
  beforePlan?: UiWeeklyPlan | null;
  afterPlan?: UiWeeklyPlan | null;
  changesInitiallyOpen?: boolean;
  visualDiffInitiallyOpen?: boolean;
  busyAction: BusyAction | null;
  disabled: boolean;
  rejectReason: string;
  onRejectReasonChange: (value: string) => void;
  onAccept: () => void;
  onReject: () => void;
}) {
  const diffSummary = useMemo(() => summarizeProposalOps(ops), [ops]);
  const dayLabels = useMemo(
    () => diffSummary.dayIds.map((dayId) => labelDayTarget(dayId, beforePlan, afterPlan)),
    [afterPlan, beforePlan, diffSummary.dayIds]
  );
  const weekLabels = useMemo(
    () => diffSummary.weekIds.map((weekId) => labelWeekTarget(weekId, beforePlan, afterPlan)),
    [afterPlan, beforePlan, diffSummary.weekIds]
  );
  const hasVisualSnapshot = Boolean(beforePlan && afterPlan);
  const normalizedStatus = status.trim().toLowerCase();
  const isPending = normalizedStatus === "pending";
  const isAccepted = normalizedStatus === "accepted";
  const isRejected = normalizedStatus === "rejected";
  const interactionDisabled = disabled || busyAction !== null || !isPending;

  const statusLabel = isAccepted ? "Accepted" : isRejected ? "Rejected" : isPending ? "Pending" : status;
  const statusClassName = isAccepted
    ? "border-emerald-400/25 bg-emerald-400/15 text-emerald-100"
    : isRejected
      ? "border-rose-400/25 bg-rose-400/15 text-rose-100"
      : "border-amber-400/25 bg-amber-400/15 text-amber-100";

  return (
    <div className="mt-2 rounded-xl border border-emerald-400/25 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.10),transparent_42%),linear-gradient(180deg,rgba(16,185,129,0.06),rgba(15,23,42,0.94))] p-3" data-proposal-id={proposalId}>
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-emerald-100">Proposal</div>
        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClassName}`}>
          {statusLabel}
        </span>
      </div>
      {diffSummary.items.length > 0 ? (
        <div className="mt-2 rounded-lg border border-emerald-400/20 bg-white/[0.05] px-2 py-2">
          <div className="flex items-center justify-between text-[11px] font-semibold text-emerald-100">
            <span>Plan impact</span>
            <span>{diffSummary.items.length} change{diffSummary.items.length === 1 ? "" : "s"}</span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-emerald-400/12">
            <div
              className="h-full rounded-full bg-emerald-500 transition-[width] duration-300"
              style={{ width: `${Math.min(100, 24 + diffSummary.items.length * 14)}%` }}
            />
          </div>
        </div>
      ) : null}
      {(diffSummary.dayIds.length > 0 || diffSummary.weekIds.length > 0) ? (
        <div className="mt-1 space-y-0.5 text-xs text-emerald-100">
          {dayLabels.length > 0 ? <div>Days: {compactLabelList(dayLabels)}</div> : null}
          {weekLabels.length > 0 ? <div>Weeks: {compactLabelList(weekLabels)}</div> : null}
        </div>
      ) : null}
      {diffSummary.items.length > 0 ? (
        <details className="mt-2 rounded-md border border-emerald-400/20 bg-white/[0.05] p-2" open={changesInitiallyOpen}>
          <summary className="cursor-pointer text-xs font-semibold text-emerald-100">
            Proposed changes ({diffSummary.items.length})
          </summary>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-[var(--text-secondary)]">
            {diffSummary.items.map((item, index) => (
              <li key={`${item.scope}:${item.target}:${item.action}:${index}`}>
                <span className="font-semibold">
                  {item.scope === "day"
                    ? labelDayTarget(item.target, beforePlan, afterPlan)
                    : item.scope === "week"
                      ? labelWeekTarget(item.target, beforePlan, afterPlan)
                      : item.target}
                </span>
                : {item.action} ({item.detail})
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      {(diffSummary.dayIds.length > 0 || diffSummary.weekIds.length > 0) ? (
        <details className="mt-2 rounded-md border border-emerald-400/20 bg-white/[0.05] p-2" open={visualDiffInitiallyOpen}>
          <summary className="cursor-pointer text-xs font-semibold text-emerald-100">Visual before vs after</summary>
          {hasVisualSnapshot && beforePlan && afterPlan ? (
            <div className="mt-2 space-y-2">
              {diffSummary.dayIds.map((dayId) => (
                <DayBeforeAfterCard key={`day:${dayId}`} dayId={dayId} beforePlan={beforePlan} afterPlan={afterPlan} />
              ))}
              {diffSummary.weekIds.map((weekId) => (
                <WeekNotesBeforeAfterCard key={`week:${weekId}`} weekId={weekId} beforePlan={beforePlan} afterPlan={afterPlan} />
              ))}
            </div>
          ) : (
            <div className="mt-2 rounded-md border border-dashed border-white/10 bg-white/[0.03] px-2 py-2 text-[11px] text-[var(--text-secondary)]">
              Snapshot unavailable for this proposal (older proposals may not include full before/after payload).
            </div>
          )}
        </details>
      ) : null}
      {isAccepted ? (
        <div className="mt-2 rounded-md border border-emerald-400/20 bg-white/[0.04] px-2.5 py-2 text-xs text-emerald-100">
          Applied to your active training block.
        </div>
      ) : null}
      {isRejected ? (
        <div className="mt-2 rounded-md border border-rose-400/20 bg-white/[0.04] px-2.5 py-2 text-xs text-rose-100">
          Rejected. Ask the coach for an alternative adjustment.
        </div>
      ) : null}
      <div className="mt-2 flex items-center gap-2">
        <button
          className="rounded-md bg-[linear-gradient(135deg,rgba(56,189,248,0.92),rgba(16,185,129,0.88))] px-3 py-1.5 text-xs font-semibold text-slate-950 disabled:opacity-60"
          disabled={interactionDisabled}
          type="button"
          onClick={onAccept}
        >
          {busyAction === "accept" ? "Accepting..." : "Accept"}
        </button>
        <button
          className="rounded-md border border-emerald-400/25 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-emerald-100 disabled:opacity-60"
          disabled={interactionDisabled}
          type="button"
          onClick={onReject}
        >
          {busyAction === "reject" ? "Rejecting..." : "Reject"}
        </button>
      </div>
      {!isAccepted ? (
        <div className="mt-2 space-y-2">
          <div className="flex flex-wrap gap-1.5">
            {REJECT_REASON_SUGGESTIONS.map((reasonOption) => (
              <button
                key={reasonOption}
                className="rounded-full border border-emerald-400/20 bg-white/[0.04] px-2 py-1 text-[11px] text-emerald-100 transition hover:bg-white/[0.08] disabled:opacity-60"
                disabled={interactionDisabled}
                type="button"
                onClick={() => onRejectReasonChange(reasonOption)}
              >
                {reasonOption}
              </button>
            ))}
          </div>
          <textarea
            className="w-full rounded-md border border-white/10 bg-[var(--surface-elevated)]/88 px-3 py-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
            disabled={interactionDisabled}
            placeholder="Reason if you reject this"
            rows={2}
            value={rejectReason}
            onChange={(event) => onRejectReasonChange(event.target.value)}
          />
        </div>
      ) : null}
    </div>
  );
}

export function RecapMessage({
  message,
  quotaBlocked,
  busyAction,
  onAcceptProposal,
  onRejectProposal,
  baseWeeklyPlan,
  previewWeeklyPlan,
  proposalStatus,
  rejectReason,
  onRejectReasonChange,
}: {
  message: Extract<CoachThreadMessage, { kind: "recap" }>;
  quotaBlocked: boolean;
  busyAction: BusyAction | null;
  onAcceptProposal: (proposalId: string) => void;
  onRejectProposal: (proposalId: string) => void;
  baseWeeklyPlan?: UiWeeklyPlan | null;
  previewWeeklyPlan?: UiWeeklyPlan | null;
  proposalStatus: string;
  rejectReason: string;
  onRejectReasonChange: (value: string) => void;
}) {
  const recap = message.recap;
  const sections = [
    { label: "This week", blocks: recap.narrative.this_week_blocks ?? [] },
    { label: "Looking ahead", blocks: recap.narrative.looking_ahead_blocks ?? [] },
  ].filter((section) => section.blocks.length > 0);

  return (
    <div className="rounded-2xl border border-sky-400/25 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.10),transparent_42%),linear-gradient(180deg,rgba(56,189,248,0.06),rgba(15,23,42,0.94))] p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-sky-100">Weekly recap</div>
        <span className="rounded-full border border-sky-400/25 bg-sky-400/12 px-2 py-0.5 text-[10px] font-semibold text-sky-100">
          Coach summary
        </span>
      </div>
      <div className="mt-2 space-y-2 rounded-lg border border-sky-400/20 bg-white/[0.05] p-2">
        {sections.map((section) => (
          <div key={`${message.id}-${section.label}`}>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">{section.label}</div>
            <div className="mt-1 space-y-1">
              {section.blocks.map((block) => (
                <div key={block.key} className="rounded-md bg-white/[0.04] px-2 py-1.5">
                  {block.title ? (
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">{block.title}</div>
                  ) : null}
                  <HtmlSnippet className="pv-content text-xs text-[var(--text-secondary)]" html={block.content_html} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {recap.proposal_id ? (
        <ProposalCard
          proposalId={recap.proposal_id}
          ops={recap.ops ?? []}
          status={proposalStatus}
          beforePlan={baseWeeklyPlan}
          afterPlan={previewWeeklyPlan}
          changesInitiallyOpen={false}
          visualDiffInitiallyOpen={false}
          busyAction={busyAction}
          disabled={quotaBlocked}
          rejectReason={rejectReason}
          onRejectReasonChange={onRejectReasonChange}
          onAccept={() => onAcceptProposal(recap.proposal_id ?? "")}
          onReject={() => onRejectProposal(recap.proposal_id ?? "")}
        />
      ) : null}
    </div>
  );
}

export function threadTitle(
  threadId: string | null,
  title?: string | null,
  signals?: CoachThreadSignals
): string {
  if (!threadId) return "New coaching topic";
  if (title && title.trim()) return title.trim();
  if (signals?.source === "weekly_recap") return "Weekly Recap";
  if (signals?.source === "proactive") return "Coach Alert";
  return signals?.previewText?.slice(0, 40) || "Coaching conversation";
}

export function sourceEmoji(source: CoachThreadSignals["source"] | undefined): string {
  if (source === "weekly_recap") return "\u{1F4CA}";
  if (source === "proactive") return "\u26A1";
  return "\u{1F4AC}";
}

export function showLowQuotaWarning(quota: CoachQuota | null): boolean {
  if (!quota || !quota.is_limited || quota.remaining == null) return false;
  return quota.remaining <= 5;
}

export function buildThreadUrl(threadId: string | null): string {
  if (!threadId) return "/app/api/coach/thread";
  return `/app/api/coach/thread?thread_id=${encodeURIComponent(threadId)}`;
}
