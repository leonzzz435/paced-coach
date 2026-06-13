import { RenderWeeklyPlan } from "@/components/plan-viewer/versioned/plan-renderer";
import type { PlanViewMode, WeeklyPlanTheme } from "@/components/plan-viewer/types";
import type { OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiWeeklyPlan } from "@/lib/types/ui-blocks";

type Props = {
    weeklyPlan: UiWeeklyPlan;
    highlightDayIds?: string[];
    onAskAboutBlock?: OnAskAboutBlock;
    theme?: WeeklyPlanTheme;
    mode?: PlanViewMode;
};

export default function WeeklyPlanView({ weeklyPlan, highlightDayIds, onAskAboutBlock, theme, mode }: Props) {
    return (
        <RenderWeeklyPlan
            weeklyPlan={weeklyPlan}
            highlightDayIds={highlightDayIds}
            onAskAboutBlock={onAskAboutBlock}
            theme={theme}
            mode={mode}
        />
    );
}
