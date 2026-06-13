from __future__ import annotations

import calendar
import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from core.version_manifest import get_version_manifest

CURRENT_UI_SCHEMA_VERSION = get_version_manifest().components.ui_schema.current_schema_version


def _clamp_date(v: object) -> object:
    if isinstance(v, datetime.date):
        return v
    if not isinstance(v, str):
        return v
    try:
        return datetime.date.fromisoformat(v)
    except ValueError:
        # LLM hallucinated an impossible date (e.g. 2026-02-29).
        # Clamp day to last valid day of the month.
        parts = v.split("-")
        if len(parts) == 3:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            max_day = calendar.monthrange(year, month)[1]
            return datetime.date(year, month, min(day, max_day))
        raise


SafeDate = Annotated[datetime.date, BeforeValidator(_clamp_date)]


def _normalize_ui_signal_tone(v: object) -> object:
    if not isinstance(v, str):
        return v

    tone = v.strip().lower().replace("_", "-")
    return {
        "accent": "neutral",
        "info": "neutral",
        "informational": "neutral",
        "warn": "warning",
        "watch": "warning",
        "bad": "danger",
        "error": "danger",
        "critical": "danger",
        "success": "good",
        "positive": "good",
    }.get(tone, tone)


UiSignalTone = Annotated[
    Literal["good", "warning", "danger", "neutral"],
    BeforeValidator(_normalize_ui_signal_tone),
]
OptionalUiSignalTone = Annotated[
    Literal["good", "warning", "danger", "neutral"] | None,
    BeforeValidator(_normalize_ui_signal_tone),
]


class UiHtmlBlock(BaseModel):
    type: Literal["html"] = "html"
    key: str = Field(
        description=(
            "Stable unique identifier for this block within its container (day/week/phase/section). "
            "Used for React keys and checklist persistence."
        )
    )
    variant: Literal["workout", "support", "fueling", "checklist", "callout", "notes", "meta", "generic"] = Field(
        description=(
            "Visual/semantic category for rendering (e.g. workout, checklist, callout). "
            "Use checklist for actionable step lists. "
            "Use meta only for week-level notes, never inside a day."
        )
    )
    title: str | None = Field(
        default=None,
        description="Optional short heading shown above the HTML fragment.",
    )
    tone: OptionalUiSignalTone = Field(
        default=None,
        description="Optional callout tone; only allowed when variant=callout.",
    )
    content_html: str = Field(description="Self-contained HTML fragment (no <html>/<head>/<body>/<style> tags).")


class UiDisclosureNode(BaseModel):
    node_id: str = Field(description="Stable identifier for this disclosure node.")
    title: str = Field(description="Display title for the node header.")
    summary: str | None = Field(
        default=None,
        description="Optional one-line summary shown while collapsed.",
    )
    tone: UiSignalTone = Field(
        default="neutral",
        description="Optional health signal used for node accent color.",
    )
    default_open: bool | None = Field(
        default=None,
        description=(
            "Optional initial expansion hint. True = start expanded, False = start collapsed. "
            "Null lets the renderer choose a neutral default."
        ),
    )
    disclosure_mode: Literal["auto", "collapsible", "inline"] = Field(
        default="auto",
        description=(
            "Renderer hint for disclosure chrome. "
            "'collapsible' renders a hide/show container, "
            "'inline' renders content directly with no extra hide toggle, "
            "'auto' defers to renderer defaults."
        ),
    )
    blocks: list[UiHtmlBlock] = Field(
        default_factory=list,
        description="Leaf HTML blocks rendered when this node is expanded.",
    )
    children: list[UiDisclosureNode] = Field(
        default_factory=list,
        description="Nested disclosure nodes for arbitrary depth (N-level drill-down).",
    )


# ── Weekly Plan ─────────────────────────────────────────────


class UiDayPlan(BaseModel):
    day_id: str = Field(description="Stable day identifier (usually ISO date, e.g. '2026-02-16').")
    date: SafeDate = Field(description="Calendar date for the day (ISO).")
    day_label: str | None = Field(
        default=None,
        description="Optional display label (e.g., 'Mon — Easy Run').",
    )
    focus_type: str | None = Field(
        default=None,
        description=(
            "Primary training focus for the day as a lowercase kebab-case string. "
            "Drives the colored left-border on day cards in the UI. "
            "Open-world semantic labels are allowed (e.g. threshold, tempo, endurance, hills, brick, trail). "
            "Leave null only for rest days."
        ),
    )
    workout_title: str | None = Field(
        default=None,
        description="Short punchy title for the main session (e.g., '6x3m VO2max'). Displayed on the calendar card.",
    )
    primary_distance_km: float | None = Field(
        default=None,
        description="Main session distance in km if applicable.",
    )
    icon: str | None = Field(
        default=None,
        description="A single emoji representing the primary sport/activity (e.g., '🏃‍♂️', '🚴', '🏊', '🏋️').",
    )
    focus_color: str | None = Field(
        default=None,
        description=(
            "Optional CSS color selected by the formatter for this day's focus (hex/rgb/hsl). "
            "Used by the renderer for day accents. Set for non-rest days when possible."
        ),
    )
    nodes: list[UiDisclosureNode] = Field(
        default_factory=list,
        description="Nested disclosure nodes for this day (preferred in schema v1).",
    )
    blocks: list[UiHtmlBlock] = Field(default_factory=list)
    estimated_duration_min: int | None = Field(
        default=None,
        description=(
            "Total session duration in minutes including warm-up/cool-down. "
            "Drives bar height in the dashboard week-rhythm strip. Null for rest days."
        ),
    )
    estimated_intensity: Literal["rest", "low", "moderate", "high", "very_high"] | None = Field(
        default=None,
        description=(
            "Overall session intensity. Drives bar color in the week-rhythm strip: "
            "rest=gray, low=green, moderate=amber, high=orange, very_high=red. "
            "Set for ALL days including rest days."
        ),
    )
    readiness_note: str | None = Field(
        default=None,
        description=(
            "1-2 sentence contextual readiness verdict for this day, shown on the hero card "
            "when this day is 'today'. Write in direct coaching voice. "
            "Examples: 'Go as written — recovery strong', "
            "'Consider dropping strides — HRV dipped overnight'."
        ),
    )
    is_completed: bool = Field(
        default=False,
        description="Whether the user explicitly marked this day's primary training session as completed.",
    )


class UiWeekPlan(BaseModel):
    week_id: str = Field(description="Stable week identifier (e.g., 'wk-2026-02-16').")
    week_label: str | None = Field(
        default=None,
        description="Optional display label for the week.",
    )
    week_theme: str | None = Field(
        default=None,
        description=(
            "Short theme label for the week (e.g., 'Build Week 2 of 3', 'Recovery', 'Race Week'). "
            "Displayed as the primary week heading. Captures the coaching intent in 3-6 words."
        ),
    )
    start_date: SafeDate = Field(description="Week start date (ISO).")
    end_date: SafeDate = Field(description="Week end date (ISO).")
    notes_blocks: list[UiHtmlBlock] = Field(
        default_factory=list,
        description=(
            "Week-level notes and meta (focus, constraints, travel notes). May include variant=meta or variant=callout."
        ),
    )
    notes_nodes: list[UiDisclosureNode] = Field(
        default_factory=list,
        description="Nested week-level disclosure nodes (preferred in schema v1).",
    )
    days: list[UiDayPlan] = Field(default_factory=list, description="Day-by-day plan entries.")


class LlmWeeklyPlan(BaseModel):
    """LLM-facing schema: only stochastic fields the LLM should populate."""

    # ── Surface layer (what the athlete reads) ──────────────────
    plan_brief: str | None = Field(
        default=None,
        description=(
            "2-3 sentence coaching message for the training block — like a Monday morning "
            "text from your coach. Focus on intent, feel, and the one thing that matters most. "
            "Direct second-person voice. Must stand alone."
        ),
    )

    # ── Context layer (for AI agents + drill-down) ──────────────
    global_blocks: list[UiHtmlBlock] = Field(
        default_factory=list,
        description=(
            "Plan-global coach notes (zones, readiness rules, guardrails). "
            "Agent context — not shown by default. Keep lean: 1-2 blocks."
        ),
    )
    global_nodes: list[UiDisclosureNode] = Field(
        default_factory=list,
        description="Plan-global disclosure nodes. Agent context — available on drill-down.",
    )
    weeks: list[UiWeekPlan] = Field(
        default_factory=list,
        description="Ordered list of weeks.",
    )


class UiWeeklyPlan(LlmWeeklyPlan):
    """Full UI schema: deterministic metadata added by node code."""

    type: Literal["weekly_plan"] = "weekly_plan"
    plan_id: str = ""
    schema_version: int = CURRENT_UI_SCHEMA_VERSION
    version: int = 1
    athlete_name: str = ""
    created_at: str | None = None


# ── Season Plan ─────────────────────────────────────────────


class UiSeasonPhase(BaseModel):
    phase_id: str = Field(description="Stable identifier for the phase (e.g., 'phase-base-1').")
    title: str = Field(description="Display title for the phase.")
    start_date: SafeDate = Field(description="Phase start date (ISO).")
    end_date: SafeDate = Field(description="Phase end date (ISO).")
    summary: str | None = Field(
        default=None,
        description="Optional one-sentence summary for collapsed/overview display.",
    )
    nodes: list[UiDisclosureNode] = Field(
        default_factory=list,
        description="Nested disclosure nodes for this phase (preferred in schema v1).",
    )
    blocks: list[UiHtmlBlock] = Field(
        default_factory=list,
        description="Ordered blocks describing goals, structure, and guardrails for this phase.",
    )


class LlmSeasonPlan(BaseModel):
    """LLM-facing schema: only stochastic fields the LLM should populate."""

    # ── Surface layer (what the athlete reads) ──────────────────
    season_summary_line: str | None = Field(
        default=None,
        description=(
            "One-liner for the Season Arc banner (under 80 chars). "
            "Example: 'Week 3 of 12 · Aerobic Base · Trail Strength On-Ramp'."
        ),
    )

    # ── Context layer (for AI agents + drill-down) ──────────────
    global_blocks: list[UiHtmlBlock] = Field(
        default_factory=list,
        description=(
            "Season-global coach notes (principles, guardrails, zones). "
            "Agent context — not shown by default. Keep lean: 1-2 blocks."
        ),
    )
    global_nodes: list[UiDisclosureNode] = Field(
        default_factory=list,
        description="Season-global disclosure nodes. Agent context — available on drill-down.",
    )
    start_date: SafeDate = Field(description="Plan start date (ISO).")
    end_date: SafeDate = Field(description="Plan end date (ISO).")
    phases: list[UiSeasonPhase] = Field(
        ..., min_length=1, description="One or more season phases in chronological order."
    )


class UiSeasonPlan(LlmSeasonPlan):
    """Full UI schema: deterministic metadata added by node code."""

    type: Literal["season_plan"] = "season_plan"
    plan_id: str = ""
    schema_version: int = CURRENT_UI_SCHEMA_VERSION
    version: int = 1
    athlete_name: str = ""
    created_at: str | None = None


# ── Analysis ────────────────────────────────────────────────


class UiKpi(BaseModel):
    kpi_id: str = Field(description="Stable identifier for the KPI (e.g., 'sleep-score').")
    label: str = Field(description="Human-readable KPI name.")
    value: str = Field(description="Formatted KPI value for display (include units).")
    trend: str | None = Field(
        default=None,
        description="Optional short trend/explanation string.",
    )
    status: UiSignalTone = Field(
        default="neutral",
        description="Status indicator used for UI coloring and emphasis.",
    )
    domain: str | None = Field(
        default=None,
        description=(
            "Optional grouping domain for UI display. Prefer canonical values: "
            "load, recovery, performance, body, sleep."
        ),
    )
    trend_points: list[float] | None = Field(
        default=None,
        description=(
            "7-14 numeric data points for a sparkline visualization (oldest first). "
            "Renderer draws a tiny SVG line chart beside the KPI card. "
            "Populate when historical trend data is available in the source."
        ),
    )


class UiAnalysisSection(BaseModel):
    section_id: str = Field(description="Stable identifier for the section.")
    title: str = Field(description="Display title for the section.")
    tone: UiSignalTone = Field(
        default="neutral",
        description=(
            "Overall health signal for the section — drives the section header color in the UI. "
            "good = on track, warning = monitor, danger = action needed, neutral = informational."
        ),
    )
    summary: str | None = Field(
        default=None,
        description="Optional one-sentence summary for collapsed/overview display.",
    )
    nodes: list[UiDisclosureNode] = Field(
        default_factory=list,
        description="Nested disclosure nodes for this section (preferred in schema v1).",
    )
    blocks: list[UiHtmlBlock] = Field(
        default_factory=list,
        description="Ordered blocks in this section; prefer multiple smaller blocks over one blob.",
    )


class LlmAnalysis(BaseModel):
    """LLM-facing schema: only stochastic fields the LLM should populate."""

    # ── Surface layer (what the athlete reads) ──────────────────
    headline_brief: str | None = Field(
        default=None,
        description=(
            "2-3 sentence coaching TL;DR — the first thing the athlete reads. "
            "Answer: what matters most right now? Direct second-person coaching voice."
        ),
    )
    coach_action: str | None = Field(
        default=None,
        description=(
            "Single, direct coaching directive — the #1 thing to do right now. "
            "Example: 'Prioritize sleep through Thursday — your HRV trend is declining.' "
            "Commanding voice. Must stand alone without any other context."
        ),
    )
    dashboard_kpis: list[UiKpi] = Field(
        default_factory=list,
        description=(
            "Curated above-the-fold KPI strip (3-6 metrics). Order by coaching salience. Only the strongest signals."
        ),
    )

    # ── Context layer (for AI agents + drill-down) ──────────────
    kpis: list[UiKpi] = Field(default_factory=list, description="Full KPI inventory for agent context and drill-down.")
    sections: list[UiAnalysisSection] = Field(
        default_factory=list,
        description="Detail sections for agent context. Not shown by default — available on drill-down.",
    )


class UiAnalysis(LlmAnalysis):
    """Full UI schema: deterministic metadata added by node code."""

    type: Literal["analysis"] = "analysis"
    analysis_id: str = ""
    schema_version: int = CURRENT_UI_SCHEMA_VERSION
    version: int = 1
    athlete_name: str = ""
    created_at: str | None = None


UiWeeklyPlan.model_rebuild()
UiSeasonPlan.model_rebuild()
UiAnalysis.model_rebuild()
UiHtmlBlock.model_rebuild()
UiDisclosureNode.model_rebuild()
