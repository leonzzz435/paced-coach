/* ─────────────────────────────────────────────
   Shared UI Block types — mirrors Python schemas
   (services/ai/langgraph/schemas/ui_blocks.py)
   ───────────────────────────────────────────── */

// ── Analysis ────────────────────────────────────

export type UiKpiStatus = "good" | "warning" | "danger" | "neutral";

export type UiKpi = {
    kpi_id: string;
    label: string;
    value: string;
    trend?: string | null;
    status: UiKpiStatus;
    domain?: string | null;
    trend_points?: number[] | null;
};

export type UiAnalysisSectionTone = "neutral" | "good" | "warning" | "danger";

export type UiHtmlBlockVariant =
    | "workout"
    | "support"
    | "fueling"
    | "checklist"
    | "callout"
    | "notes"
    | "meta"
    | "generic";

export type UiHtmlBlock = {
    type: "html";
    key: string;
    variant: UiHtmlBlockVariant;
    title?: string | null;
    tone?: UiAnalysisSectionTone | null;
    content_html: string;
};

export type UiDisclosureNode = {
    node_id: string;
    title: string;
    summary?: string | null;
    tone?: UiAnalysisSectionTone;
    default_open?: boolean | null;
    disclosure_mode?: "auto" | "collapsible" | "inline";
    blocks: UiHtmlBlock[];
    children: UiDisclosureNode[];
};

export type UiAnalysisSection = {
    section_id: string;
    title: string;
    tone: UiAnalysisSectionTone;
    summary?: string | null;
    nodes?: UiDisclosureNode[];
    blocks: UiHtmlBlock[];
};

export type UiAnalysis = {
    type: "analysis";
    analysis_id: string;
    schema_version: number;
    version: number;
    athlete_name: string;
    created_at?: string | null;
    // Surface layer
    headline_brief?: string | null;
    coach_action?: string | null;
    dashboard_kpis?: UiKpi[];
    // Context layer (drill-down + agent context)
    kpis: UiKpi[];
    sections: UiAnalysisSection[];
};

// ── Season Plan ─────────────────────────────────

export type UiSeasonPhase = {
    phase_id: string;
    title: string;
    start_date: string;
    end_date: string;
    summary?: string | null;
    nodes?: UiDisclosureNode[];
    blocks: UiHtmlBlock[];
};

export type UiSeasonPlan = {
    type: "season_plan";
    plan_id: string;
    schema_version: number;
    version: number;
    athlete_name: string;
    start_date: string;
    end_date: string;
    season_summary_line?: string | null;
    global_nodes?: UiDisclosureNode[];
    global_blocks: UiHtmlBlock[];
    phases: UiSeasonPhase[];
};

// ── Weekly Plan ─────────────────────────────────

export type UiDayPlan = {
    day_id: string;
    date: string;
    day_label?: string | null;
    focus_type?: string | null;
    focus_color?: string | null;
    workout_title?: string | null;
    primary_distance_km?: number | null;
    icon?: string | null;
    nodes?: UiDisclosureNode[];
    blocks: UiHtmlBlock[];
    estimated_duration_min?: number | null;
    estimated_intensity?: "rest" | "low" | "moderate" | "high" | "very_high" | null;
    readiness_note?: string | null;
    is_completed?: boolean;
};

export type UiWeekPlan = {
    week_id: string;
    week_label?: string | null;
    week_theme?: string | null;
    start_date: string;
    end_date: string;
    notes_nodes?: UiDisclosureNode[];
    notes_blocks: UiHtmlBlock[];
    days: UiDayPlan[];
};

export type UiWeeklyPlan = {
    type: "weekly_plan";
    plan_id: string;
    schema_version: number;
    version: number;
    athlete_name: string;
    created_at?: string | null;
    // Surface layer
    plan_brief?: string | null;
    // Context layer (drill-down + agent context)
    global_nodes?: UiDisclosureNode[];
    global_blocks: UiHtmlBlock[];
    weeks: UiWeekPlan[];
};
