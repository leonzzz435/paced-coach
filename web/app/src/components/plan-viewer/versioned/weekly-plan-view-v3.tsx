"use client";

import { CalendarDays, Check, ChevronDown, Clock3, Gauge, MapPin, Sparkles } from "lucide-react";
import { useMemo, useRef, useState, useTransition, type CSSProperties } from "react";

import { toggleDayCompletionAction } from "@/app/actions/plan";
import MarkdownSnippet from "@/components/markdown_snippet";
import type { PlanViewMode, SemanticBlockV3, WeeklyPlanTheme, WeeklyPlanV3 } from "@/components/plan-viewer/types";
import ArtifactSection from "@/components/plan-viewer/versioned/artifact-section-v3";
import SemanticBlock from "@/components/plan-viewer/versioned/semantic-block-v3";
import type { OnAskAboutBlock } from "@/lib/types/ask-about";
import { athleteLocalYYYYMMDD } from "@/lib/date-utils";

type Props = {
    weeklyPlan: WeeklyPlanV3;
    highlightDayIds?: string[];
    onAskAboutBlock?: OnAskAboutBlock;
    theme?: WeeklyPlanTheme;
    mode?: PlanViewMode;
    nowIso?: string;
};

type ExecutionDay = WeeklyPlanV3["weeks"][number]["days"][number];

const THEME_STYLE: Record<WeeklyPlanTheme, CSSProperties> = {
    light: {
        "--surface": "#ffffff",
        "--surface-elevated": "#f8fafc",
        "--border": "rgba(100,116,139,0.22)",
        "--text-primary": "#0f172a",
        "--text-secondary": "#334155",
        "--text-muted": "#64748b",
    } as CSSProperties,
    dark: {
        "--surface": "rgba(11,16,27,0.94)",
        "--surface-elevated": "rgba(15,23,42,0.82)",
        "--border": "rgba(148,163,184,0.16)",
        "--text-primary": "#f8fafc",
        "--text-secondary": "#cbd5e1",
        "--text-muted": "#94a3b8",
    } as CSSProperties,
};

const INTENSITY_ACCENT = {
    rest: "bg-slate-500",
    low: "bg-emerald-400",
    moderate: "bg-amber-400",
    high: "bg-orange-500",
    very_high: "bg-rose-500",
} as const;

function formatDate(value: string, options: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" }): string {
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return value;
    return new Intl.DateTimeFormat("en", options).format(parsed);
}

function formatDuration(minutes: number): string {
    if (minutes === 0) return "Rest";
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    return [hours ? `${hours}h` : "", rest ? `${rest}m` : ""].filter(Boolean).join(" ");
}

function Blocks({ blocks, parentLabel, onAskAboutBlock }: { blocks: SemanticBlockV3[]; parentLabel: string; onAskAboutBlock?: OnAskAboutBlock }) {
    if (blocks.length === 0) return null;
    return (
        <div className="space-y-4">
            {blocks.map((block) => (
                <SemanticBlock key={block.block_id} block={block} parentLabel={parentLabel} sourceTab="weekly" onAskAboutBlock={onAskAboutBlock} />
            ))}
        </div>
    );
}

export default function WeeklyPlanViewV3({
    weeklyPlan,
    highlightDayIds,
    onAskAboutBlock,
    theme = "light",
    mode = "full",
    nowIso,
}: Props) {
    const today = athleteLocalYYYYMMDD(nowIso);
    const visibleWeeks = mode === "landing" ? weeklyPlan.weeks.slice(0, 2) : weeklyPlan.weeks;
    const visibleDays = useMemo(() => visibleWeeks.flatMap((week) => week.days), [visibleWeeks]);
    const defaultDayId = visibleDays.find((day) => day.date === today)?.day_id ?? visibleDays[0]?.day_id ?? "";
    const [selectedDayId, setSelectedDayId] = useState(defaultDayId);
    const [completedMap, setCompletedMap] = useState<Record<string, boolean>>({});
    const [pendingDayIds, setPendingDayIds] = useState<Set<string>>(() => new Set());
    const pendingDayIdsRef = useRef(new Set<string>());
    const [, startTransition] = useTransition();
    const highlightSet = useMemo(() => new Set(highlightDayIds ?? []), [highlightDayIds]);
    const selectedDay = visibleDays.find((day) => day.day_id === selectedDayId) ?? visibleDays[0];
    const selectedWeek = visibleWeeks.find((week) => week.days.some((day) => day.day_id === selectedDay?.day_id));

    const isDayDone = (day: ExecutionDay): boolean => completedMap[day.day_id] ?? day.is_completed;

    const toggleCompletion = (day: ExecutionDay) => {
        if (pendingDayIdsRef.current.has(day.day_id)) return;
        const previousValue = isDayDone(day);
        const nextValue = !previousValue;
        pendingDayIdsRef.current.add(day.day_id);
        setPendingDayIds((current) => new Set(current).add(day.day_id));
        setCompletedMap((current) => ({ ...current, [day.day_id]: nextValue }));
        startTransition(async () => {
            try {
                await toggleDayCompletionAction(day.day_id, nextValue);
            } catch (error) {
                console.error("Failed to persist checkmark:", error);
                setCompletedMap((current) => ({ ...current, [day.day_id]: previousValue }));
            } finally {
                pendingDayIdsRef.current.delete(day.day_id);
                setPendingDayIds((current) => {
                    const next = new Set(current);
                    next.delete(day.day_id);
                    return next;
                });
            }
        });
    };

    return (
        <div className="space-y-6" style={THEME_STYLE[theme]}>
            <header className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 sm:p-6">
                <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
                    <div className="min-w-0">
                        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-violet-300">
                            <Sparkles className="h-3.5 w-3.5" /> 28-day execution · v3
                        </div>
                        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-3xl">{weeklyPlan.title}</h1>
                    </div>
                    <div className="flex shrink-0 items-center gap-3 text-sm text-[var(--text-secondary)]">
                        <CalendarDays className="h-5 w-5 text-violet-300" />
                        <div>
                            <div className="text-[10px] font-bold uppercase tracking-wide text-[var(--text-muted)]">Execution window</div>
                            <div className="mt-0.5 tabular-nums">{formatDate(weeklyPlan.start_date)} — {formatDate(weeklyPlan.end_date, { month: "short", day: "numeric", year: "numeric" })}</div>
                        </div>
                    </div>
                </div>
                <details className="group mt-5 border-t border-[var(--border)] pt-4">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-semibold text-[var(--text-secondary)]">
                        Coach rationale
                        <ChevronDown className="h-4 w-4 text-[var(--text-muted)] transition-transform group-open:rotate-180" />
                    </summary>
                    <MarkdownSnippet markdown={weeklyPlan.summary_markdown} className="mt-4 max-w-4xl text-sm leading-relaxed text-[var(--text-secondary)]" />
                </details>
            </header>

            <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5" aria-label="28-day training calendar">
                <div className="mb-4 flex items-center justify-between gap-4 px-1">
                    <div>
                        <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-sky-300">Training calendar</div>
                        <h2 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">Your next 28 days</h2>
                    </div>
                    <div className="text-xs text-[var(--text-muted)]">Select a day for details</div>
                </div>

                <div className="space-y-3">
                    {visibleWeeks.map((week, weekIndex) => {
                        const completed = week.days.filter(isDayDone).length;
                        return (
                            <div key={week.week_id} className="grid gap-2 lg:grid-cols-[11rem_minmax(0,1fr)] lg:items-stretch">
                                <div className="flex items-center justify-between rounded-xl bg-[var(--surface-elevated)] px-3 py-2 lg:block">
                                    <div>
                                        <div className="text-[9px] font-bold uppercase tracking-[0.16em] text-violet-300">Week {String(weekIndex + 1).padStart(2, "0")}</div>
                                        <div className="mt-1 line-clamp-2 text-xs font-semibold text-[var(--text-primary)]">{week.title}</div>
                                    </div>
                                    <div className="mt-0 text-[10px] tabular-nums text-[var(--text-muted)] lg:mt-2">{completed}/7 complete</div>
                                </div>
                                <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-4 lg:grid-cols-7">
                                    {week.days.map((day) => {
                                        const selected = day.day_id === selectedDay?.day_id;
                                        const done = isDayDone(day);
                                        const isToday = day.date === today;
                                        const highlighted = highlightSet.has(day.day_id);
                                        return (
                                            <button
                                                key={day.day_id}
                                                type="button"
                                                aria-pressed={selected}
                                                className={`relative min-h-24 bg-[var(--surface)] p-2.5 text-left transition hover:bg-[var(--surface-elevated)] ${selected ? "!bg-violet-400/[0.11] ring-1 ring-inset ring-violet-400/45" : ""}`}
                                                onClick={() => setSelectedDayId(day.day_id)}
                                            >
                                                {(highlighted || isToday) && <span className="absolute inset-x-0 top-0 h-0.5 bg-sky-400" />}
                                                <div className="flex items-center justify-between gap-2">
                                                    <span className={`text-[9px] font-bold uppercase tracking-wide ${isToday ? "text-sky-300" : "text-[var(--text-muted)]"}`}>{formatDate(day.date, { weekday: "short", day: "numeric" })}</span>
                                                    {done && <span className="grid h-4 w-4 place-items-center rounded-full bg-emerald-400/15 text-emerald-300"><Check className="h-2.5 w-2.5" /></span>}
                                                </div>
                                                <div className="mt-2 line-clamp-2 text-[11px] font-semibold leading-snug text-[var(--text-primary)]">{day.sessions[0]?.title ?? "Recovery day"}</div>
                                                <div className="mt-2 flex items-center gap-2 text-[9px] text-[var(--text-muted)]">
                                                    <span className={`h-1.5 w-1.5 rounded-full ${INTENSITY_ACCENT[day.intensity]}`} />
                                                    <span>{formatDuration(day.total_duration_min)}</span>
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </section>

            {selectedDay && selectedWeek && (
                <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 sm:p-6" aria-live="polite">
                    <div className="flex flex-col justify-between gap-4 border-b border-[var(--border)] pb-5 sm:flex-row sm:items-start">
                        <div>
                            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-sky-300">{formatDate(selectedDay.date, { weekday: "long", month: "long", day: "numeric" })}</div>
                            <h2 className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">{selectedDay.sessions[0]?.title ?? selectedDay.label}</h2>
                            <div className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--text-muted)]">
                                <span className="flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" />{formatDuration(selectedDay.total_duration_min)}</span>
                                <span className="flex items-center gap-1.5 capitalize"><Gauge className="h-3.5 w-3.5" />{selectedDay.intensity.replace("_", " ")}</span>
                                <span>{selectedWeek.title}</span>
                            </div>
                        </div>
                        <button
                            type="button"
                            disabled={pendingDayIds.has(selectedDay.day_id)}
                            aria-busy={pendingDayIds.has(selectedDay.day_id)}
                            className={`inline-flex shrink-0 items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold transition ${isDayDone(selectedDay) ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300" : "border-[var(--border)] text-[var(--text-secondary)] hover:border-emerald-400/30 hover:text-emerald-300"}`}
                            onClick={() => toggleCompletion(selectedDay)}
                        >
                            <Check className="h-4 w-4" /> {isDayDone(selectedDay) ? "Completed" : "Mark complete"}
                        </button>
                    </div>

                    <div className="mt-6 space-y-6">
                        {selectedDay.sessions.map((session) => (
                            <article key={session.session_id} className="rounded-xl border border-[var(--border)] bg-[var(--surface-elevated)] p-4 sm:p-5">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-violet-300">{session.sport}</div>
                                    <div className="flex gap-3 text-xs text-[var(--text-muted)]"><span>{session.duration_min} min</span>{session.distance_km != null && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{session.distance_km} km</span>}</div>
                                </div>
                                <h3 className="mt-2 text-lg font-semibold text-[var(--text-primary)]">{session.title}</h3>
                                <div className="mt-4 grid gap-5 lg:grid-cols-2">
                                    <div><div className="text-[10px] font-bold uppercase tracking-wide text-[var(--text-muted)]">Objective</div><MarkdownSnippet markdown={session.objective_markdown} className="mt-1 text-sm text-[var(--text-secondary)]" /></div>
                                    <div><div className="text-[10px] font-bold uppercase tracking-wide text-[var(--text-muted)]">Prescription</div><MarkdownSnippet markdown={session.prescription_markdown} className="mt-1 text-sm text-[var(--text-secondary)]" /></div>
                                </div>
                                {session.blocks.length > 0 && <div className="mt-5"><Blocks blocks={session.blocks} parentLabel={session.title} onAskAboutBlock={onAskAboutBlock} /></div>}
                            </article>
                        ))}
                        <Blocks blocks={selectedDay.blocks} parentLabel={selectedDay.label} onAskAboutBlock={onAskAboutBlock} />
                    </div>

                    {(selectedWeek.intent_markdown || selectedWeek.blocks.length > 0) && (
                        <details className="group mt-6 border-t border-[var(--border)] pt-5">
                            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-semibold text-[var(--text-secondary)]">
                                Week guidance
                                <ChevronDown className="h-4 w-4 text-[var(--text-muted)] transition-transform group-open:rotate-180" />
                            </summary>
                            <MarkdownSnippet markdown={selectedWeek.intent_markdown} className="mt-4 max-w-3xl text-sm text-[var(--text-secondary)]" />
                            {selectedWeek.blocks.length > 0 && <div className="mt-5"><Blocks blocks={selectedWeek.blocks} parentLabel={selectedWeek.title} onAskAboutBlock={onAskAboutBlock} /></div>}
                        </details>
                    )}
                </section>
            )}

            {weeklyPlan.sections.length > 0 && (
                <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-5 sm:px-6">
                    <div className="border-b border-[var(--border)] py-5">
                        <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-violet-300">Reference</div>
                        <h2 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">Coach notes, safeguards and decision context</h2>
                    </div>
                    {weeklyPlan.sections.map((section) => <ArtifactSection key={section.section_id} section={section} sourceTab="weekly" onAskAboutBlock={onAskAboutBlock} collapsed />)}
                </section>
            )}
        </div>
    );
}
