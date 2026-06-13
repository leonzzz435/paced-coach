"use client";

import { useMemo, useRef, useState } from "react";

import { SeasonTimeline } from "@/components/plan-viewer/components/season-timeline";
import DisclosureNodeTree, { blocksToFallbackNodes } from "@/components/plan-viewer/components/disclosure-node-tree";
import type { PlanViewMode } from "@/components/plan-viewer/types";
import { type OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiSeasonPlan } from "@/lib/types/ui-blocks";

type Props = {
    seasonPlan: UiSeasonPlan;
    selectedPhaseId?: string | null;
    onAskAboutBlock?: OnAskAboutBlock;
    onPhaseSelect?: (phaseId: string | null) => void;
    mode?: PlanViewMode;
};

function parseDate(value: string): Date | null {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function currentPhaseIndex(seasonPlan: UiSeasonPlan): number {
    const now = new Date();
    const idx = seasonPlan.phases.findIndex((phase) => {
        const start = parseDate(phase.start_date);
        const end = parseDate(phase.end_date);
        const inclusiveEnd = end ? new Date(end.getTime() + 86_400_000) : null;
        return Boolean(start && inclusiveEnd && start <= now && now < inclusiveEnd);
    });
    return idx >= 0 ? idx : 0;
}

function formatDateRange(start: string, end: string): string {
    const fmt = (v: string) => {
        const d = parseDate(v);
        if (!d) return v;
        return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(d);
    };
    return `${fmt(start)} - ${fmt(end)}`;
}

function previewPhaseIndexes(phases: UiSeasonPlan["phases"], currentIdx: number): number[] {
    if (phases.length <= 2) return phases.map((_, index) => index);

    const start = Math.min(Math.max(currentIdx, 0), Math.max(0, phases.length - 2));
    return [start, Math.min(phases.length - 1, start + 1)];
}

export default function SeasonPlanViewV1({
    seasonPlan,
    selectedPhaseId,
    onAskAboutBlock,
    onPhaseSelect,
    mode = "full",
}: Props) {
    const currentIdx = useMemo(() => currentPhaseIndex(seasonPlan), [seasonPlan]);
    const currentPhase = seasonPlan.phases[currentIdx] ?? null;
    const isLandingMode = mode === "landing";
    const [localExpandedPhaseId, setLocalExpandedPhaseId] = useState<string | null>(() =>
        isLandingMode ? null : selectedPhaseId ?? currentPhase?.phase_id ?? null,
    );
    const [showStrategy, setShowStrategy] = useState(false);
    const cardRefs = useRef<Record<string, HTMLElement | null>>({});
    const expandedPhaseId = selectedPhaseId ?? localExpandedPhaseId;
    const phaseEntries = useMemo(() => {
        if (!isLandingMode) {
            return seasonPlan.phases.map((phase, index) => ({ phase, index }));
        }
        return previewPhaseIndexes(seasonPlan.phases, currentIdx).map((index) => ({
            phase: seasonPlan.phases[index],
            index,
        })).filter((entry): entry is { phase: UiSeasonPlan["phases"][number]; index: number } => Boolean(entry.phase));
    }, [currentIdx, isLandingMode, seasonPlan.phases]);

    const scrollToPhase = (phaseId: string) => {
        const card = cardRefs.current[phaseId];
        if (card) {
            card.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    };

    const focusPhase = (phaseId: string) => {
        setLocalExpandedPhaseId(phaseId);
        scrollToPhase(phaseId);
        onPhaseSelect?.(phaseId);
    };

    const togglePhase = (phaseId: string) => {
        const nextPhaseId = expandedPhaseId === phaseId ? null : phaseId;
        setLocalExpandedPhaseId(nextPhaseId);
        if (nextPhaseId) {
            scrollToPhase(nextPhaseId);
        }
        onPhaseSelect?.(nextPhaseId);
    };

    const globalNodes =
        seasonPlan.global_nodes && seasonPlan.global_nodes.length > 0
            ? seasonPlan.global_nodes
            : blocksToFallbackNodes(seasonPlan.global_blocks ?? [], `${seasonPlan.plan_id}-global`, "Season strategy");

    const hasDetails = globalNodes.length > 0 || seasonPlan.phases.some((p) => (p.nodes?.length ?? 0) > 0 || (p.blocks?.length ?? 0) > 0);

    return (
        <div className="space-y-5">
            {seasonPlan.season_summary_line && (
                <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.12),transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-5 shadow-[0_18px_36px_rgba(2,6,23,0.18)]">
                    <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">Season Arc</div>
                    <p className="mt-2 text-sm font-semibold leading-relaxed text-[var(--text-primary)]">{seasonPlan.season_summary_line}</p>
                </section>
            )}

            <SeasonTimeline
                phases={seasonPlan.phases}
                startDate={seasonPlan.start_date}
                endDate={seasonPlan.end_date}
                currentPhaseId={currentPhase?.phase_id ?? null}
                selectedPhaseId={expandedPhaseId}
                onPhaseClick={focusPhase}
            />

            <section className="space-y-2">
                {phaseEntries.map(({ phase, index }) => {
                    const isCurrent = index === currentIdx;
                    const isExpanded = expandedPhaseId === phase.phase_id;
                    const phaseNodes =
                        phase.nodes && phase.nodes.length > 0
                            ? phase.nodes
                            : blocksToFallbackNodes(phase.blocks ?? [], phase.phase_id, phase.title);
                    const hasContent = phaseNodes.length > 0;

                    return (
                        <article
                            key={phase.phase_id}
                            ref={(node) => {
                                cardRefs.current[phase.phase_id] = node;
                            }}
                            className={`rounded-xl border bg-[var(--surface)]/95 shadow-sm ${isCurrent ? "pv-season-current-phase" : "border-[var(--border)]"}`}
                        >
                            <button
                                type="button"
                                className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.03]"
                                onClick={() => {
                                    if (hasContent) {
                                        togglePhase(phase.phase_id);
                                    }
                                }}
                            >
                                <div className="space-y-0.5">
                                    <div className="flex items-center gap-2">
                                        <span className={`text-[10px] font-bold uppercase tracking-wide ${isCurrent ? "text-emerald-300" : "text-[var(--text-muted)]"}`}>
                                            {isCurrent ? "Current Phase" : `Phase ${index + 1}`}
                                        </span>
                                        <span className="text-[10px] text-[var(--text-muted)]">{formatDateRange(phase.start_date, phase.end_date)}</span>
                                    </div>
                                    <h3 className="text-sm font-semibold text-[var(--text-primary)]">{phase.title}</h3>
                                    {phase.summary && <p className="text-xs text-[var(--text-secondary)]">{phase.summary}</p>}
                                </div>
                                {hasContent && (
                                    <span className="text-xs font-semibold text-[var(--text-muted)]">{isExpanded ? "Hide" : "Show"}</span>
                                )}
                            </button>

                            {isExpanded && hasContent && (
                                <div className="space-y-3 border-t border-[var(--border)] px-4 py-4">
                                    <DisclosureNodeTree
                                        nodes={phaseNodes}
                                        onAskAboutBlock={onAskAboutBlock}
                                        parentLabel={`${phase.title} (${phase.start_date} - ${phase.end_date})`}
                                        sourceTab="season"
                                    />
                                </div>
                            )}
                        </article>
                    );
                })}
            </section>

            {!isLandingMode && hasDetails && globalNodes.length > 0 && (
                <>
                    <button
                        type="button"
                        className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] py-2.5 text-xs font-semibold text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-elevated)] hover:text-[var(--text-primary)]"
                        onClick={() => setShowStrategy((prev) => !prev)}
                    >
                        {showStrategy ? "Hide strategy & guardrails" : "Show strategy & guardrails"}
                        <span className="text-[10px]">{showStrategy ? "\u25B2" : "\u25BC"}</span>
                    </button>

                    {showStrategy && (
                        <section className="space-y-2">
                            <div className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">Strategy and guardrails</div>
                            <DisclosureNodeTree
                                nodes={globalNodes}
                                onAskAboutBlock={onAskAboutBlock}
                                parentLabel="Season strategy and guardrails"
                                sourceTab="season"
                            />
                        </section>
                    )}
                </>
            )}
        </div>
    );
}
