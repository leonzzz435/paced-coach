"use client";

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";

import DisclosureNodeTree, { blocksToFallbackNodes } from "@/components/plan-viewer/components/disclosure-node-tree";
import type { PlanViewMode, WeeklyPlanTheme } from "@/components/plan-viewer/types";
import { useCheckboxState } from "@/lib/hooks/use-checkbox-state";
import { type OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiDayPlan, UiHtmlBlock, UiWeeklyPlan } from "@/lib/types/ui-blocks";

type Props = {
    weeklyPlan: UiWeeklyPlan;
    highlightDayIds?: string[];
    onAskAboutBlock?: OnAskAboutBlock;
    theme?: WeeklyPlanTheme;
    mode?: PlanViewMode;
};

type WeeklyThemeStyle = CSSProperties & {
    [key: `--${string}`]: string | number | undefined;
    "--surface": string;
    "--surface-elevated": string;
    "--card": string;
    "--border": string;
    "--border-accent": string;
    "--text-primary": string;
    "--text-secondary": string;
    "--text-muted": string;
    "--wp-brief-gradient": string;
    "--wp-card-shadow": string;
    "--wp-panel-border": string;
    "--wp-surface": string;
    "--wp-surface-elevated": string;
    "--wp-note-surface": string;
    "--wp-detail-surface": string;
    "--wp-text-primary": string;
    "--wp-text-secondary": string;
    "--wp-text-muted": string;
    "--wp-progress-track": string;
    "--wp-intensity-active": string;
    "--wp-intensity-idle": string;
    "--wp-check-idle-bg": string;
    "--wp-check-idle-text": string;
    "--wp-check-done-bg": string;
    "--wp-check-done-border": string;
    "--wp-check-done-text": string;
};

const WEEKLY_THEME_STYLES: Record<WeeklyPlanTheme, WeeklyThemeStyle> = {
    light: {
        "--surface": "#ffffff",
        "--surface-elevated": "#f5f7fb",
        "--card": "#ffffff",
        "--border": "rgba(212, 212, 216, 0.72)",
        "--border-accent": "rgba(59, 130, 246, 0.22)",
        "--text-primary": "#18181b",
        "--text-secondary": "#3f3f46",
        "--text-muted": "#71717a",
        "--wp-brief-gradient": "linear-gradient(135deg, rgba(255,255,255,1), rgba(248,250,252,1) 58%, rgba(236,253,245,0.92) 100%)",
        "--wp-card-shadow": "0 10px 24px rgba(15, 23, 42, 0.06)",
        "--wp-panel-border": "rgba(212, 212, 216, 0.72)",
        "--wp-surface": "#ffffff",
        "--wp-surface-elevated": "rgba(244, 244, 245, 0.72)",
        "--wp-note-surface": "rgba(244, 244, 245, 0.72)",
        "--wp-detail-surface": "rgba(250, 250, 250, 0.88)",
        "--wp-text-primary": "#18181b",
        "--wp-text-secondary": "#3f3f46",
        "--wp-text-muted": "#71717a",
        "--wp-progress-track": "#e4e4e7",
        "--wp-intensity-active": "#27272a",
        "--wp-intensity-idle": "#d4d4d8",
        "--wp-check-idle-bg": "#ffffff",
        "--wp-check-idle-text": "#71717a",
        "--wp-check-done-bg": "rgba(16, 185, 129, 0.12)",
        "--wp-check-done-border": "rgba(16, 185, 129, 0.35)",
        "--wp-check-done-text": "#047857",
    },
    dark: {
        "--surface": "rgba(11, 16, 27, 0.94)",
        "--surface-elevated": "rgba(15, 23, 42, 0.88)",
        "--card": "rgba(15, 23, 42, 0.82)",
        "--border": "rgba(148, 163, 184, 0.16)",
        "--border-accent": "rgba(96, 165, 250, 0.28)",
        "--text-primary": "#f8fafc",
        "--text-secondary": "#cbd5e1",
        "--text-muted": "#94a3b8",
        "--wp-brief-gradient": "radial-gradient(circle at top left, rgba(139,92,246,0.16), transparent 36%), linear-gradient(180deg, rgba(11,16,27,0.98), rgba(15,23,42,0.96))",
        "--wp-card-shadow": "0 18px 40px rgba(2, 6, 23, 0.28)",
        "--wp-panel-border": "rgba(148, 163, 184, 0.16)",
        "--wp-surface": "rgba(11, 16, 27, 0.9)",
        "--wp-surface-elevated": "rgba(15, 23, 42, 0.82)",
        "--wp-note-surface": "rgba(15, 23, 42, 0.72)",
        "--wp-detail-surface": "rgba(15, 23, 42, 0.74)",
        "--wp-text-primary": "#f8fafc",
        "--wp-text-secondary": "#cbd5e1",
        "--wp-text-muted": "#94a3b8",
        "--wp-progress-track": "rgba(148, 163, 184, 0.18)",
        "--wp-intensity-active": "#f8fafc",
        "--wp-intensity-idle": "rgba(148, 163, 184, 0.36)",
        "--wp-check-idle-bg": "rgba(15, 23, 42, 0.82)",
        "--wp-check-idle-text": "#cbd5e1",
        "--wp-check-done-bg": "rgba(16, 185, 129, 0.16)",
        "--wp-check-done-border": "rgba(52, 211, 153, 0.35)",
        "--wp-check-done-text": "#6ee7b7",
    },
};

const FOCUS_LABEL_OVERRIDES: Record<string, string> = {
    sweetspot: "Sweet Spot",
    vo2max: "VO2max",
};

function focusLabel(type: string): string {
    return FOCUS_LABEL_OVERRIDES[type] ?? type.charAt(0).toUpperCase() + type.slice(1).replace(/-/g, " ");
}

function cssToken(value: string): string {
    return value.trim().toLowerCase().replace(/[^a-z0-9-]+/g, "-");
}

function parseDate(value: string): Date | null {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function previewWeeks(weeklyPlan: UiWeeklyPlan, todayIso: string) {
    if (weeklyPlan.weeks.length <= 2) return weeklyPlan.weeks;

    const currentWeekIdx = weeklyPlan.weeks.findIndex((week) => {
        return week.days.some((day) => day.date === todayIso) || (week.start_date <= todayIso && todayIso <= week.end_date);
    });
    const start = currentWeekIdx >= 0
        ? Math.min(currentWeekIdx, Math.max(0, weeklyPlan.weeks.length - 2))
        : 0;
    return weeklyPlan.weeks.slice(start, start + 2);
}

function countChecklistBlocks(days: UiDayPlan[]): number {
    return days.reduce((acc, day) => acc + (day.blocks ?? []).filter((b) => b.variant === "checklist").length, 0);
}

function completionLabel(day: UiDayPlan, today: Date, isChecked: (key: string) => boolean): string | null {
    const dayDate = parseDate(day.date);
    if (!dayDate || dayDate >= today) return null;

    const checklistBlocks = (day.blocks ?? []).filter((block) => block.variant === "checklist");
    if (checklistBlocks.length === 0) return "logged";

    const done = checklistBlocks.filter((block) => isChecked(block.key)).length;
    if (done === 0) return "pending";
    if (done === checklistBlocks.length) return "done";
    return "partial";
}

function IntensityIndicator({ intensity }: { intensity?: "rest" | "low" | "moderate" | "high" | "very_high" | null }) {
    if (!intensity || intensity === "rest") return null;

    const level = { low: 1, moderate: 2, high: 3, very_high: 4 }[intensity] || 0;

    return (
        <div className="flex gap-0.5" title={`Intensity: ${intensity}`}>
            {[1, 2, 3, 4].map((i) => (
                <div
                    key={i}
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ backgroundColor: i <= level ? "var(--wp-intensity-active)" : "var(--wp-intensity-idle)" }}
                />
            ))}
        </div>
    );
}

function formatDuration(minutes?: number | null): string | null {
    if (!minutes) return null;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
}

function checklistFooter(
    block: UiHtmlBlock,
    isChecked: (key: string) => boolean,
    toggle: (key: string) => void,
): ReactNode {
    if (block.variant !== "checklist") return null;

    return (
        <button
            className={`rounded-full border px-2 py-0.5 text-[10px] transition-colors ${isChecked(block.key)
                ? "border-[var(--wp-check-done-border)] bg-[var(--wp-check-done-bg)] text-[var(--wp-check-done-text)]"
                : "border-[var(--wp-panel-border)] bg-[var(--wp-check-idle-bg)] text-[var(--wp-check-idle-text)]"
                }`}
            type="button"
            onClick={() => toggle(block.key)}
        >
            {isChecked(block.key) ? "Done" : "Mark"}
        </button>
    );
}

export default function WeeklyPlanViewV1({
    weeklyPlan,
    highlightDayIds,
    onAskAboutBlock,
    theme = "light",
    mode = "full",
}: Props) {
    const highlightSet = useMemo(() => new Set(highlightDayIds ?? []), [highlightDayIds]);
    const { isChecked, toggle } = useCheckboxState(weeklyPlan.plan_id);
    const [openDayByWeek, setOpenDayByWeek] = useState<Record<string, string | null>>({});
    const [showCoachNotes, setShowCoachNotes] = useState(false);
    const [showWeekNotes, setShowWeekNotes] = useState<Record<string, boolean>>({});
    const themeStyle = WEEKLY_THEME_STYLES[theme];

    const today = new Date();
    const todayIso = today.toISOString().slice(0, 10);
    const isLandingMode = mode === "landing";
    const visibleWeeks = isLandingMode ? previewWeeks(weeklyPlan, todayIso) : weeklyPlan.weeks;

    const setOpenDay = (weekId: string, dayId: string) => {
        setOpenDayByWeek((prev) => ({ ...prev, [weekId]: dayId }));
    };

    const toggleWeekNotes = (weekId: string) => {
        setShowWeekNotes((prev) => ({ ...prev, [weekId]: !prev[weekId] }));
    };

    const globalNodes =
        weeklyPlan.global_nodes && weeklyPlan.global_nodes.length > 0
            ? weeklyPlan.global_nodes
            : blocksToFallbackNodes(weeklyPlan.global_blocks ?? [], `${weeklyPlan.plan_id}-global`, "Plan note");

    const hasCoachNotes = globalNodes.length > 0;

    return (
        <div className="space-y-4" style={themeStyle}>
            {/* ── Surface Layer: Plan Brief ── */}
            {weeklyPlan.plan_brief && (
                <section
                    className="overflow-hidden rounded-2xl border border-[var(--wp-panel-border)] p-5"
                    style={{ backgroundImage: "var(--wp-brief-gradient)", boxShadow: "var(--wp-card-shadow)" }}
                >
                    <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--wp-text-muted)]">This Block</div>
                    <p className="mt-2 text-sm leading-relaxed text-[var(--wp-text-secondary)]">{weeklyPlan.plan_brief}</p>
                </section>
            )}

            {/* ── Surface Layer: Week Cards with Day Strips ── */}
            {visibleWeeks.map((week) => {
                const defaultDay = week.days.find((day) => day.date === todayIso)?.day_id ?? week.days[0]?.day_id ?? null;
                const openDayId = openDayByWeek[week.week_id] ?? defaultDay;
                const openDay = week.days.find((day) => day.day_id === openDayId) ?? null;

                const totalChecks = countChecklistBlocks(week.days ?? []);
                const doneChecks = (week.days ?? []).reduce(
                    (acc, day) =>
                        acc +
                        (day.blocks ?? []).filter((block) => block.variant === "checklist" && isChecked(block.key)).length,
                    0,
                );
                const progressPct = totalChecks > 0 ? Math.round((doneChecks / totalChecks) * 100) : 0;

                const weekNodes =
                    week.notes_nodes && week.notes_nodes.length > 0
                        ? week.notes_nodes
                        : blocksToFallbackNodes(week.notes_blocks ?? [], `${week.week_id}-notes`, week.week_label ?? "Week note");
                const hasWeekNotes = !isLandingMode && weekNodes.length > 0;
                const weekNotesOpen = showWeekNotes[week.week_id] ?? false;

                return (
                    <section
                        key={week.week_id}
                        className="rounded-xl border border-[var(--wp-panel-border)] bg-[var(--wp-surface)] p-4"
                        style={{ boxShadow: "var(--wp-card-shadow)" }}
                    >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <div className="text-xs font-semibold uppercase tracking-wide text-[var(--wp-text-muted)]">
                                    {week.week_theme ?? week.week_label ?? "Training block"}
                                </div>
                                <div className="text-xs text-[var(--wp-text-muted)]">
                                    {week.start_date} {"->"} {week.end_date}
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                {hasWeekNotes && (
                                    <button
                                        type="button"
                                        className="text-[10px] font-semibold text-[var(--wp-text-muted)] transition-colors hover:text-[var(--wp-text-secondary)]"
                                        onClick={() => toggleWeekNotes(week.week_id)}
                                    >
                                        {weekNotesOpen ? "Hide notes" : "Week notes"}
                                    </button>
                                )}
                                {totalChecks > 0 && (
                                    <div className="flex items-center gap-2">
                                        <div className="h-1.5 w-24 overflow-hidden rounded-full" style={{ backgroundColor: "var(--wp-progress-track)" }}>
                                            <div
                                                className="h-full rounded-full bg-emerald-400 transition-all duration-300"
                                                style={{ width: `${progressPct}%` }}
                                            />
                                        </div>
                                        <span className="text-[10px] font-semibold tabular-nums text-[var(--wp-text-muted)]">
                                            {doneChecks}/{totalChecks}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Week Notes (collapsed by default) */}
                        {weekNotesOpen && (
                            <div className="mt-3 rounded-lg border border-[var(--wp-panel-border)] bg-[var(--wp-note-surface)] p-3">
                                <DisclosureNodeTree
                                    nodes={weekNodes}
                                    onAskAboutBlock={onAskAboutBlock}
                                    parentLabel={week.week_label ?? `${week.start_date} - ${week.end_date}`}
                                    renderBlockFooter={(block) => checklistFooter(block, isChecked, toggle)}
                                    sourceTab="weekly"
                                />
                            </div>
                        )}

                        {/* Day Strip */}
                        <div className="mt-4">
                            <div className="pv-week-strip" role="tablist" aria-label={`Week ${week.week_id} days`}>
                                {week.days.map((day) => {
                                    const isOpen = openDayId === day.day_id;
                                    const focusTypeRaw = day.focus_type ?? null;
                                    const focusType = focusTypeRaw ? cssToken(focusTypeRaw) : null;
                                    const focusColor = day.focus_color ?? null;
                                    const status = completionLabel(day, today, isChecked);

                                    return (
                                        <button
                                            key={day.day_id}
                                            type="button"
                                            className={`pv-week-strip-day flex flex-col justify-between ${focusType ? `focus--${focusType}` : ""} ${isOpen ? "pv-week-strip-day--active" : ""}`}
                                            style={focusColor ? ({ "--pv-focus-color": focusColor } as CSSProperties) : undefined}
                                            onClick={() => setOpenDay(week.week_id, day.day_id)}
                                        >
                                            <div className="flex w-full items-start justify-between gap-2 overflow-hidden">
                                                <div className="pv-week-strip-day-label">{day.day_label ?? day.date}</div>
                                                <div className="flex gap-1 text-base leading-none">
                                                    {day.icon && <span>{day.icon}</span>}
                                                </div>
                                            </div>

                                            {day.workout_title && (
                                                <div className="mt-2 line-clamp-2 text-left text-[13px] font-bold leading-snug text-[var(--wp-text-primary)]">
                                                    {day.workout_title}
                                                </div>
                                            )}

                                            <div className="mt-2 flex w-full items-end justify-between gap-2">
                                                <div className="pv-week-strip-day-meta flex flex-col items-start gap-0.5 !mt-0">
                                                    <span>
                                                        {focusTypeRaw ? focusLabel(focusTypeRaw) : "Rest"}
                                                        {status ? ` | ${status}` : ""}
                                                    </span>
                                                    {(day.estimated_duration_min || day.primary_distance_km) && (
                                                        <span className="font-semibold tracking-tight text-[var(--wp-text-secondary)]">
                                                            {formatDuration(day.estimated_duration_min)}
                                                            {day.estimated_duration_min && day.primary_distance_km ? " · " : ""}
                                                            {day.primary_distance_km ? `${day.primary_distance_km}km` : ""}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="pb-[2px]">
                                                    <IntensityIndicator intensity={day.estimated_intensity} />
                                                </div>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Selected Day Detail */}
                        {openDay && (
                            <div
                                className={`mt-4 rounded-lg border border-[var(--wp-panel-border)] bg-[var(--wp-detail-surface)] p-3 ${highlightSet.has(openDay.day_id) ? "ring-2 ring-emerald-300/70" : ""}`}
                            >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div>
                                        <div className="text-sm font-semibold text-[var(--wp-text-primary)]">{openDay.day_label ?? openDay.date}</div>
                                        <div className="text-xs text-[var(--wp-text-muted)]">{openDay.date}</div>
                                    </div>
                                    {openDay.focus_type && (
                                        <span
                                            className={`pv-focus-pill focus focus--${cssToken(openDay.focus_type)}`}
                                            style={
                                                openDay.focus_color
                                                    ? ({ color: openDay.focus_color, borderColor: openDay.focus_color } as CSSProperties)
                                                    : undefined
                                            }
                                        >
                                            {focusLabel(openDay.focus_type)}
                                        </span>
                                    )}
                                </div>

                                {/* Readiness Note — the coaching voice */}
                                {openDay.readiness_note && (
                                    <div className="mt-2 rounded-lg border border-emerald-400/25 bg-emerald-500/10 px-3 py-2 text-sm text-[var(--wp-text-secondary)]">
                                        {openDay.readiness_note}
                                    </div>
                                )}

                                {/* Session Content */}
                                <div className="mt-3">
                                    <DisclosureNodeTree
                                        nodes={
                                            openDay.nodes && openDay.nodes.length > 0
                                                ? openDay.nodes
                                                : blocksToFallbackNodes(openDay.blocks ?? [], openDay.day_id, openDay.day_label ?? openDay.date)
                                        }
                                        onAskAboutBlock={onAskAboutBlock}
                                        parentLabel={openDay.day_label ?? openDay.date}
                                        renderBlockFooter={(block) => checklistFooter(block, isChecked, toggle)}
                                        sourceTab="weekly"
                                    />
                                </div>
                            </div>
                        )}
                    </section>
                );
            })}

            {/* ── Context Layer Toggle: Coach Notes ── */}
            {!isLandingMode && hasCoachNotes && (
                <>
                    <button
                        type="button"
                        className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--wp-panel-border)] bg-[var(--wp-surface)] py-2.5 text-xs font-semibold text-[var(--wp-text-muted)] transition-colors hover:bg-[var(--wp-surface-elevated)] hover:text-[var(--wp-text-secondary)]"
                        onClick={() => setShowCoachNotes((prev) => !prev)}
                    >
                        {showCoachNotes ? "Hide coach notes" : "Show coach notes (zones, rules)"}
                        <span className="text-[10px]">{showCoachNotes ? "\u25B2" : "\u25BC"}</span>
                    </button>

                    {showCoachNotes && (
                        <section
                            className="rounded-xl border border-[var(--wp-panel-border)] bg-[var(--wp-surface)] p-4"
                            style={{ boxShadow: "var(--wp-card-shadow)" }}
                        >
                            <div className="text-xs font-semibold uppercase tracking-wide text-[var(--wp-text-muted)]">Training block notes</div>
                            <div className="mt-3 space-y-2">
                                <DisclosureNodeTree
                                    nodes={globalNodes}
                                    onAskAboutBlock={onAskAboutBlock}
                                    parentLabel="Training block notes"
                                    renderBlockFooter={(block) => checklistFooter(block, isChecked, toggle)}
                                    sourceTab="weekly"
                                />
                            </div>
                        </section>
                    )}
                </>
            )}
        </div>
    );
}
