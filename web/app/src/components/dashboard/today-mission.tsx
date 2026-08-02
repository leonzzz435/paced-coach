"use client";

import Link from "next/link";
import { useMemo } from "react";
import BlockDisclosure from "@/components/plan-viewer/components/block-disclosure";
import MarkdownSnippet from "@/components/markdown_snippet";
import type { WeeklyPlanV3 } from "@/components/plan-viewer/types";
import { athleteLocalYYYYMMDD } from "@/lib/date-utils";
import { openCoachWithPrefill } from "@/lib/types/ask-about";
import type { UiDayPlan, UiDisclosureNode, UiHtmlBlock, UiWeeklyPlan } from "@/lib/types/ui-blocks";

function getAllBlocks(day: UiDayPlan): UiHtmlBlock[] {
  if (day.blocks && day.blocks.length > 0) return day.blocks;
  if (day.nodes && day.nodes.length > 0) {
    const blocks: UiHtmlBlock[] = [];
    const extract = (nodes: UiDisclosureNode[]) => {
      for (const n of nodes) {
        blocks.push(...n.blocks);
        if (n.children) extract(n.children);
      }
    };
    extract(day.nodes);
    return blocks;
  }
  return [];
}

function intensityLabel(value: UiDayPlan["estimated_intensity"]): string {
  if (!value) return "Intensity TBD";
  if (value === "very_high") return "Very high";
  return value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, " ");
}

function accentForIntensity(intensity: UiDayPlan["estimated_intensity"] | null, isRest: boolean): string {
  if (isRest) return "#64748b";
  switch (intensity) {
    case "very_high": return "#f43f5e";
    case "high": return "#f97316";
    case "moderate": return "#f59e0b";
    case "low":
    default: return "#22c55e";
  }
}

type Props = {
  weeklyPlan: UiWeeklyPlan | WeeklyPlanV3;
  warnings?: string[];
  dayOverride?: UiDayPlan;
  dailySyncCompleted?: boolean;
  nowIso?: string;
};

type V3Day = WeeklyPlanV3["weeks"][number]["days"][number];
type V3Week = WeeklyPlanV3["weeks"][number];

function isWeeklyPlanV3(plan: UiWeeklyPlan | WeeklyPlanV3): plan is WeeklyPlanV3 {
  return plan.schema_version === 3 && "summary_markdown" in plan;
}

function findV3TodayEntry(weeklyPlan: WeeklyPlanV3, todayIso: string): { week: V3Week; day: V3Day } | null {
  for (const week of weeklyPlan.weeks) {
    const day = week.days.find((candidate) => candidate.date === todayIso);
    if (day) return { week, day };
  }
  return null;
}

function athleteLocalHour(nowIso?: string): number {
  const hour = nowIso?.match(/^\d{4}-\d{2}-\d{2}T(\d{2})/)?.[1];
  return hour == null ? new Date().getHours() : Number(hour);
}

function findTodayEntry(weeklyPlan: UiWeeklyPlan, todayIso: string, dayOverride?: UiDayPlan | null) {
  for (const week of weeklyPlan.weeks ?? []) {
    for (const day of week.days ?? []) {
      const matchesOverride =
        dayOverride && ((dayOverride.day_id && day.day_id === dayOverride.day_id) || day.date === dayOverride.date);
      if (matchesOverride || day.date === todayIso) {
        return {
          week,
          day: dayOverride ?? day,
        };
      }
    }
  }
  return null;
}

export default function TodayMission({ weeklyPlan, warnings = [], dayOverride, dailySyncCompleted, nowIso }: Props) {
  const todayIso = athleteLocalYYYYMMDD(nowIso);
  const v3Entry = useMemo(
    () => (isWeeklyPlanV3(weeklyPlan) ? findV3TodayEntry(weeklyPlan, todayIso) : null),
    [todayIso, weeklyPlan],
  );
  const overrideMatchesToday = Boolean(
    dayOverride &&
      (dayOverride.date === todayIso || (dayOverride.day_id && dayOverride.day_id === v3Entry?.day.day_id)),
  );
  const legacyEntry = useMemo(
    () => (isWeeklyPlanV3(weeklyPlan) ? null : findTodayEntry(weeklyPlan, todayIso, dayOverride)),
    [dayOverride, todayIso, weeklyPlan],
  );
  const v3Day = overrideMatchesToday ? null : v3Entry?.day ?? null;
  const v3Week = overrideMatchesToday ? null : v3Entry?.week ?? null;
  const today = overrideMatchesToday ? dayOverride ?? null : legacyEntry?.day ?? null;
  const todayWeek = legacyEntry?.week ?? v3Week;

  const isEvening = athleteLocalHour(nowIso) >= 18;
  const isRestDay = Boolean(
    v3Day?.intensity === "rest" ||
      (today &&
        (today.estimated_intensity === "rest" ||
          (!today.focus_type && (today.blocks?.length ?? 0) === 0 && (today.nodes?.length ?? 0) === 0)))
  );

  const accent = accentForIntensity(today?.estimated_intensity ?? v3Day?.intensity ?? null, isRestDay);

  const headerLabel = today?.day_label ?? v3Day?.sessions[0]?.title ?? v3Day?.label ?? (isRestDay ? "Recovery Day" : "Session TBD");
  const duration = today?.estimated_duration_min ?? v3Day?.total_duration_min;
  const durationBadge = duration != null ? (duration === 0 ? "Rest" : `${duration} min`) : isRestDay ? "Rest" : "Duration TBD";
  const readinessNote = today?.readiness_note?.trim() ?? null;

  const actionableDate = today?.date ?? v3Day?.date;
  const actionableDayId = today?.day_id ?? v3Day?.day_id;
  const actionableLabel = today?.day_label ?? v3Day?.label;
  const actionableWorkoutTitle = today?.workout_title ?? v3Day?.sessions[0]?.title;
  const askCoachPrefill = actionableDate && actionableDayId
    ? {
        message: `Today (${actionableLabel ?? actionableDate}): assess my readiness (GO / MODIFY / PROTECT) for this session and propose plan patch ops if needed.`,
        uiContext: {
          source: "today_mission" as const,
          day_id: actionableDayId,
          week_id: todayWeek?.week_id ?? null,
          date: actionableDate,
          day_label: actionableLabel ?? null,
          workout_title: actionableWorkoutTitle ?? null,
        },
      }
    : {
        message: `Today (${todayIso}): assess my readiness (GO / MODIFY / PROTECT) and propose plan patch ops if needed.`,
      };

  const allBlocks = today ? getAllBlocks(today) : [];
  const blocks = dailySyncCompleted
    ? allBlocks.filter((b) => !b.title?.toLowerCase().includes("readiness"))
    : allBlocks;

  return (
    <section
      className="flex h-full flex-col rounded-2xl border-l-[3px] bg-[var(--surface)] p-6 sm:p-8 lg:p-10 text-[var(--text-primary)] [&_.pv-ask-button]:hidden shadow-sm overflow-hidden relative"
      style={{ borderLeftColor: accent }}
    >
      <div className="relative z-10 flex flex-col h-full min-h-0">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 shrink-0">
          <div className="min-w-0">
            <div className="text-xs font-semibold text-[var(--text-muted)]">
              {isEvening && !isRestDay ? "Evening Review" : "Today’s Mission"}
            </div>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl text-[var(--text-primary)]">{headerLabel}</h2>

            <div className="mt-4 flex flex-wrap items-center gap-2 mb-6">
              <span className="rounded-lg border border-[var(--border)] bg-[var(--surface-elevated)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]">
                {durationBadge}
              </span>
              {!isRestDay && (
                <span className="rounded-lg border border-[var(--border)] bg-[var(--surface-elevated)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]">
                  {intensityLabel(today?.estimated_intensity ?? v3Day?.intensity ?? null)}
                </span>
              )}
            </div>
          </div>

          <button
            type="button"
            className="min-h-11 shrink-0 self-start rounded-full bg-[var(--accent-coach)] px-5 py-2.5 text-sm font-bold text-white shadow-sm transition-transform hover:scale-105 hover:brightness-110 active:scale-95 outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-coach)] focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
            onClick={() => openCoachWithPrefill(askCoachPrefill)}
          >
            Ask Coach
          </button>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto pr-2 -mr-2 space-y-4 pb-2">
          {warnings.length > 0 ? (
            <div className="rounded-2xl bg-[var(--surface-elevated)] p-4 border border-[var(--border)]">
              <div className="text-xs font-semibold text-[var(--text-muted)] mb-2">Before you train</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm font-medium text-[var(--text-secondary)]">
                {warnings.map((w) => <li key={w}>{w}</li>)}
              </ul>
            </div>
          ) : null}

          {readinessNote ? (
            <div className="rounded-2xl p-5 border border-[var(--border)] bg-[var(--surface-elevated)] shadow-sm">
              <div className="text-xs font-semibold text-[var(--text-muted)] mb-2">
                Coach Note
              </div>
              <p className="text-sm font-medium leading-relaxed text-[var(--text-primary)]">{readinessNote}</p>
            </div>
          ) : null}

          {v3Day ? (
            <div className="mt-2 space-y-4">
              {v3Day.sessions.length > 0 ? (
                v3Day.sessions.map((session) => (
                  <article key={session.session_id} className="rounded-2xl border border-[var(--border)] bg-[var(--surface-elevated)] p-5 shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{session.sport}</div>
                      <div className="text-xs tabular-nums text-[var(--text-muted)]">{session.duration_min} min</div>
                    </div>
                    <h3 className="mt-2 text-base font-semibold text-[var(--text-primary)]">{session.title}</h3>
                    <MarkdownSnippet markdown={session.objective_markdown} className="mt-2 text-sm leading-6 text-[var(--text-secondary)]" />
                    <details className="group mt-3 border-t border-[var(--border)] pt-3">
                      <summary className="cursor-pointer text-sm font-semibold text-sky-300">Show prescription</summary>
                      <MarkdownSnippet markdown={session.prescription_markdown} className="mt-2 text-sm leading-6 text-[var(--text-secondary)]" />
                    </details>
                  </article>
                ))
              ) : (
                <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-elevated)] p-5 text-sm leading-6 text-[var(--text-secondary)]">
                  This is a planned recovery day. Protect the recovery intent and use the full plan for the coach&apos;s context.
                </div>
              )}
              <Link className="inline-flex text-sm font-semibold text-sky-300 transition hover:text-sky-200" href="/app/plan">
                Open full 28-day plan →
              </Link>
            </div>
          ) : today ? (
            blocks.length > 0 ? (
              <div className="mt-6 flex flex-col gap-6">
                {blocks.map((block) => (
                  <div key={block.key}>
                    <div className="text-xs font-semibold text-[var(--text-muted)] mb-2">
                      {block.title || block.variant}
                    </div>
                    <BlockDisclosure
                      block={block}
                      sourceTab="weekly"
                      parentLabel={headerLabel}
                      collapsible={false}
                      compact={true}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-6 text-sm font-medium text-[var(--text-muted)] italic">
                No specific structured workflow required for today&apos;s session.
              </div>
            )
          ) : (
            <div className="mt-6 flex h-32 items-center justify-center rounded-2xl border-2 border-dashed border-[var(--border-accent)] text-[var(--text-muted)] text-sm font-medium">
              No session active. Tap &quot;Ask Coach&quot; to generate a plan.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
