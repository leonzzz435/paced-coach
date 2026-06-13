"use client";

import { useMemo } from "react";
import BlockDisclosure from "@/components/plan-viewer/components/block-disclosure";
import { localYYYYMMDD } from "@/lib/date-utils";
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
  weeklyPlan: UiWeeklyPlan;
  warnings?: string[];
  dayOverride?: UiDayPlan;
  dailySyncCompleted?: boolean;
};

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

export default function TodayMission({ weeklyPlan, warnings = [], dayOverride, dailySyncCompleted }: Props) {
  const todayIso = useMemo(() => localYYYYMMDD(), []);
  const todayEntry = useMemo(() => findTodayEntry(weeklyPlan, todayIso, dayOverride), [dayOverride, todayIso, weeklyPlan]);
  const today = todayEntry?.day ?? null;
  const todayWeek = todayEntry?.week ?? null;

  const isEvening = new Date().getHours() >= 18;
  const isRestDay = Boolean(
    today &&
    (today.estimated_intensity === "rest" || (!today.focus_type && (today.blocks?.length ?? 0) === 0 && (today.nodes?.length ?? 0) === 0))
  );

  const accent = accentForIntensity(today?.estimated_intensity ?? null, isRestDay);

  const headerLabel = today?.day_label ?? (isRestDay ? "Recovery Day" : "Session TBD");
  const durationBadge = today?.estimated_duration_min != null ? `${today.estimated_duration_min} min` : isRestDay ? "Rest" : "Duration TBD";
  const readinessNote = today?.readiness_note?.trim() ?? null;

  const askCoachPrefill = today
    ? {
        message: `Today (${today.day_label ?? today.date}): assess my readiness (GO / MODIFY / PROTECT) for this session and propose plan patch ops if needed.`,
        uiContext: {
          source: "today_mission" as const,
          day_id: today.day_id,
          week_id: todayWeek?.week_id ?? null,
          date: today.date,
          day_label: today.day_label ?? null,
          workout_title: today.workout_title ?? null,
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
                  {intensityLabel(today?.estimated_intensity ?? null)}
                </span>
              )}
            </div>
          </div>

          <button
            type="button"
            className="shrink-0 self-start rounded-full bg-[var(--accent-coach)] px-5 py-2.5 text-sm font-bold text-white shadow-sm transition-transform hover:scale-105 hover:brightness-110 active:scale-95 outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-coach)] focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
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

          {today ? (
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
