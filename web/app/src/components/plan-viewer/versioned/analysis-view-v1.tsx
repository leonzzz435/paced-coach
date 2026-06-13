"use client";

import { useMemo, useState } from "react";

import DisclosureNodeTree, { blocksToFallbackNodes } from "@/components/plan-viewer/components/disclosure-node-tree";
import type { PlanViewMode } from "@/components/plan-viewer/types";
import { type OnAskAboutBlock } from "@/lib/types/ask-about";
import type { UiAnalysis, UiKpiStatus } from "@/lib/types/ui-blocks";

const STATUS_STYLES: Record<UiKpiStatus, { soft: string; border: string; badge: string; dot: string; card: string }> = {
    good: {
        soft: "bg-emerald-500/10",
        border: "border-emerald-400/25",
        badge: "bg-emerald-400/15 text-emerald-200 ring-1 ring-inset ring-emerald-400/25",
        dot: "bg-emerald-300",
        card: "bg-[linear-gradient(180deg,rgba(16,185,129,0.12),rgba(15,23,42,0.96))]",
    },
    warning: {
        soft: "bg-amber-500/10",
        border: "border-amber-400/25",
        badge: "bg-amber-400/15 text-amber-100 ring-1 ring-inset ring-amber-400/25",
        dot: "bg-amber-300",
        card: "bg-[linear-gradient(180deg,rgba(245,158,11,0.12),rgba(15,23,42,0.96))]",
    },
    danger: {
        soft: "bg-rose-500/10",
        border: "border-rose-400/25",
        badge: "bg-rose-400/15 text-rose-100 ring-1 ring-inset ring-rose-400/25",
        dot: "bg-rose-300",
        card: "bg-[linear-gradient(180deg,rgba(244,63,94,0.12),rgba(15,23,42,0.96))]",
    },
    neutral: {
        soft: "bg-sky-500/10",
        border: "border-sky-400/25",
        badge: "bg-sky-400/15 text-sky-100 ring-1 ring-inset ring-sky-400/25",
        dot: "bg-sky-300",
        card: "bg-[linear-gradient(180deg,rgba(56,189,248,0.12),rgba(15,23,42,0.96))]",
    },
};

const STATUS_LABELS: Record<UiKpiStatus, string> = {
    danger: "risk",
    warning: "watch",
    good: "good",
    neutral: "stable",
};

const DOMAIN_LABELS: Record<string, string> = {
    load: "Load & Training",
    recovery: "Recovery",
    performance: "Performance",
    body: "Body",
    sleep: "Sleep",
    other: "Other",
};

const DOMAIN_ORDER = ["load", "recovery", "performance", "body", "sleep", "other"];

type Props = {
    analysis: UiAnalysis;
    onAskAboutBlock?: OnAskAboutBlock;
    mode?: PlanViewMode;
};

type DomainGroup = {
    key: string;
    title: string;
    kpis: UiAnalysis["kpis"];
    statusSummary: string;
    status: UiKpiStatus;
};

function normalizeDomain(value?: string | null): string {
    const cleaned = (value ?? "").trim().toLowerCase();
    return cleaned.length > 0 ? cleaned : "other";
}

function domainLabel(key: string): string {
    return DOMAIN_LABELS[key] ?? key.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function statusLabel(status: UiKpiStatus): string {
    return STATUS_LABELS[status];
}

function statusSummary(kpis: UiAnalysis["kpis"]): { text: string; status: UiKpiStatus } {
    const counts = { danger: 0, warning: 0, good: 0, neutral: 0 };
    kpis.forEach((kpi) => {
        counts[kpi.status] += 1;
    });

    const pieces = [
        counts.danger > 0 ? `${counts.danger} ${statusLabel("danger")}` : null,
        counts.warning > 0 ? `${counts.warning} ${statusLabel("warning")}` : null,
        counts.good > 0 ? `${counts.good} ${statusLabel("good")}` : null,
        counts.neutral > 0 ? `${counts.neutral} ${statusLabel("neutral")}` : null,
    ].filter(Boolean);

    const aggregateStatus: UiKpiStatus = counts.danger > 0 ? "danger" : counts.warning > 0 ? "warning" : counts.good > 0 ? "good" : "neutral";

    return {
        text: pieces.length > 0 ? pieces.join(" | ") : "Neutral signal",
        status: aggregateStatus,
    };
}

function formatReportDate(value?: string | null): string | null {
    if (!value) return null;

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return null;

    return new Intl.DateTimeFormat("en", {
        month: "short",
        day: "numeric",
        year: "numeric",
    }).format(parsed);
}

export default function AnalysisViewV1({ analysis, onAskAboutBlock, mode = "full" }: Props) {
    const [showDetails, setShowDetails] = useState(false);
    const isLandingMode = mode === "landing";

    const domainGroups = useMemo(() => {
        const grouped = new Map<string, UiAnalysis["kpis"]>();
        analysis.kpis.forEach((kpi) => {
            const domain = normalizeDomain(kpi.domain);
            const bucket = grouped.get(domain) ?? [];
            bucket.push(kpi);
            grouped.set(domain, bucket);
        });

        const keys = Array.from(grouped.keys()).sort((a, b) => {
            const ai = DOMAIN_ORDER.indexOf(a);
            const bi = DOMAIN_ORDER.indexOf(b);
            if (ai === -1 && bi === -1) return a.localeCompare(b);
            if (ai === -1) return 1;
            if (bi === -1) return -1;
            return ai - bi;
        });

        return keys.map((key) => {
            const kpis = grouped.get(key) ?? [];
            const summary = statusSummary(kpis);
            return {
                key,
                title: domainLabel(key),
                kpis,
                statusSummary: summary.text,
                status: summary.status,
            } satisfies DomainGroup;
        });
    }, [analysis.kpis]);

    const dashboardKpis = useMemo(() => {
        const source = analysis.dashboard_kpis && analysis.dashboard_kpis.length > 0 ? analysis.dashboard_kpis : analysis.kpis;
        return source.slice(0, isLandingMode ? 3 : 6);
    }, [analysis.dashboard_kpis, analysis.kpis, isLandingMode]);
    const aggregateSource = analysis.kpis.length > 0 ? analysis.kpis : dashboardKpis;
    const kpiAggregate = useMemo(() => statusSummary(aggregateSource), [aggregateSource]);
    const reportDateLabel = useMemo(() => formatReportDate(analysis.created_at), [analysis.created_at]);

    const [openDomains, setOpenDomains] = useState<Record<string, boolean>>(() => {
        const initial: Record<string, boolean> = {};
        domainGroups.forEach((group) => {
            initial[group.key] = group.status === "danger" || group.status === "warning";
        });
        if (domainGroups.length > 0 && !Object.values(initial).some(Boolean)) {
            initial[domainGroups[0].key] = true;
        }
        return initial;
    });
    const [openSections, setOpenSections] = useState<Record<string, boolean>>({});

    const toggleDomain = (domainKey: string) => {
        setOpenDomains((prev) => ({ ...prev, [domainKey]: !prev[domainKey] }));
    };

    const toggleSection = (sectionId: string) => {
        setOpenSections((prev) => ({ ...prev, [sectionId]: !prev[sectionId] }));
    };

    return (
        <div className="space-y-5">
            <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.12),transparent_38%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.08),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-5 shadow-[0_18px_36px_rgba(2,6,23,0.18)]">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="max-w-2xl">
                        <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">
                            Coach&apos;s Brief
                        </div>
                        <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                            {analysis.headline_brief?.trim() || "Training signal review across load, recovery, performance, and planning outputs."}
                        </p>
                        {analysis.coach_action && (
                            <div className="mt-3 flex items-start gap-2 rounded-lg border border-emerald-400/25 bg-emerald-500/10 px-3 py-2.5">
                                <span className="mt-0.5 shrink-0 text-[10px] font-bold uppercase tracking-wide text-emerald-300">Action</span>
                                <span className="text-sm font-medium text-[var(--text-primary)]">{analysis.coach_action}</span>
                            </div>
                        )}
                    </div>
                    <span className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase ${STATUS_STYLES[kpiAggregate.status].badge}`}>
                        {kpiAggregate.text}
                    </span>
                </div>

                {reportDateLabel && (
                    <div className="mt-3 text-[10px] text-[var(--text-muted)]">{reportDateLabel}</div>
                )}
            </section>

            {dashboardKpis.length > 0 && (
                <section className={`grid gap-3 ${isLandingMode ? "grid-cols-1 sm:grid-cols-3" : "grid-cols-2 sm:grid-cols-3"}`}>
                    {dashboardKpis.map((kpi) => {
                        const style = STATUS_STYLES[kpi.status] ?? STATUS_STYLES.neutral;
                        return (
                            <div key={kpi.kpi_id} className={`rounded-2xl border p-3 shadow-[0_14px_28px_rgba(2,6,23,0.16)] ${style.border} ${style.card}`}>
                                <div className="flex items-center justify-between gap-2">
                                    <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--text-muted)]">{kpi.label}</span>
                                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${style.badge}`}>
                                        {statusLabel(kpi.status)}
                                    </span>
                                </div>
                                <div className="mt-2 text-lg font-bold tracking-tight text-[var(--text-primary)]">{kpi.value}</div>
                                {kpi.trend && <div className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">{kpi.trend}</div>}
                            </div>
                        );
                    })}
                </section>
            )}

            {!isLandingMode && (analysis.kpis.length > 0 || analysis.sections.length > 0) && (
                <button
                    type="button"
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] py-2.5 text-xs font-semibold text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-elevated)] hover:text-[var(--text-primary)]"
                    onClick={() => setShowDetails((prev) => !prev)}
                >
                    {showDetails ? "Hide full analysis" : "Show full analysis"}
                    <span className="text-[10px]">{showDetails ? "\u25B2" : "\u25BC"}</span>
                </button>
            )}

            {!isLandingMode && showDetails && (
                <>
                    {domainGroups.length > 0 && (
                        <section className="space-y-3">
                            <div className="px-1 text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
                                KPI Clusters ({analysis.kpis.length} across {domainGroups.length} domains)
                            </div>

                            {domainGroups.map((group) => {
                                const style = STATUS_STYLES[group.status] ?? STATUS_STYLES.neutral;
                                const isOpen = openDomains[group.key] ?? false;
                                return (
                                    <article key={group.key} className={`overflow-hidden rounded-2xl border bg-[var(--surface)] shadow-[0_16px_32px_rgba(2,6,23,0.18)] ${style.border}`}>
                                        <button
                                            type="button"
                                            className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left ${style.soft}`}
                                            onClick={() => toggleDomain(group.key)}
                                        >
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <span className={`inline-block h-2 w-2 rounded-full ${style.dot}`} />
                                                    <span className="text-xs font-bold uppercase tracking-wide text-[var(--text-primary)]">{group.title}</span>
                                                </div>
                                                <p className="mt-1 text-xs text-[var(--text-secondary)]">{group.kpis.length} KPIs | {group.statusSummary}</p>
                                            </div>
                                            <span className="rounded-full bg-white/8 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-secondary)] ring-1 ring-inset ring-white/10">
                                                {isOpen ? "Hide" : "Open"}
                                            </span>
                                        </button>

                                        {isOpen && (
                                            <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
                                                {group.kpis.map((kpi) => {
                                                    const kpiStyle = STATUS_STYLES[kpi.status] ?? STATUS_STYLES.neutral;
                                                    return (
                                                        <div key={kpi.kpi_id} className={`flex flex-col rounded-2xl border p-3 shadow-[0_14px_28px_rgba(2,6,23,0.16)] ${kpiStyle.border} ${kpiStyle.card}`}>
                                                            <div className="flex items-center justify-between gap-2">
                                                                <div className="min-w-0">
                                                                    <div className="flex items-start gap-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                                                                        <span className={`shrink-0 mt-1 inline-block h-2 w-2 rounded-full ${kpiStyle.dot}`} />
                                                                        <span className="leading-snug">{kpi.label}</span>
                                                                    </div>
                                                                </div>
                                                                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${kpiStyle.badge}`}>
                                                                    {statusLabel(kpi.status)}
                                                                </span>
                                                            </div>
                                                            <div className="mt-2 text-xl font-bold tracking-tight text-[var(--text-primary)]">{kpi.value}</div>
                                                            <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">{kpi.trend ?? "No trend note"}</p>
                                                            <div className="mt-auto pt-3 pb-1 flex justify-end">
                                                                <button
                                                                    className="pv-ask-button hidden sm:inline-flex"
                                                                    type="button"
                                                                    onClick={() =>
                                                                        onAskAboutBlock?.({
                                                                            source_tab: "analysis",
                                                                            block_key: kpi.kpi_id,
                                                                            block_variant: "meta",
                                                                            block_title: kpi.label,
                                                                            content_preview: `${kpi.value}${kpi.trend ? ` ${kpi.trend}` : ""}`.slice(0, 200),
                                                                            parent_label: group.title,
                                                                        })
                                                                    }
                                                                >
                                                                    Ask
                                                                </button>
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </article>
                                );
                            })}
                        </section>
                    )}

                    {analysis.sections.length > 0 && (
                        <section className="space-y-3">
                            <div className="px-1 text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
                                Coaching Sections
                            </div>

                            {analysis.sections.map((section) => {
                                const sectionStyle = STATUS_STYLES[section.tone] ?? STATUS_STYLES.neutral;
                                const isOpen = openSections[section.section_id] ?? false;
                                const nodes =
                                    section.nodes && section.nodes.length > 0
                                        ? section.nodes
                                        : blocksToFallbackNodes(section.blocks ?? [], section.section_id, section.title);
                                return (
                                    <article key={section.section_id} className={`overflow-hidden rounded-xl border bg-[var(--surface)] shadow-[0_16px_32px_rgba(2,6,23,0.18)] ${sectionStyle.border}`}>
                                        <button
                                            type="button"
                                            className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left ${sectionStyle.soft}`}
                                            onClick={() => toggleSection(section.section_id)}
                                        >
                                            <div className="space-y-1">
                                                <div className="flex items-center gap-2">
                                                    <span className={`inline-block h-2 w-2 rounded-full ${sectionStyle.dot}`} />
                                                    <span className="text-xs font-bold uppercase tracking-wide text-[var(--text-primary)]">{section.title}</span>
                                                </div>
                                                <p className="text-xs text-[var(--text-secondary)]">{section.summary ?? "Tap to expand section details"}</p>
                                            </div>
                                            <span className="text-xs font-semibold text-[var(--text-secondary)]">{isOpen ? "Hide" : "Show"}</span>
                                        </button>

                                        {isOpen && (
                                            <div className="border-t border-[var(--border)] p-4">
                                                <DisclosureNodeTree
                                                    nodes={nodes}
                                                    onAskAboutBlock={onAskAboutBlock}
                                                    parentLabel={section.title}
                                                    sourceTab="analysis"
                                                />
                                            </div>
                                        )}
                                    </article>
                                );
                            })}
                        </section>
                    )}
                </>
            )}
        </div>
    );
}
