"use client";

import { useMemo, useState, type ReactNode } from "react";

import BlockDisclosure from "@/components/plan-viewer/components/block-disclosure";
import { buildContentPreview, type AskAboutContext, type OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiDisclosureNode, UiHtmlBlock } from "@/lib/types/ui-blocks";

type Props = {
    nodes: UiDisclosureNode[];
    sourceTab: AskAboutContext["source_tab"];
    parentLabel: string;
    onAskAboutBlock?: OnAskAboutBlock;
    renderBlockFooter?: (block: UiHtmlBlock) => ReactNode;
    depth?: number;
};

export function blocksToFallbackNodes(blocks: UiHtmlBlock[], nodePrefix: string, defaultTitle: string): UiDisclosureNode[] {
    return blocks.map((block, index) => ({
        node_id: `${nodePrefix}-${block.key}-${index}`,
        title: block.title ?? defaultTitle,
        summary: buildContentPreview(block.content_html, 120),
        tone: block.tone ?? "neutral",
        disclosure_mode: "inline" as const,
        default_open: true,
        blocks: [block],
        children: [],
    }));
}

function nodeSummary(node: UiDisclosureNode): string {
    if (node.summary) return node.summary;
    const blockCount = node.blocks.length;
    const childCount = node.children.length;
    if (blockCount === 0 && childCount === 0) return "No details";
    const bits: string[] = [];
    if (childCount > 0) bits.push(`${childCount} nested`);
    if (blockCount > 0) bits.push(`${blockCount} block${blockCount > 1 ? "s" : ""}`);
    return bits.join(" | ");
}

function resolveDisclosureMode(node: UiDisclosureNode): "collapsible" | "inline" {
    const mode = node.disclosure_mode ?? "auto";
    if (mode === "collapsible") return "collapsible";
    if (mode === "inline") return "inline";
    if (node.children.length > 0) return "collapsible";
    if (node.blocks.length > 1) return "collapsible";
    return "inline";
}

function resolveDefaultOpen(node: UiDisclosureNode): boolean {
    if (typeof node.default_open === "boolean") return node.default_open;
    return false;
}

export default function DisclosureNodeTree({
    nodes,
    sourceTab,
    parentLabel,
    onAskAboutBlock,
    renderBlockFooter,
    depth = 0,
}: Props) {
    return (
        <div className={`space-y-2 ${depth > 0 ? "pl-2" : ""}`}>
            {nodes.map((node) => (
                <NodeDisclosure
                    key={node.node_id}
                    depth={depth}
                    node={node}
                    onAskAboutBlock={onAskAboutBlock}
                    parentLabel={parentLabel}
                    renderBlockFooter={renderBlockFooter}
                    sourceTab={sourceTab}
                />
            ))}
        </div>
    );
}

function NodeDisclosure({
    node,
    sourceTab,
    parentLabel,
    onAskAboutBlock,
    renderBlockFooter,
    depth,
}: {
    node: UiDisclosureNode;
    sourceTab: AskAboutContext["source_tab"];
    parentLabel: string;
    onAskAboutBlock?: OnAskAboutBlock;
    renderBlockFooter?: (block: UiHtmlBlock) => ReactNode;
    depth: number;
}) {
    const [open, setOpen] = useState(resolveDefaultOpen(node));

    const summary = useMemo(() => nodeSummary(node), [node]);
    const nextParentLabel = `${parentLabel} > ${node.title}`;
    const mode = resolveDisclosureMode(node);
    const isSingleLeafNode = node.blocks.length === 1 && node.children.length === 0;
    const showInlineHeader = !isSingleLeafNode;

    if (isSingleLeafNode) {
        const [block] = node.blocks;
        if (!block) return null;
        return (
            <BlockDisclosure
                block={block}
                collapsible={false}
                compact={true}
                fallbackTitle={node.title}
                onAskAboutBlock={onAskAboutBlock}
                parentLabel={nextParentLabel}
                renderFooter={renderBlockFooter}
                sourceTab={sourceTab}
            />
        );
    }

    if (mode === "inline") {
        return (
            <div className="space-y-2">
                {showInlineHeader && (
                    <div className="px-1">
                        <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">{node.title}</div>
                        <div className="mt-0.5 text-xs text-[var(--text-muted)]">{summary}</div>
                    </div>
                )}

                {node.blocks.map((block) => (
                    <BlockDisclosure
                        key={block.key}
                        block={block}
                        collapsible={false}
                        compact={true}
                        fallbackTitle={showInlineHeader ? node.title : undefined}
                        onAskAboutBlock={onAskAboutBlock}
                        parentLabel={nextParentLabel}
                        renderFooter={renderBlockFooter}
                        sourceTab={sourceTab}
                    />
                ))}

                {node.children.length > 0 && (
                    <DisclosureNodeTree
                        depth={depth + 1}
                        nodes={node.children}
                        onAskAboutBlock={onAskAboutBlock}
                        parentLabel={nextParentLabel}
                        renderBlockFooter={renderBlockFooter}
                        sourceTab={sourceTab}
                    />
                )}
            </div>
        );
    }

    return (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)]">
            <button
                className="flex w-full items-start justify-between gap-2 rounded-lg px-3 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--border-accent)] focus-visible:ring-inset"
                type="button"
                onClick={() => setOpen((prev) => !prev)}
            >
                <div>
                    <div className="text-xs font-bold uppercase tracking-wide text-[var(--text-secondary)]">{node.title}</div>
                    <div className="mt-1 text-xs text-[var(--text-muted)]">{summary}</div>
                </div>
                <span className="text-[11px] font-semibold uppercase text-[var(--text-muted)]">{open ? "Hide" : "Open"}</span>
            </button>

            <div className={`pv-disclosure-body ${open ? "pv-disclosure-body--open" : ""}`}>
                <div className="space-y-2 border-t border-[var(--border)] px-3 py-3">
                    {node.blocks.map((block) => (
                        <BlockDisclosure
                            key={block.key}
                            block={block}
                            collapsible={false}
                            compact={true}
                            fallbackTitle={node.title}
                            onAskAboutBlock={onAskAboutBlock}
                            parentLabel={nextParentLabel}
                            renderFooter={renderBlockFooter}
                            sourceTab={sourceTab}
                        />
                    ))}

                    {node.children.length > 0 && (
                        <DisclosureNodeTree
                            depth={depth + 1}
                            nodes={node.children}
                            onAskAboutBlock={onAskAboutBlock}
                            parentLabel={nextParentLabel}
                            renderBlockFooter={renderBlockFooter}
                            sourceTab={sourceTab}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}
