"use client";

import "./plan-viewer.css";

import { useMemo, useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import AnalysisView from "./analysis-view";
import SeasonProgress from "@/components/dashboard/season-progress";
import DisclosureNodeTree, { blocksToFallbackNodes } from "./components/disclosure-node-tree";
import { localYYYYMMDD } from "@/lib/date-utils";
import { formatPlanDayNumber, formatPlanRangeLabel, getMonthGridColumnStartClass } from "@/lib/plan-calendar";
import { getPrimaryWorkoutTitle } from "@/lib/day-display";
import {
    buildAskAboutPrefill,
    openCoachWithPrefill,
    type AskAboutContext,
    type OnAskAboutBlock,
} from "@/lib/types/ask-about";
import { toggleDayCompletionAction } from "@/app/actions/plan";
import type { UiAnalysis, UiDayPlan, UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";
import { X, FileText, Map, ChevronLeft, ChevronRight, Check } from "lucide-react";
import SeasonPlanView from "./season-plan-view";
import type { SeasonPlanV3, WeeklyPlanV3 } from "./types";
import { RenderAnalysis, RenderSeasonPlan, RenderWeeklyPlan } from "./versioned/plan-renderer";

type Props = {
    analysis?: UiAnalysis | null;
    seasonPlan?: UiSeasonPlan | SeasonPlanV3 | null;
    weeklyPlan?: UiWeeklyPlan | WeeklyPlanV3 | null;
    onAskAboutBlock?: OnAskAboutBlock;
    nowIso?: string;
    publicPreview?: boolean;
};

type LegacyProps = Omit<Props, "seasonPlan" | "weeklyPlan"> & {
    seasonPlan?: UiSeasonPlan | null;
    weeklyPlan?: UiWeeklyPlan | null;
};

type OverlayPanel = "analysis" | "season";

function getIntensityColor(intensity?: string | null): string {
    switch (intensity) {
        case "rest": return "bg-zinc-200";
        case "low": return "bg-emerald-400";
        case "moderate": return "bg-amber-400";
        case "high": return "bg-orange-500";
        case "very_high": return "bg-rose-500";
        default: return "bg-zinc-200";
    }
}

function LegacyPlanViewer({ analysis, seasonPlan, weeklyPlan, onAskAboutBlock, nowIso, publicPreview = false }: LegacyProps) {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const todayIso = useMemo(() => localYYYYMMDD(), []);
    const [selectedDay, setSelectedDay] = useState<UiDayPlan | null>(null);
    const [completedMap, setCompletedMap] = useState<Record<string, boolean>>({});
    const [, startTransition] = useTransition();
    const activePanelParam = searchParams.get("panel");
    const activePanel: OverlayPanel | null =
        activePanelParam === "analysis" || activePanelParam === "season" ? activePanelParam : null;
    const activeSeasonPhaseId = activePanel === "season" ? searchParams.get("phase") : null;

    const replaceOverlayState = (panel: OverlayPanel | null, phaseId?: string | null) => {
        const nextParams = new URLSearchParams(searchParams.toString());
        if (panel) {
            nextParams.set("panel", panel);
        } else {
            nextParams.delete("panel");
        }

        if (panel === "season" && phaseId) {
            nextParams.set("phase", phaseId);
        } else {
            nextParams.delete("phase");
        }

        const query = nextParams.toString();
        router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    };

    const openSeasonPanel = (phaseId?: string | null) => replaceOverlayState("season", phaseId ?? null);
    const openAnalysisPanel = () => replaceOverlayState("analysis");
    const closeOverlay = () => replaceOverlayState(null);

    const toggleCompletion = (e: React.MouseEvent, day: UiDayPlan) => {
        e.preventDefault();
        e.stopPropagation();

        const currentStatus = isDayDone(day);

        // Optimistic UI update
        setCompletedMap((prev) => ({ ...prev, [day.day_id]: !currentStatus }));

        // Server action without blocking rendering
        startTransition(async () => {
            try {
                await toggleDayCompletionAction(day.day_id, !currentStatus);
            } catch (err) {
                console.error("Failed to persist checkmark:", err);
                // Revert optimistic update gracefully
                setCompletedMap((prev) => {
                    const next = { ...prev };
                    delete next[day.day_id];
                    return next;
                });
            }
        });
    };

    // Completion is tracked at the day level
    const isDayDone = (day: UiDayPlan): boolean => {
        // 1. Optimistic override local state
        if (completedMap[day.day_id] !== undefined) return completedMap[day.day_id];
        // 2. Exact API truth
        if (day.is_completed !== undefined) return day.is_completed;
        // 3. Fallback for old plans without 'is_completed'
        const isPast = day.date < todayIso;
        return isPast && day.estimated_intensity !== "rest";
    };

    const months = useMemo(() => {
        if (!weeklyPlan?.weeks) return [];
        const allDays = weeklyPlan.weeks.flatMap(w => w.days || []);
        const groups: Record<string, UiDayPlan[]> = {};
        for (const day of allDays) {
            if (!day.date) continue;
            const monthKey = day.date.slice(0, 7);
            if (!groups[monthKey]) groups[monthKey] = [];
            groups[monthKey].push(day);
        }
        return Object.keys(groups).sort().map(monthKey => {
            const days = groups[monthKey].slice().sort((left, right) => left.date.localeCompare(right.date));
            const label = formatPlanRangeLabel(monthKey, days);
            return { monthKey, label, days };
        });
    }, [weeklyPlan]);

    const todayMonthKey = todayIso.slice(0, 7);
    const defaultMonthIdx = useMemo(() => {
        const idx = months.findIndex(m => m.monthKey === todayMonthKey);
        return idx >= 0 ? idx : 0;
    }, [months, todayMonthKey]);

    const [monthIdx, setMonthIdx] = useState<number | null>(null);
    const activeMonthIdx = monthIdx ?? defaultMonthIdx;
    const activeMonth = months[activeMonthIdx];

    const athleteName = analysis?.athlete_name ?? seasonPlan?.athlete_name ?? weeklyPlan?.athlete_name ?? "";
    const version = analysis?.version ?? seasonPlan?.version ?? weeklyPlan?.version ?? 1;

    const handleAskAboutBlock = (ctx: AskAboutContext) => {
        onAskAboutBlock?.(ctx);
        openCoachWithPrefill(buildAskAboutPrefill(ctx));
    };

    return (
        <div className="flex flex-col gap-6 relative">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--surface)] backdrop-blur rounded-2xl p-4 border border-[var(--border)] shadow-sm">
                <div className="flex items-center gap-3">
                    <h1 className="text-xl font-extrabold tracking-tight text-[var(--text-primary)]">Training Plan</h1>
                    <span className="rounded-full bg-[var(--surface-elevated)] px-2.5 py-0.5 text-[10px] font-bold uppercase text-[var(--text-muted)]">v{version}</span>
                    {athleteName && <span className="text-sm font-semibold text-[var(--text-secondary)]">{athleteName}</span>}
                </div>
                <div className="flex items-center gap-2">
                    {seasonPlan && (
                        <button
                            type="button"
                            onClick={() => openSeasonPanel(activeSeasonPhaseId)}
                            className="flex items-center gap-2 rounded-xl bg-sky-500/10 text-sky-400 px-4 py-2 text-sm font-bold transition hover:bg-sky-500/20"
                        >
                            <Map className="w-4 h-4" />
                            Season Strategy
                        </button>
                    )}
                    {analysis && (
                        <button
                            type="button"
                            onClick={openAnalysisPanel}
                            className="flex items-center gap-2 rounded-xl bg-indigo-500/10 text-indigo-400 px-4 py-2 text-sm font-bold transition hover:bg-indigo-500/20"
                        >
                            <FileText className="w-4 h-4" />
                            Coach Report
                        </button>
                    )}
                </div>
            </div>

            {/* Season Context */}
            {seasonPlan && (
                <div className="w-full">
                    <SeasonProgress seasonPlan={seasonPlan} allowLinks={!publicPreview} hideLink={true} nowIso={nowIso} />
                </div>
            )}

            {/* Layout Box */}
            <div className="flex flex-col lg:flex-row gap-6 items-start relative min-h-[600px]">

                {/* Calendar */}
                <div className="flex-1 w-full bg-[var(--surface)] rounded-3xl border border-[var(--border)] shadow-sm overflow-hidden shrink min-w-0">

                    {months.length > 0 && activeMonth ? (
                        <>
                            {/* Month Nav Bar */}
                            <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-[var(--border)]">
                                <button
                                    onClick={() => setMonthIdx(Math.max(0, activeMonthIdx - 1))}
                                    disabled={activeMonthIdx === 0}
                                    className="flex items-center justify-center w-9 h-9 rounded-xl border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)] hover:border-[var(--border-accent)] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>

                                <div className="flex flex-col items-center gap-1">
                                    <h2 className="text-lg font-extrabold tracking-tight text-[var(--text-primary)]">
                                        {activeMonth.label}
                                    </h2>
                                    {/* Month dots */}
                                    {months.length > 1 && (
                                        <div className="flex items-center gap-1.5">
                                            {months.map((m, i) => (
                                                <button
                                                    key={m.monthKey}
                                                    onClick={() => setMonthIdx(i)}
                                                    className={`rounded-full transition-all ${i === activeMonthIdx
                                                        ? "w-4 h-2 bg-[var(--text-primary)]"
                                                        : m.monthKey < todayMonthKey
                                                            ? "w-2 h-2 bg-emerald-400 hover:bg-emerald-500"
                                                            : "w-2 h-2 bg-[var(--text-muted)] hover:bg-[var(--text-secondary)]"
                                                        }`}
                                                />
                                            ))}
                                        </div>
                                    )}
                                </div>

                                <button
                                    onClick={() => setMonthIdx(Math.min(months.length - 1, activeMonthIdx + 1))}
                                    disabled={activeMonthIdx === months.length - 1}
                                    className="flex items-center justify-center w-9 h-9 rounded-xl border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)] hover:border-[var(--border-accent)] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>

                            {/* Weekday Headers */}
                            <div className="hidden sm:grid grid-cols-7 gap-px bg-[var(--border)] border-b border-[var(--border)]">
                                {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map(d => (
                                    <div key={d} className="bg-[var(--surface)] py-2 text-center text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--text-muted)]">
                                        {d}
                                    </div>
                                ))}
                            </div>

                            {/* Calendar Grid */}
                            <div className="flex flex-col sm:grid sm:grid-cols-7 gap-px bg-[var(--border)]">
                                {activeMonth.days.map((day, dIdx) => {
                                    const isToday = day.date === todayIso;
                                    const isPast = day.date < todayIso;
                                    const isSelected = selectedDay?.day_id === day.day_id;
                                    const isRest = day.estimated_intensity === "rest";
                                    const title = getPrimaryWorkoutTitle(day);
                                    const hasSession = !isRest && !!(title || day.estimated_duration_min || day.estimated_intensity);
                                    const done = hasSession && isDayDone(day);
                                    const colStartClass = dIdx === 0 ? getMonthGridColumnStartClass(day.date) : "";

                                    // Build cell bg state
                                    let cellBg: string;
                                    if (isSelected) {
                                        cellBg = "bg-[var(--surface-elevated)] ring-2 ring-inset ring-sky-500 shadow-lg z-20 sm:scale-[1.02] sm:z-20 border-sky-500/30 border-l-[4px] sm:border-l-0";
                                    } else if (isToday) {
                                        cellBg = "bg-[var(--surface-elevated)] ring-2 ring-inset ring-[var(--accent-primary)] z-10 border-[var(--accent-primary)] border-l-[4px] sm:border-l-0";
                                    } else if (done) {
                                        cellBg = "bg-emerald-500/5 hover:bg-emerald-500/10";
                                    } else if (isPast) {
                                        cellBg = "bg-[var(--surface)] opacity-60 hover:opacity-80";
                                    } else {
                                        cellBg = "bg-[var(--surface)] hover:bg-[var(--surface-elevated)] hover:shadow-sm";
                                    }

                                    return (
                                        <div
                                            key={day.day_id}
                                            className={`relative min-h-[70px] sm:min-h-[110px] p-3 flex flex-row items-center sm:flex-col sm:items-stretch gap-4 sm:gap-0 ${colStartClass} ${cellBg} transition-all duration-200 cursor-pointer group`}
                                            onClick={() => setSelectedDay(isSelected ? null : day)}
                                        >
                                            {/* Top color strip (only visible on desktop grid) */}
                                            {!isRest && day.focus_color && !done && !isSelected && (
                                                <div className="hidden sm:block absolute top-0 inset-x-0 h-[3px]" style={{ backgroundColor: day.focus_color }} />
                                            )}
                                            {done && !isSelected && (
                                                <div className="hidden sm:block absolute top-0 inset-x-0 h-[3px] bg-emerald-400" />
                                            )}

                                            {/* Edge color strip (mobile list view) */}
                                            {!isRest && day.focus_color && !done && !isSelected && !isToday && (
                                                <div className="sm:hidden absolute top-0 bottom-0 left-0 w-[4px]" style={{ backgroundColor: day.focus_color }} />
                                            )}
                                            {done && !isSelected && !isToday && (
                                                <div className="sm:hidden absolute top-0 bottom-0 left-0 w-[4px] bg-emerald-400" />
                                            )}

                                            {/* Day number / Date indicator */}
                                            <div className="flex flex-col items-center sm:flex-row justify-between shrink-0 sm:mb-2 gap-1 w-[40px] sm:w-auto">
                                                <span className={`
                                                    hidden sm:flex items-center justify-center w-7 h-7 rounded-full text-[13px] font-bold leading-none transition-all
                                                    ${isSelected ? "bg-sky-500 text-white shadow-sm" : isToday ? "bg-[var(--accent-primary)] text-white" : done ? "text-emerald-400" : isPast ? "text-[var(--text-muted)]" : "text-[var(--text-primary)] group-hover:text-white"}
                                                `}>
                                                    {formatPlanDayNumber(day.date)}
                                                </span>
                                                <div className="sm:hidden flex flex-col items-center text-center">
                                                    <span className={`text-[10px] sm:hidden font-bold uppercase tracking-widest ${isToday ? "text-[var(--accent-primary)]" : "text-[var(--text-muted)]"}`}>
                                                        {new Date(`${day.date}T00:00:00Z`).toLocaleDateString("en-US", { weekday: "short", timeZone: "UTC" })}
                                                    </span>
                                                    <span className={`text-xl sm:hidden font-extrabold ${isPast ? "text-[var(--text-muted)]" : isToday ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}`}>
                                                        {formatPlanDayNumber(day.date)}
                                                    </span>
                                                </div>

                                                {/* Checkmark button (Mobile: moves to the far right, Desktop: top right) */}
                                                <div className="hidden sm:block">
                                                    {hasSession && (
                                                        <button
                                                            type="button"
                                                            onClick={(e) => toggleCompletion(e, day)}
                                                            className={`
                                                                flex items-center justify-center w-7 h-7 rounded-md border-[1.5px] shrink-0 transition-all
                                                                ${done
                                                                    ? "bg-emerald-500 border-emerald-500 shadow-sm text-white hover:bg-emerald-600 hover:border-emerald-600"
                                                                    : "bg-[var(--surface)] border-[var(--border-accent)] text-transparent hover:border-emerald-400 hover:text-emerald-400 hover:bg-emerald-500/10"
                                                                }
                                                                ${isSelected ? "ring-2 ring-white/50" : ""}
                                                            `}
                                                            title={done ? "Mark as not done" : "Mark as done"}
                                                        >
                                                            <Check className={`w-4 h-4 stroke-[3] ${done ? "visible" : "invisible group-hover:visible"}`} />
                                                        </button>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Session content */}
                                            <div className="flex flex-col gap-1 flex-1 sm:mt-auto py-1 sm:py-0 pr-8 sm:pr-0">
                                                {isRest ? (
                                                    <span className={`text-[11px] sm:text-[10px] font-bold uppercase tracking-wider ${isSelected ? "text-sky-400" : "text-[var(--text-muted)]"}`}>Rest</span>
                                                ) : (
                                                    <>
                                                        {title && (
                                                            <div className={`text-[11px] font-bold leading-snug line-clamp-2 ${done ? "line-through opacity-50" : isSelected ? "text-sky-300" : isPast ? "text-[var(--text-muted)]" : "text-[var(--text-primary)]"
                                                                }`} style={!done && !isSelected && day.focus_color ? { color: day.focus_color } : {}}>
                                                                {title}
                                                            </div>
                                                        )}
                                                        <div className="flex items-center gap-1.5 mt-0.5 sm:mt-1">
                                                            <div className={`h-1.5 sm:h-1 flex-1 rounded-full ${getIntensityColor(day.estimated_intensity)} ${done ? "opacity-30" : isSelected ? "opacity-100" : "opacity-70"}`} />
                                                        </div>
                                                        {day.estimated_duration_min && (
                                                            <div className={`text-[11px] sm:text-[10px] font-semibold mt-0.5 sm:-mt-0.5 ${isSelected ? "text-sky-400" : "text-[var(--text-muted)]"}`}>
                                                                {day.estimated_duration_min}m
                                                            </div>
                                                        )}
                                                    </>
                                                )}
                                            </div>

                                            {/* Mobile checkmark rendering block */}
                                            <div className="sm:hidden absolute right-3 top-1/2 -translate-y-1/2">
                                                {hasSession && (
                                                    <button
                                                        type="button"
                                                        onClick={(e) => toggleCompletion(e, day)}
                                                        className={`
                                                            flex items-center justify-center w-8 h-8 rounded-full border-[1.5px] shrink-0 transition-all
                                                            ${done
                                                                ? "bg-emerald-500 border-emerald-500 shadow-sm text-white"
                                                                : "bg-[var(--surface-elevated)] border-[var(--border-accent)] text-transparent"
                                                            }
                                                        `}
                                                        title={done ? "Mark as not done" : "Mark as done"}
                                                    >
                                                        <Check className={`w-4 h-4 stroke-[3] ${done ? "visible" : "invisible"}`} />
                                                    </button>
                                                )}
                                            </div>

                                            {isToday && !isSelected && (
                                                <div className="hidden sm:block absolute top-1 right-1">
                                                    <span className="rounded-full bg-[var(--accent-primary)] px-1.5 py-0.5 text-[8px] font-extrabold uppercase tracking-widest text-white shadow-sm">
                                                        Today
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Summary footer */}
                            <div className="flex items-center justify-between px-6 py-3 border-t border-[var(--border)] bg-[var(--background)]/50">
                                <div className="flex items-center gap-4 text-xs font-semibold text-[var(--text-muted)]">
                                    {(() => {
                                        const days = activeMonth.days;
                                        const sessionDays = days.filter((day) => {
                                            if (day.estimated_intensity === "rest") return false;
                                            return !!(getPrimaryWorkoutTitle(day) || day.estimated_duration_min || day.estimated_intensity);
                                        });
                                        const doneDays = sessionDays.filter(d => isDayDone(d));
                                        return (
                                            <span className="flex items-center gap-1.5">
                                                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                                                {doneDays.length}/{sessionDays.length} sessions done
                                            </span>
                                        );
                                    })()}
                                </div>
                                <button
                                    onClick={() => {
                                        const todayM = months.findIndex(m => m.monthKey === todayMonthKey);
                                        setMonthIdx(todayM >= 0 ? todayM : defaultMonthIdx);
                                    }}
                                    className="text-xs font-bold text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
                                >
                                    Jump to today →
                                </button>
                            </div>
                        </>
                    ) : (
                        <div className="flex h-64 items-center justify-center text-sm font-medium text-[var(--text-muted)] italic p-8">
                            No plan data available.
                        </div>
                    )}
                </div>

                {/* Day Detail Panel */}
                <div className={`
                    fixed lg:static inset-0 z-50 lg:z-auto transition-all duration-300 ease-in-out
                    ${selectedDay ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none lg:w-0 lg:opacity-0"}
                    lg:pointer-events-auto lg:shrink-0 flex
                `}>
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm lg:hidden" onClick={() => setSelectedDay(null)} />

                    <div className={`
                        absolute lg:relative bottom-0 lg:bottom-auto right-0
                        w-full lg:w-[420px] max-h-[85vh] lg:max-h-none h-full
                        bg-[var(--surface)] rounded-t-3xl lg:rounded-3xl border border-[var(--border)] shadow-2xl lg:shadow-sm
                        transition-transform duration-300 ease-in-out
                        ${selectedDay ? "translate-y-0 lg:translate-x-0" : "translate-y-full lg:translate-y-0 lg:translate-x-8"}
                        flex flex-col overflow-hidden
                    `}>
                        {selectedDay && (
                            <>
                                <div className="flex items-start justify-between gap-4 p-5 lg:p-6 pb-4 border-b border-[var(--border)] bg-[var(--surface-elevated)]/50">
                                    <div className="min-w-0">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
                                            {new Date(`${selectedDay.date}T00:00:00Z`).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC" })}
                                        </div>
                                        <h3 className="mt-1 text-xl font-extrabold tracking-tight text-[var(--text-primary)] break-words">
                                            {selectedDay.day_label ?? selectedDay.focus_type ?? (selectedDay.estimated_intensity === "rest" ? "Rest Day" : "Session Details")}
                                        </h3>
                                        <div className="mt-3 flex flex-wrap items-center gap-2">
                                            {selectedDay.estimated_duration_min && (
                                                <span className="rounded-full bg-[var(--surface-elevated)] px-2.5 py-1 text-[11px] font-bold text-[var(--text-secondary)]">
                                                    {selectedDay.estimated_duration_min} min
                                                </span>
                                            )}
                                            {selectedDay.estimated_intensity && (
                                                <span className="rounded-full bg-[var(--surface-elevated)] px-2.5 py-1 text-[11px] font-bold text-[var(--text-secondary)] capitalize">
                                                    {selectedDay.estimated_intensity.replace("_", " ")}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <button
                                        className="p-2 -mr-2 -mt-2 rounded-full text-[var(--text-muted)] hover:bg-[var(--surface-elevated)] hover:text-[var(--text-primary)] transition"
                                        onClick={() => setSelectedDay(null)}
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>

                                <div className="flex-1 overflow-y-auto p-5 lg:p-6 pb-24 lg:pb-6 relative">
                                    {selectedDay.readiness_note && (
                                        <div className="mb-6 rounded-2xl bg-[var(--accent-coach)]/10 p-4 border border-[var(--accent-coach)]/20">
                                            <div className="text-[10px] font-bold uppercase tracking-widest text-[var(--accent-coach)] mb-1">Coach Note</div>
                                            <div className="text-sm font-medium text-[var(--text-primary)] leading-relaxed">{selectedDay.readiness_note}</div>
                                        </div>
                                    )}

                                    {(() => {
                                        const hasNodes = selectedDay.nodes && selectedDay.nodes.length > 0;
                                        const hasBlocks = selectedDay.blocks && selectedDay.blocks.length > 0;

                                        if (hasNodes || hasBlocks) {
                                            return (
                                                <DisclosureNodeTree
                                                    nodes={hasNodes ? selectedDay.nodes! : blocksToFallbackNodes(selectedDay.blocks!, selectedDay.day_id, "Session Details")}
                                                    parentLabel={selectedDay.day_label ?? selectedDay.date}
                                                    sourceTab="weekly"
                                                    onAskAboutBlock={handleAskAboutBlock}
                                                />
                                            );
                                        }

                                        return (
                                            <div className="flex flex-col items-center justify-center h-32 text-center">
                                                <div className="text-sm font-medium text-[var(--text-muted)] italic">No detailed session data for this day.</div>
                                            </div>
                                        );
                                    })()}
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Analysis Modal */}
            {activePanel === "analysis" && analysis && (
                <div className="fixed inset-0 z-[100] flex justify-end">
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeOverlay} />
                    <div className="relative w-full max-w-2xl bg-[var(--surface)] h-full shadow-2xl border-l border-[var(--border)] overflow-y-auto animate-in slide-in-from-right duration-300">
                        <div className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--surface)]/90 backdrop-blur">
                            <div className="bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.08),transparent_38%),radial-gradient(circle_at_top_right,rgba(59,130,246,0.08),transparent_42%)] px-4 py-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">Analysis Report</div>
                                        <h2 className="mt-1 text-xl font-bold tracking-tight text-[var(--text-primary)]">Coach Analysis Report</h2>
                                        <p className="mt-1 max-w-xl text-xs leading-relaxed text-[var(--text-secondary)]">
                                            {analysis.headline_brief?.trim() || "Load, recovery, and performance analysis with coaching guidance."}
                                        </p>
                                    </div>
                                    <button type="button" onClick={closeOverlay} className="rounded-full p-2 text-[var(--text-muted)] transition hover:bg-[var(--surface-elevated)] hover:text-[var(--text-primary)]">
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div className="p-4 sm:p-6">
                            <AnalysisView analysis={analysis} onAskAboutBlock={handleAskAboutBlock} />
                        </div>
                    </div>
                </div>
            )}

            {/* Season Modal */}
            {activePanel === "season" && seasonPlan && (
                <div className="fixed inset-0 z-[100] flex justify-end">
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity" onClick={closeOverlay} />
                    <div className="relative h-full w-full max-w-3xl border-l border-[var(--border)] bg-[var(--surface)] shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300 xl:max-w-4xl">
                        <div className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--surface)]/90 backdrop-blur">
                            <div className="bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.10),transparent_38%),radial-gradient(circle_at_top_right,rgba(56,189,248,0.10),transparent_44%)] px-4 py-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">Season Strategy</div>
                                        <h2 className="mt-1 text-xl font-bold tracking-tight text-[var(--text-primary)]">Season Strategy</h2>
                                        <p className="mt-1 max-w-xl text-xs leading-relaxed text-[var(--text-secondary)]">
                                            {seasonPlan.season_summary_line?.trim() || `${seasonPlan.start_date} to ${seasonPlan.end_date}`}
                                        </p>
                                    </div>
                                    <button type="button" onClick={closeOverlay} className="rounded-full p-2 text-[var(--text-muted)] transition hover:bg-[var(--surface-elevated)] hover:text-[var(--text-primary)]">
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div className="p-4 sm:p-6">
                            <SeasonPlanView
                                seasonPlan={seasonPlan}
                                selectedPhaseId={activeSeasonPhaseId}
                                onAskAboutBlock={handleAskAboutBlock}
                                onPhaseSelect={(phaseId) => openSeasonPanel(phaseId)}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function PlanViewer(props: Props) {
    const requiresVersionedDispatch = [props.analysis, props.seasonPlan, props.weeklyPlan]
        .some((artifact) => artifact != null && artifact.schema_version !== 1);
    if (!requiresVersionedDispatch) {
        return <LegacyPlanViewer {...props} seasonPlan={props.seasonPlan as UiSeasonPlan | null | undefined} weeklyPlan={props.weeklyPlan as UiWeeklyPlan | null | undefined} />;
    }

    return (
        <div className="space-y-8">
            {props.weeklyPlan ? (
                <RenderWeeklyPlan
                    weeklyPlan={props.weeklyPlan}
                    onAskAboutBlock={props.onAskAboutBlock}
                    theme="dark"
                    mode={props.publicPreview ? "landing" : "full"}
                    nowIso={props.nowIso}
                />
            ) : null}
            {props.seasonPlan ? (
                <RenderSeasonPlan
                    seasonPlan={props.seasonPlan}
                    onAskAboutBlock={props.onAskAboutBlock}
                    mode={props.publicPreview ? "landing" : "full"}
                />
            ) : null}
            {props.analysis ? (
                <RenderAnalysis
                    analysis={props.analysis}
                    onAskAboutBlock={props.onAskAboutBlock}
                    mode={props.publicPreview ? "landing" : "full"}
                />
            ) : null}
        </div>
    );
}
