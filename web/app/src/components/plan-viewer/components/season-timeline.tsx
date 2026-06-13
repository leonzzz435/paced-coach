"use client";

import { useEffect, useRef } from "react";

import { UiSeasonPlan } from "@/lib/types/ui-blocks";
import "./season-timeline.css";

type Props = {
    phases: UiSeasonPlan["phases"];
    startDate: string;
    endDate: string;
    currentPhaseId?: string | null;
    selectedPhaseId?: string | null;
    onPhaseClick?: (phaseId: string) => void;
};

function getPhaseColorClass(index: number) {
    const i = (index % 6) + 1;
    return `seg--p${i}`;
}

function parseDateMs(value: string): number | null {
    const ms = new Date(value).getTime();
    return Number.isNaN(ms) ? null : ms;
}

function formatDate(value: string): string {
    const ms = parseDateMs(value);
    if (ms === null) return value;
    return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(ms);
}

function formatDateRange(startDate: string, endDate: string): string {
    return `${formatDate(startDate)} - ${formatDate(endDate)}`;
}

function getDurationLabel(startDate: string, endDate: string): string {
    const start = parseDateMs(startDate);
    const end = parseDateMs(endDate);
    if (start === null || end === null) return "";

    const dayCount = Math.max(1, Math.round((end - start) / 86_400_000) + 1);
    if (dayCount < 14) return `${dayCount}d`;

    const weeks = Math.round((dayCount / 7) * 10) / 10;
    return `${weeks}w`;
}

export function SeasonTimeline({
    phases,
    startDate,
    endDate,
    currentPhaseId,
    selectedPhaseId,
    onPhaseClick,
}: Props) {
    const cardRefs = useRef<Record<string, HTMLButtonElement | null>>({});
    const hasPhases = phases.length > 0;
    const start = parseDateMs(startDate) ?? 0;
    const end = parseDateMs(endDate) ?? start;
    const totalDuration = Math.max(1, end - start);
    const focusPhaseId = hasPhases ? selectedPhaseId ?? currentPhaseId ?? phases[0]?.phase_id ?? null : null;
    const focusPhase = hasPhases ? phases.find((phase) => phase.phase_id === focusPhaseId) ?? phases[0] : null;

    useEffect(() => {
        if (!focusPhaseId) return;
        const node = cardRefs.current[focusPhaseId];
        if (!node) return;

        node.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
            inline: "center",
        });
    }, [focusPhaseId]);

    if (!focusPhase) return null;

    return (
        <div className="timeline">
            <div className="timeline__header">
                <div>
                    <div className="timeline__eyebrow">Season Roadmap</div>
                    <div className="timeline__headline">
                        {phases.length} phases
                    </div>
                </div>
                <div className="timeline__range">
                    {formatDateRange(startDate, endDate)}
                </div>
            </div>

            <div className="timeline__overview">
                <div className="timeline__track" aria-hidden="true">
                    {phases.map((phase, idx) => {
                        const pStart = parseDateMs(phase.start_date) ?? start;
                        const pEnd = parseDateMs(phase.end_date) ?? pStart;
                        const pDuration = Math.max(0, pEnd - pStart);
                        const isFocused = phase.phase_id === focusPhaseId;

                        return (
                            <div
                                key={phase.phase_id}
                                className={`timeline__track-segment ${getPhaseColorClass(idx)} ${isFocused ? "timeline__track-segment--selected" : ""}`}
                                style={{ flex: Math.max(0.6, (pDuration / totalDuration) * 100) }}
                                title={`${phase.title} (${phase.start_date} - ${phase.end_date})`}
                            />
                        );
                    })}
                </div>

                <div className="timeline__focus">
                    <div className="timeline__focus-copy">
                        <span className="timeline__focus-label">
                            {focusPhase.phase_id === currentPhaseId ? "Current phase" : "Selected phase"}
                        </span>
                        <div className="timeline__focus-title">{focusPhase.title}</div>
                    </div>
                    <div className="timeline__focus-meta">
                        <span>{formatDateRange(focusPhase.start_date, focusPhase.end_date)}</span>
                        <span>{getDurationLabel(focusPhase.start_date, focusPhase.end_date)}</span>
                    </div>
                </div>
            </div>

            <div className="timeline__cards" role="list" aria-label="Season phases">
                {phases.map((phase, idx) => {
                    const isCurrent = phase.phase_id === currentPhaseId;
                    const isSelected = phase.phase_id === focusPhaseId;

                    return (
                        <button
                            key={phase.phase_id}
                            ref={(node) => {
                                cardRefs.current[phase.phase_id] = node;
                            }}
                            className={`timeline__card ${getPhaseColorClass(idx)} ${isSelected ? "timeline__card--selected" : ""} ${isCurrent ? "timeline__card--current" : ""}`}
                            title={`${phase.title} (${phase.start_date} - ${phase.end_date})`}
                            type="button"
                            onClick={() => onPhaseClick?.(phase.phase_id)}
                        >
                            <div className="timeline__card-top">
                                <span className="timeline__phase-pill">P{idx + 1}</span>
                                {isCurrent ? <span className="timeline__phase-badge">Current</span> : null}
                            </div>
                            <div className="timeline__card-title">{phase.title}</div>
                            <div className="timeline__card-meta">
                                <span>{formatDateRange(phase.start_date, phase.end_date)}</span>
                                <span>{getDurationLabel(phase.start_date, phase.end_date)}</span>
                            </div>
                            {phase.summary ? (
                                <p className="timeline__card-summary">{phase.summary}</p>
                            ) : (
                                <p className="timeline__card-summary timeline__card-summary--muted">
                                    Tap to open the full phase breakdown.
                                </p>
                            )}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
