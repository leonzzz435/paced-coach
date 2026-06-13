import AnalysisViewV1 from "@/components/plan-viewer/versioned/analysis-view-v1";
import SeasonPlanViewV1 from "@/components/plan-viewer/versioned/season-plan-view-v1";
import type { PlanViewMode, WeeklyPlanTheme } from "@/components/plan-viewer/types";
import WeeklyPlanViewV1 from "@/components/plan-viewer/versioned/weekly-plan-view-v1";
import { resolveSchemaVersion } from "@/lib/plan-version";
import type { OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiAnalysis, UiSeasonPlan, UiWeeklyPlan } from "@/lib/types/ui-blocks";

type AnalysisProps = {
    analysis: UiAnalysis;
    onAskAboutBlock?: OnAskAboutBlock;
    mode?: PlanViewMode;
};
type SeasonProps = {
    seasonPlan: UiSeasonPlan;
    selectedPhaseId?: string | null;
    onAskAboutBlock?: OnAskAboutBlock;
    onPhaseSelect?: (phaseId: string | null) => void;
    mode?: PlanViewMode;
};
type WeeklyProps = {
    weeklyPlan: UiWeeklyPlan;
    highlightDayIds?: string[];
    onAskAboutBlock?: OnAskAboutBlock;
    theme?: WeeklyPlanTheme;
    mode?: PlanViewMode;
};

export function RenderAnalysis({ analysis, onAskAboutBlock, mode }: AnalysisProps) {
    const version = resolveSchemaVersion(analysis.schema_version);
    if (version === null && analysis.schema_version) {
        return <UnsupportedSchema kind="analysis" schemaVersion={analysis.schema_version} />;
    }
    return <AnalysisViewV1 analysis={analysis} onAskAboutBlock={onAskAboutBlock} mode={mode} />;
}

export function RenderSeasonPlan({ seasonPlan, selectedPhaseId, onAskAboutBlock, onPhaseSelect, mode }: SeasonProps) {
    const version = resolveSchemaVersion(seasonPlan.schema_version);
    if (version === null && seasonPlan.schema_version) {
        return <UnsupportedSchema kind="season" schemaVersion={seasonPlan.schema_version} />;
    }
    return (
        <SeasonPlanViewV1
            seasonPlan={seasonPlan}
            selectedPhaseId={selectedPhaseId}
            onAskAboutBlock={onAskAboutBlock}
            onPhaseSelect={onPhaseSelect}
            mode={mode}
        />
    );
}

export function RenderWeeklyPlan({ weeklyPlan, highlightDayIds, onAskAboutBlock, theme, mode }: WeeklyProps) {
    const version = resolveSchemaVersion(weeklyPlan.schema_version);
    if (version === null && weeklyPlan.schema_version) {
        return <UnsupportedSchema kind="weekly" schemaVersion={weeklyPlan.schema_version} />;
    }
    return (
        <WeeklyPlanViewV1
            weeklyPlan={weeklyPlan}
            highlightDayIds={highlightDayIds}
            onAskAboutBlock={onAskAboutBlock}
            theme={theme}
            mode={mode}
        />
    );
}

function UnsupportedSchema({ kind, schemaVersion }: { kind: "analysis" | "season" | "weekly"; schemaVersion: number }) {
    return (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            Unsupported {kind} schema version: {schemaVersion}. Regenerate plans with schema v1.
        </div>
    );
}
