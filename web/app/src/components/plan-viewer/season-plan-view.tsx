import { RenderSeasonPlan } from "@/components/plan-viewer/versioned/plan-renderer";
import type { PlanViewMode } from "@/components/plan-viewer/types";
import type { OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiSeasonPlan } from "@/lib/types/ui-blocks";

type Props = {
    seasonPlan: UiSeasonPlan;
    selectedPhaseId?: string | null;
    onAskAboutBlock?: OnAskAboutBlock;
    onPhaseSelect?: (phaseId: string | null) => void;
    mode?: PlanViewMode;
};

export default function SeasonPlanView({ seasonPlan, selectedPhaseId, onAskAboutBlock, onPhaseSelect, mode }: Props) {
    return (
        <RenderSeasonPlan
            seasonPlan={seasonPlan}
            selectedPhaseId={selectedPhaseId}
            onAskAboutBlock={onAskAboutBlock}
            onPhaseSelect={onPhaseSelect}
            mode={mode}
        />
    );
}
