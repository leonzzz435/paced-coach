export type PlanViewMode = "full" | "landing";
export type WeeklyPlanTheme = "light" | "dark";

export type ArtifactEmphasis = "primary" | "secondary" | "subtle";
export type DisclosureIntent = "inline" | "collapsible" | "summary_first";
export type SignalTone = "neutral" | "info" | "success" | "warning" | "danger";
export type TrainingIntensity = "rest" | "low" | "moderate" | "high" | "very_high";

type SemanticBlockBase = {
    block_id: string;
    title?: string | null;
    emphasis: ArtifactEmphasis;
};

export type NarrativeBlockV3 = SemanticBlockBase & { type: "narrative"; markdown: string };
export type CalloutBlockV3 = SemanticBlockBase & { type: "callout"; tone: SignalTone; markdown: string };
export type ChecklistBlockV3 = SemanticBlockBase & {
    type: "checklist";
    items: Array<{ item_id: string; label: string; detail_markdown?: string | null }>;
};
export type DataTableBlockV3 = SemanticBlockBase & {
    type: "data_table";
    columns: Array<{ key: string; label: string; align: "left" | "center" | "right" }>;
    rows: Array<Record<string, string>>;
};
export type WorkoutBlockV3 = SemanticBlockBase & {
    type: "workout";
    session_id: string;
    title: string;
    objective_markdown: string;
};
export type IntervalTableBlockV3 = SemanticBlockBase & {
    type: "interval_table";
    session_id: string;
    intervals: Array<{ label: string; duration: string; prescription: string; recovery?: string | null }>;
};
export type FuelingBlockV3 = SemanticBlockBase & {
    type: "fueling";
    session_id?: string | null;
    before_markdown?: string | null;
    during_markdown?: string | null;
    after_markdown?: string | null;
};
export type RecoveryBlockV3 = SemanticBlockBase & {
    type: "recovery";
    session_id?: string | null;
    markdown: string;
};
export type NotesBlockV3 = SemanticBlockBase & { type: "notes"; markdown: string };
export type PhaseTimelineBlockV3 = SemanticBlockBase & {
    type: "phase_timeline";
    milestones: Array<{ phase_id: string; label: string; note?: string | null }>;
};
export type DisclosureBlockV3 = Omit<SemanticBlockBase, "title"> & {
    type: "disclosure";
    label: string;
    summary_markdown: string;
    default_open: boolean;
};

export type SemanticBlockV3 =
    | NarrativeBlockV3
    | CalloutBlockV3
    | ChecklistBlockV3
    | DataTableBlockV3
    | WorkoutBlockV3
    | IntervalTableBlockV3
    | FuelingBlockV3
    | RecoveryBlockV3
    | NotesBlockV3
    | PhaseTimelineBlockV3
    | DisclosureBlockV3;

export type ArtifactSectionV3 = {
    section_id: string;
    title: string;
    summary_markdown?: string | null;
    emphasis: ArtifactEmphasis;
    disclosure_intent: DisclosureIntent;
    blocks: SemanticBlockV3[];
};

export type ArtifactAssumptionV3 = {
    statement: string;
    consequence: string;
    needs_confirmation: boolean;
};

export type ArtifactEvidenceV3 = {
    source_kind: string;
    authority: string;
    source_id: string;
    observed_at?: string | null;
    limitations: string[];
};

export type ArtifactSafetyConcernV3 = {
    concern: string;
    athlete_message_required: boolean;
};

export type DecisionLedgerEntryV3 = {
    decision_id: string;
    decided_at: string;
    title: string;
    rationale_markdown: string;
    changes_markdown: string;
    evidence_ids: string[];
};

export type PresentationCompositionV3 = {
    schema_version: 3;
    artifact_id: string;
    semantic_hash: string;
    section_order: string[];
    containers: Array<{
        container_id: string;
        block_order: string[];
        disclosure_intent?: DisclosureIntent | null;
    }>;
    featured_block_ids: string[];
    collapsed_section_ids: string[];
};

type ArtifactBaseV3 = {
    schema_version: 3;
    plan_id: string;
    version: number;
    athlete_name: string;
    created_at: string;
    title: string;
    summary_markdown: string;
    start_date: string;
    end_date: string;
    sections: ArtifactSectionV3[];
    assumptions: ArtifactAssumptionV3[];
    evidence: ArtifactEvidenceV3[];
    safety_concerns: ArtifactSafetyConcernV3[];
    unresolved_questions: string[];
    decision_ledger_entry: DecisionLedgerEntryV3;
    presentation?: PresentationCompositionV3;
};

export type SeasonPlanV3 = ArtifactBaseV3 & {
    type: "season_plan";
    goal_event_ids: string[];
    phases: Array<{
        phase_id: string;
        title: string;
        start_date: string;
        end_date: string;
        objective_markdown: string;
        success_signals: string[];
        blocks: SemanticBlockV3[];
    }>;
};

export type WeeklyPlanV3 = ArtifactBaseV3 & {
    type: "weekly_plan";
    season_plan_id: string;
    weeks: Array<{
        week_id: string;
        title: string;
        start_date: string;
        end_date: string;
        intent_markdown: string;
        blocks: SemanticBlockV3[];
        days: Array<{
            day_id: string;
            date: string;
            label: string;
            focus_type: string;
            intensity: TrainingIntensity;
            total_duration_min: number;
            is_completed: boolean;
            blocks: SemanticBlockV3[];
            sessions: Array<{
                session_id: string;
                title: string;
                sport: string;
                objective_markdown: string;
                prescription_markdown: string;
                duration_min: number;
                intensity: TrainingIntensity;
                distance_km?: number | null;
                blocks: SemanticBlockV3[];
            }>;
        }>;
    }>;
};
