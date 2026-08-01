"use client";

import {
    AlertTriangle,
    Check,
    ChevronRight,
    Dumbbell,
    Fuel,
    HeartPulse,
    MessageCircle,
    Route,
} from "lucide-react";

import MarkdownSnippet from "@/components/markdown_snippet";
import type { SemanticBlockV3 } from "@/components/plan-viewer/types";
import type { OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiHtmlBlockVariant } from "@/lib/types/ui-blocks";
import { semanticBlockText, semanticBlockTitle } from "@/lib/semantic-block";

type Props = {
    block: SemanticBlockV3;
    onAskAboutBlock?: OnAskAboutBlock;
    parentLabel: string;
    sourceTab: "season" | "weekly";
};

const VARIANT_BY_TYPE: Record<SemanticBlockV3["type"], UiHtmlBlockVariant> = {
    narrative: "generic",
    callout: "callout",
    checklist: "checklist",
    data_table: "generic",
    workout: "workout",
    interval_table: "workout",
    fueling: "fueling",
    recovery: "support",
    notes: "notes",
    phase_timeline: "meta",
    disclosure: "generic",
};

const ALIGN_CLASS = { left: "text-left", center: "text-center", right: "text-right" } as const;

function AskCoach({ block, onAskAboutBlock, parentLabel, sourceTab }: Props) {
    if (!onAskAboutBlock) return null;
    return (
        <button
            type="button"
            className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
            onClick={() => onAskAboutBlock({
                source_tab: sourceTab,
                block_key: block.block_id,
                block_variant: VARIANT_BY_TYPE[block.type],
                block_title: semanticBlockTitle(block),
                content_preview: semanticBlockText(block).slice(0, 180),
                parent_label: parentLabel,
            })}
        >
            <MessageCircle className="h-3 w-3" aria-hidden="true" />
            Ask coach
        </button>
    );
}

function BlockHeader({ block, ...props }: Props) {
    const title = semanticBlockTitle(block);
    if (!title && !props.onAskAboutBlock) return null;
    return (
        <div className="mb-2 flex items-start justify-between gap-4">
            {title ? <h4 className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--text-muted)]">{title}</h4> : <span />}
            <AskCoach block={block} {...props} />
        </div>
    );
}

export default function SemanticBlock({ block, ...props }: Props) {
    if (block.type === "narrative") {
        return (
            <div className="border-l border-sky-400/40 pl-4">
                <BlockHeader block={block} {...props} />
                <MarkdownSnippet markdown={block.markdown} className="text-sm text-[var(--text-secondary)]" />
            </div>
        );
    }

    if (block.type === "callout") {
        const toneClass = {
            neutral: "border-slate-400/25 bg-slate-400/[0.06]",
            info: "border-sky-400/30 bg-sky-400/[0.07]",
            success: "border-emerald-400/30 bg-emerald-400/[0.07]",
            warning: "border-amber-400/35 bg-amber-400/[0.08]",
            danger: "border-rose-400/35 bg-rose-400/[0.08]",
        }[block.tone];
        return (
            <div className={`rounded-xl border px-4 py-3 ${toneClass}`}>
                <div className="flex gap-3">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" aria-hidden="true" />
                    <div className="min-w-0 flex-1">
                        <BlockHeader block={block} {...props} />
                        <MarkdownSnippet markdown={block.markdown} className="text-sm text-[var(--text-secondary)]" />
                    </div>
                </div>
            </div>
        );
    }

    if (block.type === "checklist") {
        return (
            <div>
                <BlockHeader block={block} {...props} />
                <ul className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
                    {block.items.map((item) => (
                        <li key={item.item_id} className="flex gap-3 py-3">
                            <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full border border-emerald-400/35 bg-emerald-400/10 text-emerald-300">
                                <Check className="h-3 w-3" aria-hidden="true" />
                            </span>
                            <div>
                                <div className="text-sm font-semibold text-[var(--text-primary)]">{item.label}</div>
                                {item.detail_markdown && <MarkdownSnippet markdown={item.detail_markdown} className="mt-1 text-xs text-[var(--text-secondary)]" />}
                            </div>
                        </li>
                    ))}
                </ul>
            </div>
        );
    }

    if (block.type === "data_table") {
        return (
            <div className="overflow-hidden">
                <BlockHeader block={block} {...props} />
                <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
                    <table className="w-full min-w-[32rem] text-left text-xs">
                        <thead className="bg-white/[0.04] text-[var(--text-muted)]">
                            <tr>{block.columns.map((column) => <th key={column.key} className={`px-3 py-2.5 font-semibold ${ALIGN_CLASS[column.align]}`}>{column.label}</th>)}</tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--border)]">
                            {block.rows.map((row, rowIndex) => (
                                <tr key={`${block.block_id}-${rowIndex}`} className="text-[var(--text-secondary)]">
                                    {block.columns.map((column) => <td key={column.key} className={`px-3 py-3 align-top ${ALIGN_CLASS[column.align]}`}>{row[column.key]}</td>)}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    }

    if (block.type === "workout") {
        return (
            <div className="rounded-xl border border-violet-400/25 bg-[linear-gradient(135deg,rgba(139,92,246,0.11),rgba(56,189,248,0.05))] p-4">
                <div className="flex gap-3">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-violet-300/20 bg-violet-300/10 text-violet-200"><Dumbbell className="h-4 w-4" /></span>
                    <div className="min-w-0 flex-1">
                        <BlockHeader block={block} {...props} />
                        <h4 className="text-base font-semibold text-[var(--text-primary)]">{block.title}</h4>
                        <MarkdownSnippet markdown={block.objective_markdown} className="mt-1 text-sm text-[var(--text-secondary)]" />
                    </div>
                </div>
            </div>
        );
    }

    if (block.type === "interval_table") {
        return (
            <div>
                <BlockHeader block={block} {...props} />
                <div className="divide-y divide-[var(--border)] border-y border-[var(--border)]">
                    {block.intervals.map((interval, index) => (
                        <div key={`${block.block_id}-${index}`} className="grid gap-1 py-3 sm:grid-cols-[7rem_6rem_1fr] sm:gap-4">
                            <div className="text-xs font-bold uppercase tracking-wide text-sky-300">{interval.label}</div>
                            <div className="text-sm tabular-nums text-[var(--text-primary)]">{interval.duration}</div>
                            <div className="text-sm text-[var(--text-secondary)]">{interval.prescription}{interval.recovery ? <span className="block text-xs text-[var(--text-muted)]">Recovery: {interval.recovery}</span> : null}</div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (block.type === "fueling") {
        const entries = [["Before", block.before_markdown], ["During", block.during_markdown], ["After", block.after_markdown]] as const;
        return (
            <div className="rounded-xl border border-amber-300/20 bg-amber-300/[0.05] p-4">
                <div className="mb-3 flex items-center gap-2 text-amber-200"><Fuel className="h-4 w-4" /><span className="text-xs font-bold uppercase tracking-[0.14em]">{block.title ?? "Fueling"}</span></div>
                <div className="grid gap-3 sm:grid-cols-3">
                    {entries.filter(([, markdown]) => markdown).map(([label, markdown]) => (
                        <div key={label}><div className="text-[10px] font-bold uppercase tracking-wide text-[var(--text-muted)]">{label}</div><MarkdownSnippet markdown={markdown ?? ""} className="mt-1 text-xs text-[var(--text-secondary)]" /></div>
                    ))}
                </div>
                <div className="mt-3"><AskCoach block={block} {...props} /></div>
            </div>
        );
    }

    if (block.type === "recovery") {
        return (
            <div className="flex gap-3 border-y border-[var(--border)] py-3">
                <HeartPulse className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
                <div className="min-w-0 flex-1"><BlockHeader block={block} {...props} /><MarkdownSnippet markdown={block.markdown} className="text-sm text-[var(--text-secondary)]" /></div>
            </div>
        );
    }

    if (block.type === "phase_timeline") {
        return (
            <div>
                <BlockHeader block={block} {...props} />
                <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {block.milestones.map((milestone, index) => (
                        <li key={`${block.block_id}-${milestone.phase_id}`} className="relative border-l border-sky-400/35 pl-3">
                            <div className="text-[10px] font-bold uppercase tracking-wide text-sky-300">{String(index + 1).padStart(2, "0")}</div>
                            <div className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{milestone.label}</div>
                            {milestone.note && <div className="mt-1 text-xs text-[var(--text-muted)]">{milestone.note}</div>}
                        </li>
                    ))}
                </ol>
            </div>
        );
    }

    if (block.type === "disclosure") {
        return (
            <details className="group border-y border-[var(--border)] py-3" open={block.default_open}>
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-[var(--text-primary)]">
                    <span>{block.label}</span><ChevronRight className="h-4 w-4 text-[var(--text-muted)] transition-transform group-open:rotate-90" />
                </summary>
                <MarkdownSnippet markdown={block.summary_markdown} className="mt-3 text-sm text-[var(--text-secondary)]" />
                <div className="mt-3"><AskCoach block={block} {...props} /></div>
            </details>
        );
    }

    return (
        <div className="border-l border-[var(--border)] pl-4">
            <BlockHeader block={block} {...props} />
            <div className="flex gap-2"><Route className="mt-0.5 h-4 w-4 text-[var(--text-muted)]" /><MarkdownSnippet markdown={block.markdown} className="text-sm italic text-[var(--text-secondary)]" /></div>
        </div>
    );
}
