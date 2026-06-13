"use client";

import { getCurrentSeasonIndex, getCurrentWeekIndex } from "@/lib/date-utils";
import type { UiAnalysis, UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";

export type OverviewSectionId = "analysis" | "season" | "weekly";

type Props = {
    analysis?: UiAnalysis | null;
    seasonPlan?: UiSeasonPlan | null;
    weeklyPlan?: UiWeeklyPlan | null;
    onExplore: (section: OverviewSectionId) => void;
};

function formatDateRange(start?: string | null, end?: string | null): string | null {
    if (!start || !end) return null;
    return `${start} -> ${end}`;
}

function statusCounts(analysis?: UiAnalysis | null): string {
    if (!analysis) return "No analysis loaded";

    const counts = { danger: 0, warning: 0, good: 0 };
    analysis.kpis.forEach((kpi) => {
        if (kpi.status === "danger") counts.danger += 1;
        if (kpi.status === "warning") counts.warning += 1;
        if (kpi.status === "good") counts.good += 1;
    });

    const parts: string[] = [];
    if (counts.danger > 0) parts.push(`${counts.danger} danger`);
    if (counts.warning > 0) parts.push(`${counts.warning} warning`);
    if (counts.good > 0) parts.push(`${counts.good} good`);
    return parts.length > 0 ? parts.join(" | ") : "Neutral signal";
}

export default function OverviewHub({ analysis, seasonPlan, weeklyPlan, onExplore }: Props) {
    const seasonIndex = getCurrentSeasonIndex(seasonPlan);
    const weekIndex = getCurrentWeekIndex(weeklyPlan);

    const currentPhase = seasonPlan?.phases[seasonIndex] ?? null;
    const nextPhase = seasonPlan?.phases[seasonIndex + 1] ?? null;
    const currentWeek = weeklyPlan?.weeks[weekIndex] ?? null;

    return (
        <section className="pv-overview-hub" aria-label="Coaching cockpit overview">
            <article className="pv-overview-card pv-overview-card--analysis">
                <div className="pv-overview-label">Analysis</div>
                <h3 className="pv-overview-title">Signal Scan</h3>
                <p className="pv-overview-kicker">{statusCounts(analysis)}</p>
                <p className="pv-overview-meta">
                    {analysis ? `${analysis.kpis.length} KPIs | ${analysis.sections.length} sections` : "No analysis plan yet"}
                </p>
                <button className="pv-overview-action" type="button" onClick={() => onExplore("analysis")}>Explore {">"}</button>
            </article>

            <article className="pv-overview-card pv-overview-card--season">
                <div className="pv-overview-label">Season</div>
                <h3 className="pv-overview-title">{currentPhase?.title ?? "Season not available"}</h3>
                <p className="pv-overview-kicker">
                    {currentPhase?.summary ?? formatDateRange(currentPhase?.start_date, currentPhase?.end_date) ?? "No phase data"}
                </p>
                <p className="pv-overview-meta">{nextPhase ? `Next: ${nextPhase.title}` : seasonPlan ? "Final phase active" : ""}</p>
                <button className="pv-overview-action" type="button" onClick={() => onExplore("season")}>Explore {">"}</button>
            </article>

            <article className="pv-overview-card pv-overview-card--weekly">
                <div className="pv-overview-label">Current Block</div>
                <h3 className="pv-overview-title">{currentWeek?.week_label ?? "Training block not available"}</h3>
                <p className="pv-overview-kicker">
                    {currentWeek ? formatDateRange(currentWeek.start_date, currentWeek.end_date) : "No active week"}
                </p>
                <p className="pv-overview-meta">{currentWeek ? `${currentWeek.days.length} days loaded` : ""}</p>
                <button className="pv-overview-action" type="button" onClick={() => onExplore("weekly")}>Explore {">"}</button>
            </article>
        </section>
    );
}
