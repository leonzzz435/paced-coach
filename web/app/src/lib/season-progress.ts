import type { UiSeasonPlan } from "@/lib/types/ui-blocks";

function parseIso(value?: string | null): number | null {
    if (!value) return null;
    const ms = new Date(value).getTime();
    return Number.isNaN(ms) ? null : ms;
}

export type SeasonProgressState = {
    progress: number;
    nextPhaseEndMs: number | null;
    nowMs: number;
};

export function buildSeasonProgressState(seasonPlan: UiSeasonPlan, nowIso?: string): SeasonProgressState | null {
    const startMs = parseIso(seasonPlan.start_date);
    const endMs = parseIso(seasonPlan.end_date);
    if (!startMs || !endMs || seasonPlan.phases.length === 0) return null;

    const nowMs = parseIso(nowIso) ?? Date.now();
    const total = Math.max(1, endMs - startMs);
    const progress = Math.min(1, Math.max(0, (nowMs - startMs) / total));
    const nextPhaseEndMs =
        seasonPlan.phases
            .map((phase) => parseIso(phase.end_date))
            .filter((ms): ms is number => typeof ms === "number" && ms >= nowMs)
            .sort((left, right) => left - right)[0] ?? null;

    return { progress, nextPhaseEndMs, nowMs };
}
