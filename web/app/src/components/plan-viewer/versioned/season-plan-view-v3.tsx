"use client";

import { CalendarRange, CheckCircle2, CircleDot, Compass, ShieldAlert } from "lucide-react";
import { useMemo, useState, type CSSProperties } from "react";

import MarkdownSnippet from "@/components/markdown_snippet";
import type { PlanViewMode, SeasonPlanV3 } from "@/components/plan-viewer/types";
import ArtifactSection from "@/components/plan-viewer/versioned/artifact-section-v3";
import SemanticBlock from "@/components/plan-viewer/versioned/semantic-block-v3";
import type { OnAskAboutBlock } from "@/lib/types/ask-about";

type Props = {
    seasonPlan: SeasonPlanV3;
    selectedPhaseId?: string | null;
    onAskAboutBlock?: OnAskAboutBlock;
    onPhaseSelect?: (phaseId: string | null) => void;
    mode?: PlanViewMode;
};

function formatDate(value: string): string {
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return value;
    return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(parsed);
}

function activePhaseId(plan: SeasonPlanV3): string | null {
    const today = new Date().toISOString().slice(0, 10);
    return plan.phases.find((phase) => phase.start_date <= today && today <= phase.end_date)?.phase_id ?? null;
}

export default function SeasonPlanViewV3({
    seasonPlan,
    selectedPhaseId,
    onAskAboutBlock,
    onPhaseSelect,
    mode = "full",
}: Props) {
    const currentPhaseId = useMemo(() => activePhaseId(seasonPlan), [seasonPlan]);
    const [localPhaseId, setLocalPhaseId] = useState<string | null>(selectedPhaseId ?? currentPhaseId ?? seasonPlan.phases[0]?.phase_id ?? null);
    const focusedPhaseId = selectedPhaseId ?? localPhaseId;
    const visiblePhases = mode === "landing" ? seasonPlan.phases.slice(0, 3) : seasonPlan.phases;
    const collapsedSections = new Set(seasonPlan.presentation?.collapsed_section_ids ?? []);

    const choosePhase = (phaseId: string) => {
        const next = focusedPhaseId === phaseId ? null : phaseId;
        setLocalPhaseId(next);
        onPhaseSelect?.(next);
    };

    return (
        <div className="space-y-8">
            <header className="relative overflow-hidden border-b border-[var(--border)] pb-8">
                <div className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-sky-400/10 blur-3xl" />
                <div className="relative grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
                    <div className="max-w-3xl">
                        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-sky-300">
                            <Compass className="h-3.5 w-3.5" aria-hidden="true" /> Season strategy · v3
                        </div>
                        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-4xl">{seasonPlan.title}</h2>
                        <MarkdownSnippet markdown={seasonPlan.summary_markdown} className="mt-4 text-base leading-relaxed text-[var(--text-secondary)]" />
                    </div>
                    <div className="flex items-center gap-3 border-l border-sky-400/25 pl-4 text-sm text-[var(--text-secondary)]">
                        <CalendarRange className="h-5 w-5 text-sky-300" aria-hidden="true" />
                        <div><div className="text-[10px] font-bold uppercase tracking-wide text-[var(--text-muted)]">Season window</div><div className="mt-0.5 tabular-nums">{formatDate(seasonPlan.start_date)} — {formatDate(seasonPlan.end_date)}</div></div>
                    </div>
                </div>
            </header>

            <section aria-labelledby="season-phases-v3">
                <div className="mb-4 flex items-end justify-between gap-4">
                    <div><div className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">Roadmap</div><h3 id="season-phases-v3" className="mt-1 text-xl font-semibold text-[var(--text-primary)]">The arc of the season</h3></div>
                    <div className="text-xs text-[var(--text-muted)]">{seasonPlan.phases.length} phases</div>
                </div>
                <div className="overflow-x-auto pb-2">
                    <div className="grid min-w-[46rem] grid-cols-[repeat(var(--phase-count),minmax(9rem,1fr))] border-y border-[var(--border)]" style={{ "--phase-count": visiblePhases.length } as CSSProperties}>
                        {visiblePhases.map((phase, index) => {
                            const active = phase.phase_id === currentPhaseId;
                            const focused = phase.phase_id === focusedPhaseId;
                            return (
                                <button key={phase.phase_id} type="button" className={`relative px-4 py-4 text-left transition-colors hover:bg-white/[0.03] ${index > 0 ? "border-l border-[var(--border)]" : ""} ${focused ? "bg-sky-400/[0.07]" : ""}`} onClick={() => choosePhase(phase.phase_id)}>
                                    {active && <span className="absolute inset-x-0 top-0 h-0.5 bg-emerald-400" />}
                                    <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[var(--text-muted)]"><span>{String(index + 1).padStart(2, "0")}</span>{active && <span className="text-emerald-300">Now</span>}</div>
                                    <div className="mt-2 text-sm font-semibold text-[var(--text-primary)]">{phase.title}</div>
                                    <div className="mt-1 text-[11px] tabular-nums text-[var(--text-muted)]">{formatDate(phase.start_date)} — {formatDate(phase.end_date)}</div>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {visiblePhases.map((phase) => phase.phase_id === focusedPhaseId && (
                    <article key={phase.phase_id} className="mt-5 border-l-2 border-sky-400/40 pl-5">
                        <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-sky-300">Focused phase</div>
                        <h4 className="mt-1 text-xl font-semibold text-[var(--text-primary)]">{phase.title}</h4>
                        <MarkdownSnippet markdown={phase.objective_markdown} className="mt-2 max-w-3xl text-sm text-[var(--text-secondary)]" />
                        {phase.success_signals.length > 0 && <ul className="mt-4 grid gap-2 sm:grid-cols-2">{phase.success_signals.map((signal) => <li key={signal} className="flex gap-2 text-xs text-[var(--text-secondary)]"><CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-300" />{signal}</li>)}</ul>}
                        {phase.blocks.length > 0 && <div className="mt-5 space-y-4">{phase.blocks.map((block) => <SemanticBlock key={block.block_id} block={block} parentLabel={phase.title} sourceTab="season" onAskAboutBlock={onAskAboutBlock} />)}</div>}
                    </article>
                ))}
            </section>

            <div>{seasonPlan.sections.map((section) => <ArtifactSection key={section.section_id} section={section} sourceTab="season" onAskAboutBlock={onAskAboutBlock} collapsed={collapsedSections.has(section.section_id)} />)}</div>

            {mode !== "landing" && (seasonPlan.assumptions.length > 0 || seasonPlan.safety_concerns.length > 0) && (
                <section className="grid gap-6 border-t border-[var(--border)] pt-6 lg:grid-cols-2">
                    <div><div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-[var(--text-muted)]"><CircleDot className="h-4 w-4" /> Assumptions to keep visible</div><ul className="space-y-3">{seasonPlan.assumptions.map((assumption) => <li key={assumption.statement} className="text-sm text-[var(--text-secondary)]"><span className="font-semibold text-[var(--text-primary)]">{assumption.statement}</span><span className="mt-1 block text-xs">{assumption.consequence}</span></li>)}</ul></div>
                    <div><div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-[var(--text-muted)]"><ShieldAlert className="h-4 w-4 text-amber-300" /> Safety guardrails</div>{seasonPlan.safety_concerns.length > 0 ? <ul className="space-y-2">{seasonPlan.safety_concerns.map((item) => <li key={item.concern} className="border-l border-amber-300/35 pl-3 text-sm text-[var(--text-secondary)]">{item.concern}</li>)}</ul> : <p className="text-sm text-[var(--text-muted)]">No special safety concern recorded for this strategy.</p>}</div>
                </section>
            )}
        </div>
    );
}
