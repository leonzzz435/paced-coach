import { RenderAnalysis } from "@/components/plan-viewer/versioned/plan-renderer";
import type { PlanViewMode } from "@/components/plan-viewer/types";
import type { OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiAnalysis } from "@/lib/types/ui-blocks";

type Props = {
    analysis: UiAnalysis;
    onAskAboutBlock?: OnAskAboutBlock;
    mode?: PlanViewMode;
};

export default function AnalysisView({ analysis, onAskAboutBlock, mode }: Props) {
    return <RenderAnalysis analysis={analysis} onAskAboutBlock={onAskAboutBlock} mode={mode} />;
}
