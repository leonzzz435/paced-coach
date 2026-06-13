"use client";

import { useMemo, useState, useTransition } from "react";
import Link from "next/link";
import { getCurrentWeekIndex, localYYYYMMDD } from "@/lib/date-utils";
import { getPrimaryWorkoutTitle } from "@/lib/day-display";
import { toggleDayCompletionAction } from "@/app/actions/plan";
import type { UiWeeklyPlan, UiDayPlan, UiHtmlBlock } from "@/lib/types/ui-blocks";
import { Check } from "lucide-react";

type Props = {
    weeklyPlan: UiWeeklyPlan | undefined;
};

function formatHoursMinutes(totalMin: number): string {
    const hours = Math.floor(totalMin / 60);
    const minutes = totalMin % 60;
    if (hours === 0) return `${minutes}m`;
    if (minutes === 0) return `${hours}h`;
    return `${hours}h ${minutes}m`;
}

function dayAbbrev(dateStr: string): string {
    if (!dateStr) return "";
    const ms = new Date(`${dateStr}T00:00:00Z`).getTime();
    if (Number.isNaN(ms)) return dateStr.slice(5);
    return new Date(ms).toLocaleDateString("en-US", { weekday: "short", timeZone: "UTC" });
}

function dayNumber(dateStr: string): string {
    if (!dateStr) return "";
    const ms = new Date(`${dateStr}T00:00:00Z`).getTime();
    if (Number.isNaN(ms)) return "";
    return new Date(ms).toLocaleDateString("en-US", { day: "numeric", timeZone: "UTC" });
}

export default function WeekStrip({ weeklyPlan }: Props) {
    const todayIso = useMemo(() => localYYYYMMDD(), []);
    const [completedMap, setCompletedMap] = useState<Record<string, boolean>>({});
    const [, startTransition] = useTransition();

    const isDayDone = (day: UiDayPlan): boolean => {
        if (completedMap[day.day_id] !== undefined) return completedMap[day.day_id];
        if (day.is_completed !== undefined) return day.is_completed;
        const isPast = day.date < todayIso;
        return isPast && day.estimated_intensity !== "rest";
    };

    const toggleCompletion = (e: React.MouseEvent, day: UiDayPlan) => {
        e.preventDefault();
        e.stopPropagation();
        const currentStatus = isDayDone(day);
        setCompletedMap((prev) => ({ ...prev, [day.day_id]: !currentStatus }));
        startTransition(async () => {
            try {
                await toggleDayCompletionAction(day.day_id, !currentStatus);
            } catch (err) {
                console.error("Failed to persist checkmark:", err);
                setCompletedMap((prev) => {
                    const next = { ...prev };
                    delete next[day.day_id];
                    return next;
                });
            }
        });
    };

    const week = useMemo(() => {
        if (!weeklyPlan) return null;
        const idx = getCurrentWeekIndex(weeklyPlan, new Date(todayIso));
        return weeklyPlan.weeks[idx] ?? null;
    }, [weeklyPlan, todayIso]);

    const weekTotalMin = useMemo(() => {
        if (!week?.days) return null;
        const total = week.days.reduce((sum, day) => sum + (day.estimated_duration_min ?? 0), 0);
        return total > 0 ? total : null;
    }, [week]);

    if (!week || !week.days) return null;

    return (
        <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-3">
                    <h3 className="text-sm font-semibold text-[var(--text-secondary)]">This Week</h3>
                    {weekTotalMin ? (
                        <span className="text-sm font-semibold font-mono tabular-nums text-[var(--text-primary)]">{formatHoursMinutes(weekTotalMin)}</span>
                    ) : null}
                </div>
                <Link href="/app/plan" className="text-xs font-bold text-[var(--accent-primary)] hover:text-[var(--accent-primary)]/80">
                    View full plan →
                </Link>
            </div>

            <div className="flex w-full snap-x snap-mandatory overflow-x-auto overscroll-x-contain pb-4 pt-4 px-2 -mx-2 scrollbar-none lg:mx-0 lg:px-0 lg:grid lg:grid-cols-7 lg:gap-4 lg:pb-0 lg:pt-2 lg:-mt-2 lg:overflow-visible">
                {week.days.slice(0, 7).map((day) => {
                    const isToday = day.date === todayIso;
                    const isPast = day.date < todayIso;
                    const isRest = day.estimated_intensity === "rest";
                    const workoutBlocks = (day.blocks || []).filter((b: UiHtmlBlock) => b.variant === "workout");

                    const fallbackTitle = getPrimaryWorkoutTitle(day);
                    const hasSession = !isRest && (workoutBlocks.length > 0 || fallbackTitle || day.estimated_duration_min || day.estimated_intensity);
                    const done = hasSession && isDayDone(day);

                    // Card wrapper styles
                    let cardBase = "relative flex flex-col justify-between shrink-0 snap-center w-[160px] lg:w-auto h-32 rounded-2xl border p-3 transition-transform hover:scale-[1.02] active:scale-95";

                    if (isToday) {
                        cardBase += " border-[var(--accent-primary)] bg-[var(--surface-elevated)] ring-1 ring-[var(--accent-primary)] shadow-md transform scale-105 z-10 lg:scale-[1.05]";
                    } else if (done) {
                        cardBase += " border-[var(--accent-success)]/20 bg-[var(--accent-success)]/5 opacity-80 hover:opacity-100";
                    } else if (isPast) {
                        cardBase += " border-[var(--border)] bg-[var(--surface)] opacity-50 hover:opacity-80";
                    } else {
                        cardBase += " border-[var(--border)] bg-[var(--surface)] shadow-sm hover:border-[var(--border-accent)]";
                    }

                    return (
                        <Link key={day.day_id} href={`/app/plan`} className={cardBase} style={!isPast && !done && day.focus_color ? { borderBottomWidth: '4px', borderBottomColor: day.focus_color } : {}}>
                            <div className="flex items-start justify-between">
                                <div className="flex flex-col">
                                    <span className={`text-[10px] font-semibold ${isToday ? 'text-[var(--accent-primary)]' : 'text-[var(--text-muted)]'}`}>
                                        {dayAbbrev(day.date)}
                                    </span>
                                    <span className={`text-xl font-extrabold tracking-tight ${isToday ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>
                                        {dayNumber(day.date)}
                                    </span>
                                </div>
                                {hasSession && (
                                    <button
                                        type="button"
                                        onClick={(e) => toggleCompletion(e, day)}
                                        className={`
                                            flex items-center justify-center w-6 h-6 rounded-md border-[1.5px] shrink-0 transition-all
                                            ${done
                                                ? "bg-[var(--accent-success)] border-[var(--accent-success)] text-white hover:brightness-110"
                                                : "bg-[var(--surface)] border-[var(--border-accent)] text-transparent hover:border-[var(--accent-success)] hover:text-[var(--accent-success)] hover:bg-[var(--accent-success)]/10"
                                            }
                                        `}
                                        title={done ? "Mark as not done" : "Mark as done"}
                                    >
                                        <Check className={`w-3.5 h-3.5 stroke-[3] ${done ? "visible" : "invisible group-hover:visible"}`} />
                                    </button>
                                )}
                            </div>

                            <div className="flex flex-col gap-1.5 mt-auto">
                                {isRest ? (
                                    <span className="inline-flex w-fit items-center rounded-md bg-[var(--surface-elevated)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-muted)]">
                                        Rest
                                    </span>
                                ) : (
                                    <>
                                        {workoutBlocks.length > 0 ? (
                                            <div className="flex flex-col gap-1">
                                                {workoutBlocks.map((wb, idx) => (
                                                    <span
                                                        key={`${day.date}-${wb.key || idx}`}
                                                        className={`truncate text-xs font-bold leading-tight ${done ? 'text-[var(--text-dim)] line-through' : 'text-[var(--text-primary)]'}`}
                                                        style={isToday && day.focus_color && !done ? { color: day.focus_color } : {}}
                                                    >
                                                        {wb.title || fallbackTitle || "Workout"}
                                                    </span>
                                                ))}
                                            </div>
                                        ) : fallbackTitle && (
                                            <span
                                                className={`truncate text-xs font-bold leading-tight ${done ? 'text-[var(--text-dim)] line-through' : 'text-[var(--text-primary)]'}`}
                                                style={isToday && day.focus_color && !done ? { color: day.focus_color } : {}}
                                            >
                                                {fallbackTitle}
                                            </span>
                                        )}
                                        <div className="flex items-center gap-2 text-[11px] font-semibold text-[var(--text-muted)]">
                                            {day.estimated_duration_min && <span>{day.estimated_duration_min}m</span>}
                                            {day.estimated_duration_min && day.estimated_intensity && <span>•</span>}
                                            {day.estimated_intensity && <span className="capitalize">{day.estimated_intensity.replace('_', ' ')}</span>}
                                        </div>
                                    </>
                                )}
                            </div>

                            {isToday && (
                                <div className="absolute -top-3 right-3 rounded-full bg-[var(--accent-primary)] px-2.5 py-0.5 text-[9px] font-bold text-white shadow-sm z-20">
                                    Today
                                </div>
                            )}
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}
