import Link from "next/link";
import { buildSeasonProgressState } from "@/lib/season-progress";
import type { SeasonPlanV3 } from "@/components/plan-viewer/types";
import type { UiSeasonPlan } from "@/lib/types/ui-blocks";
import "@/components/plan-viewer/components/season-timeline.css";

type Props = {
    seasonPlan: UiSeasonPlan | SeasonPlanV3 | undefined;
    allowLinks?: boolean;
    hideLink?: boolean;
    nowIso?: string;
    linkHref?: string;
};

function phaseColorClass(index: number) {
    return `seg--p${(index % 6) + 1}`;
}

function daysUntil(targetMs: number, nowMs: number): number {
    const msPerDay = 86_400_000;
    return Math.max(0, Math.ceil((targetMs - nowMs) / msPerDay));
}

export default function SeasonProgress({
    seasonPlan,
    allowLinks = true,
    hideLink,
    nowIso,
    linkHref = "/app/plan?panel=season",
}: Props) {
    if (!seasonPlan) return null;

    const progressState = buildSeasonProgressState(seasonPlan, nowIso);
    if (!progressState) return null;

    const { progress, nextPhaseEndMs, nowMs } = progressState;
    const startMs = new Date(seasonPlan.start_date).getTime();
    const endMs = new Date(seasonPlan.end_date).getTime();
    const total = Math.max(1, endMs - startMs);
    const activePhase =
        seasonPlan.phases.find((phase) => {
            const pStart = new Date(phase.start_date).getTime();
            const pEnd = new Date(phase.end_date).getTime() + 86_400_000;
            return nowMs >= pStart && nowMs <= pEnd;
        }) ?? null;
    const buildPhaseHref = (phaseId?: string | null) => {
        if (!phaseId) return linkHref;
        const joiner = linkHref.includes("?") ? "&" : "?";
        return `${linkHref}${joiner}phase=${encodeURIComponent(phaseId)}`;
    };

    return (
        <div className="flex flex-col gap-3 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 sm:p-6 shadow-sm overflow-hidden">
            <div className="flex items-start justify-between gap-3 min-w-0">
                <div className="min-w-0">
                    <div className="text-[10px] font-semibold text-[var(--text-muted)]">Season Progress</div>
                    <div className="mt-1 truncate text-sm font-bold text-[var(--text-primary)]">
                        {("summary_markdown" in seasonPlan
                            ? seasonPlan.summary_markdown.trim()
                            : seasonPlan.season_summary_line?.trim()) || `${seasonPlan.start_date} → ${seasonPlan.end_date}`}
                    </div>
                </div>
                {!hideLink && allowLinks && (
                    <Link href={linkHref} className="shrink-0 text-xs font-bold text-[var(--accent-primary)] hover:text-[var(--accent-primary)]/80 tracking-wide mt-0.5">
                        Season strategy →
                    </Link>
                )}
            </div>

            <div className="sm:hidden mt-[-4px] mb-1">
                {activePhase ? (
                    <span className="text-xs font-semibold text-[var(--text-muted)]">
                        Current:{" "}
                        {allowLinks ? (
                            <Link href={buildPhaseHref(activePhase.phase_id)} className="text-[var(--text-primary)] hover:text-[var(--accent-primary)]">
                                {activePhase.title}
                            </Link>
                        ) : (
                            <span className="text-[var(--text-primary)]">{activePhase.title}</span>
                        )}
                    </span>
                ) : (
                    <span className="text-xs font-semibold text-[var(--text-muted)]">Off-season</span>
                )}
            </div>

            <div>
                <div className="relative h-6 sm:h-9 w-full overflow-hidden rounded-xl bg-[var(--background)]">
                    <div className="absolute inset-x-0 h-full flex">
                        {seasonPlan.phases.map((phase, index) => {
                            const pStart = new Date(phase.start_date).getTime() || startMs;
                            const pEnd = new Date(phase.end_date).getTime() || pStart;
                            const share = Math.max(0.001, pEnd - pStart) / total;

                            // Only show text if the segment is wide enough (rough heuristic based on time share)
                            const showText = share > 0.05;

                            if (!allowLinks) {
                                return (
                                    <div
                                        key={phase.phase_id}
                                        className={`${phaseColorClass(index)} h-full border-r border-[var(--border)] last:border-r-0 flex min-w-0 items-center px-2 overflow-hidden ${activePhase?.phase_id === phase.phase_id ? "ring-1 ring-inset ring-white/25" : ""}`}
                                        style={{ flex: share }}
                                        title={`${phase.title} (${phase.start_date} → ${phase.end_date})`}
                                        aria-label={`${phase.title}`}
                                    >
                                        {showText && (
                                            <span className="hidden truncate text-xs font-bold text-white/90 sm:inline">
                                                {phase.title}
                                            </span>
                                        )}
                                    </div>
                                );
                            }

                            return (
                                <Link
                                    key={phase.phase_id}
                                    href={buildPhaseHref(phase.phase_id)}
                                    className={`${phaseColorClass(index)} h-full border-r border-[var(--border)] last:border-r-0 flex min-w-0 items-center px-2 overflow-hidden transition-colors hover:brightness-110 ${activePhase?.phase_id === phase.phase_id ? "ring-1 ring-inset ring-white/25" : ""}`}
                                    style={{ flex: share }}
                                    title={`${phase.title} (${phase.start_date} → ${phase.end_date})`}
                                    aria-label={`Open ${phase.title} in season strategy`}
                                >
                                    {showText && (
                                        <span className="hidden truncate text-xs font-bold text-white/90 sm:inline">
                                            {phase.title}
                                        </span>
                                    )}
                                </Link>
                            );
                        })}
                    </div>

                    <div
                        className="pointer-events-none absolute top-0 bottom-0 w-1 bg-[var(--accent-primary)] shadow-[var(--glow-accent)] z-10 transition-all duration-300"
                        style={{ left: `calc(${progress * 100}% - 2px)` }}
                        aria-label="Current date marker"
                    />
                </div>
                {nextPhaseEndMs && (
                    <div className="mt-2 text-[10px] font-medium text-[var(--text-muted)] text-right">
                        {daysUntil(nextPhaseEndMs, nowMs)}d to next checkpoint
                    </div>
                )}
            </div>
        </div>
    );
}
