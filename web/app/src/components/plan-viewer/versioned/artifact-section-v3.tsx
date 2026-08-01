import { ChevronDown } from "lucide-react";

import MarkdownSnippet from "@/components/markdown_snippet";
import type { ArtifactSectionV3 } from "@/components/plan-viewer/types";
import SemanticBlock from "@/components/plan-viewer/versioned/semantic-block-v3";
import type { OnAskAboutBlock } from "@/lib/types/ask-about";

type Props = {
    section: ArtifactSectionV3;
    sourceTab: "season" | "weekly";
    onAskAboutBlock?: OnAskAboutBlock;
    collapsed?: boolean;
};

function SectionBody({ section, sourceTab, onAskAboutBlock }: Omit<Props, "collapsed">) {
    return (
        <div className="space-y-5">
            {section.summary_markdown && (
                <MarkdownSnippet markdown={section.summary_markdown} className="max-w-3xl text-sm text-[var(--text-secondary)]" />
            )}
            {section.blocks.map((block) => (
                <SemanticBlock
                    key={block.block_id}
                    block={block}
                    onAskAboutBlock={onAskAboutBlock}
                    parentLabel={section.title}
                    sourceTab={sourceTab}
                />
            ))}
        </div>
    );
}

export default function ArtifactSection({ section, sourceTab, onAskAboutBlock, collapsed = false }: Props) {
    if (section.disclosure_intent === "collapsible" || collapsed) {
        return (
            <details className="group border-t border-[var(--border)] py-5" open={!collapsed}>
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
                    <div>
                        <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-sky-300/80">Coach layer</div>
                        <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{section.title}</h3>
                    </div>
                    <ChevronDown className="h-4 w-4 text-[var(--text-muted)] transition-transform group-open:rotate-180" aria-hidden="true" />
                </summary>
                <div className="mt-5"><SectionBody section={section} sourceTab={sourceTab} onAskAboutBlock={onAskAboutBlock} /></div>
            </details>
        );
    }

    return (
        <section className={`border-t border-[var(--border)] py-6 ${section.emphasis === "primary" ? "sm:grid sm:grid-cols-[12rem_1fr] sm:gap-8" : ""}`}>
            <div className="mb-4 sm:mb-0">
                <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-sky-300/80">Coach layer</div>
                <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{section.title}</h3>
            </div>
            <SectionBody section={section} sourceTab={sourceTab} onAskAboutBlock={onAskAboutBlock} />
        </section>
    );
}
