import AnalysisViewV1 from "@/components/plan-viewer/versioned/analysis-view-v1";
import SeasonPlanViewV1 from "@/components/plan-viewer/versioned/season-plan-view-v1";
import type { PlanViewMode, SeasonPlanV3, WeeklyPlanTheme, WeeklyPlanV3 } from "@/components/plan-viewer/types";
import SeasonPlanViewV3 from "@/components/plan-viewer/versioned/season-plan-view-v3";
import WeeklyPlanViewV1 from "@/components/plan-viewer/versioned/weekly-plan-view-v1";
import WeeklyPlanViewV3 from "@/components/plan-viewer/versioned/weekly-plan-view-v3";
import { resolveSchemaVersion } from "@/lib/plan-version";
import type { OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiAnalysis, UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";

type AnalysisProps = {
    analysis: UiAnalysis;
    onAskAboutBlock?: OnAskAboutBlock;
    mode?: PlanViewMode;
};
type SeasonProps = {
    seasonPlan: UiSeasonPlan | SeasonPlanV3;
    selectedPhaseId?: string | null;
    onAskAboutBlock?: OnAskAboutBlock;
    onPhaseSelect?: (phaseId: string | null) => void;
    mode?: PlanViewMode;
};
type WeeklyProps = {
    weeklyPlan: UiWeeklyPlan | WeeklyPlanV3;
    highlightDayIds?: string[];
    onAskAboutBlock?: OnAskAboutBlock;
    theme?: WeeklyPlanTheme;
    mode?: PlanViewMode;
    nowIso?: string;
};

export function RenderAnalysis({ analysis, onAskAboutBlock, mode }: AnalysisProps) {
    const version = resolveSchemaVersion("analysis", analysis.schema_version);
    if (version !== 1) {
        return <UnsupportedSchema kind="analysis" schemaVersion={analysis.schema_version} />;
    }
    return <AnalysisViewV1 analysis={analysis} onAskAboutBlock={onAskAboutBlock} mode={mode} />;
}

export function RenderSeasonPlan({ seasonPlan, selectedPhaseId, onAskAboutBlock, onPhaseSelect, mode }: SeasonProps) {
    const version = resolveSchemaVersion("season", seasonPlan.schema_version);
    if (version === 3) {
        return <SeasonPlanViewV3 seasonPlan={seasonPlan as SeasonPlanV3} selectedPhaseId={selectedPhaseId} onAskAboutBlock={onAskAboutBlock} onPhaseSelect={onPhaseSelect} mode={mode} />;
    }
    if (version !== 1) {
        return <UnsupportedSchema kind="season" schemaVersion={seasonPlan.schema_version} />;
    }
    return (
        <SeasonPlanViewV1
            seasonPlan={seasonPlan as UiSeasonPlan}
            selectedPhaseId={selectedPhaseId}
            onAskAboutBlock={onAskAboutBlock}
            onPhaseSelect={onPhaseSelect}
            mode={mode}
        />
    );
}

export function RenderWeeklyPlan({ weeklyPlan, highlightDayIds, onAskAboutBlock, theme, mode, nowIso }: WeeklyProps) {
    const version = resolveSchemaVersion("weekly", weeklyPlan.schema_version);
    if (version === 3) {
        return <WeeklyPlanViewV3 weeklyPlan={weeklyPlan as WeeklyPlanV3} highlightDayIds={highlightDayIds} onAskAboutBlock={onAskAboutBlock} theme={theme} mode={mode} nowIso={nowIso} />;
    }
    if (version !== 1) {
        return <UnsupportedSchema kind="weekly" schemaVersion={weeklyPlan.schema_version} />;
    }
    return (
        <WeeklyPlanViewV1
            weeklyPlan={weeklyPlan as UiWeeklyPlan}
            highlightDayIds={highlightDayIds}
            onAskAboutBlock={onAskAboutBlock}
            theme={theme}
            mode={mode}
        />
    );
}

function UnsupportedSchema({ kind, schemaVersion }: { kind: "analysis" | "season" | "weekly"; schemaVersion: number }) {
    return (
        <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100" role="alert">
            <div className="font-semibold">This {kind} artifact cannot be displayed</div>
            <div className="mt-1 text-amber-100/80">
                Unsupported {kind} schema version: {schemaVersion}. Regenerate this artifact with a supported schema.
            </div>
        </div>
    );
}
