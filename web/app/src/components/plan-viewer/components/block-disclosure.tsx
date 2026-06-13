"use client";

import { useMemo, useState, type ReactNode } from "react";

import HtmlSnippet from "@/components/html_snippet";
import { buildContentPreview, type AskAboutContext, type OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiHtmlBlock } from "@/lib/types/ui-blocks";

type Props = {
    sourceTab: AskAboutContext["source_tab"];
    block: UiHtmlBlock;
    parentLabel: string;
    fallbackTitle?: string;
    defaultOpen?: boolean;
    collapsible?: boolean;
    compact?: boolean;
    onAskAboutBlock?: OnAskAboutBlock;
    renderFooter?: (block: UiHtmlBlock) => ReactNode;
};

export default function BlockDisclosure({
    sourceTab,
    block,
    parentLabel,
    fallbackTitle,
    defaultOpen = false,
    collapsible = true,
    compact = false,
    onAskAboutBlock,
    renderFooter,
}: Props) {
    const [open, setOpen] = useState(defaultOpen);

    const blockTitle = block.title ?? fallbackTitle ?? "Detail";
    const preview = useMemo(() => buildContentPreview(block.content_html, 180), [block.content_html]);

    if (!collapsible) {
        if (compact) {
            return (
                <div className="space-y-2">
                    <HtmlSnippet className="pv-content text-sm leading-relaxed text-[var(--text-secondary,#94a3b8)]" html={block.content_html} />
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>{renderFooter?.(block)}</div>
                        <button
                            className="pv-ask-button"
                            type="button"
                            onClick={() =>
                                onAskAboutBlock?.({
                                    source_tab: sourceTab,
                                    block_key: block.key,
                                    block_variant: block.variant,
                                    block_title: blockTitle,
                                    content_preview: buildContentPreview(block.content_html),
                                    parent_label: parentLabel,
                                })
                            }
                        >
                            Ask about this
                        </button>
                    </div>
                </div>
            );
        }
        return (
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)]">
                <div className="px-3 pb-3 pt-2.5">
                    <div className="mb-2 flex items-center justify-between gap-2">
                        <div className="min-w-0">
                            <div className="truncate text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">{blockTitle}</div>
                            <div className="mt-1 text-xs text-[var(--text-muted)]">{preview || "Detail"}</div>
                        </div>
                        <span className="rounded-full bg-[var(--surface-elevated)] px-2 py-0.5 text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                            {block.variant}
                        </span>
                    </div>
                    <HtmlSnippet className="pv-content text-sm leading-relaxed text-[var(--text-secondary,#94a3b8)]" html={block.content_html} />
                    <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                        <div>{renderFooter?.(block)}</div>
                        <button
                            className="pv-ask-button"
                            type="button"
                            onClick={() =>
                                onAskAboutBlock?.({
                                    source_tab: sourceTab,
                                    block_key: block.key,
                                    block_variant: block.variant,
                                    block_title: blockTitle,
                                    content_preview: buildContentPreview(block.content_html),
                                    parent_label: parentLabel,
                                })
                            }
                        >
                            Ask about this
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)]">
            <button
                type="button"
                className="flex w-full items-start justify-between gap-2 rounded-lg px-3 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--border-accent)] focus-visible:ring-inset"
                onClick={() => setOpen((prev) => !prev)}
            >
                <div className="min-w-0">
                    <div className="truncate text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">{blockTitle}</div>
                    <div className="mt-1 text-xs text-[var(--text-muted)]">{preview || "Tap to expand block details"}</div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                    <span className="rounded-full bg-[var(--surface-elevated)] px-2 py-0.5 text-[10px] font-semibold uppercase text-[var(--text-muted)]">
                        {block.variant}
                    </span>
                    <span className="text-[11px] font-semibold text-[var(--text-muted)]">{open ? "Hide" : "Open"}</span>
                </div>
            </button>

            <div className={`pv-disclosure-body ${open ? "pv-disclosure-body--open" : ""}`}>
                <div className="border-t border-[var(--border)] px-3 pb-3 pt-2">
                    <HtmlSnippet className="pv-content text-sm leading-relaxed text-[var(--text-secondary,#94a3b8)]" html={block.content_html} />
                    <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                        <div>{renderFooter?.(block)}</div>
                        <button
                            className="pv-ask-button"
                            type="button"
                            onClick={() =>
                                onAskAboutBlock?.({
                                    source_tab: sourceTab,
                                    block_key: block.key,
                                    block_variant: block.variant,
                                    block_title: blockTitle,
                                    content_preview: buildContentPreview(block.content_html),
                                    parent_label: parentLabel,
                                })
                            }
                        >
                            Ask about this
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
