from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from services.ai.head_coach.schemas import CoachAssumption, CoachSafetyConcern, EvidenceProvenance

_RAW_HTML_RE = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")


def _reject_raw_html(value: str) -> str:
    normalized = value.strip()
    if _RAW_HTML_RE.search(normalized):
        raise ValueError("Model-authored Markdown must not contain raw HTML")
    return normalized


MarkdownText = Annotated[str, Field(min_length=1, max_length=20_000), AfterValidator(_reject_raw_html)]
ShortMarkdownText = Annotated[str, Field(min_length=1, max_length=4_000), AfterValidator(_reject_raw_html)]
BlockEmphasis = Literal["primary", "secondary", "subtle"]
DisclosureIntent = Literal["inline", "collapsible", "summary_first"]
SignalTone = Literal["neutral", "info", "success", "warning", "danger"]
TrainingIntensity = Literal["rest", "low", "moderate", "high", "very_high"]


class ArtifactModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NarrativeBlock(ArtifactModel):
    type: Literal["narrative"] = "narrative"
    block_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    emphasis: BlockEmphasis = "secondary"
    markdown: MarkdownText


class CalloutBlock(ArtifactModel):
    type: Literal["callout"] = "callout"
    block_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    emphasis: BlockEmphasis = "secondary"
    tone: SignalTone
    markdown: ShortMarkdownText


class ChecklistItem(ArtifactModel):
    item_id: str = Field(min_length=1, max_length=200)
    label: str = Field(min_length=1, max_length=500)
    detail_markdown: ShortMarkdownText | None = None


class ChecklistBlock(ArtifactModel):
    type: Literal["checklist"] = "checklist"
    block_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    emphasis: BlockEmphasis = "secondary"
    items: list[ChecklistItem] = Field(min_length=1, max_length=30)

    @field_validator("items")
    @classmethod
    def validate_unique_item_ids(cls, value: list[ChecklistItem]) -> list[ChecklistItem]:
        item_ids = [item.item_id for item in value]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Checklist item IDs must be unique")
        return value


class DataTableColumn(ArtifactModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    label: str = Field(min_length=1, max_length=100)
    align: Literal["left", "center", "right"] = "left"


class DataTableBlock(ArtifactModel):
    type: Literal["data_table"] = "data_table"
    block_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    emphasis: BlockEmphasis = "secondary"
    columns: list[DataTableColumn] = Field(min_length=1, max_length=10)
    rows: list[dict[str, str]] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_table_shape(self) -> DataTableBlock:
        column_keys = [column.key for column in self.columns]
        if len(column_keys) != len(set(column_keys)):
            raise ValueError("Data-table column keys must be unique")
        expected_keys = set(column_keys)
        if any(set(row) != expected_keys for row in self.rows):
            raise ValueError("Every data-table row must match the declared columns")
        return self


class WorkoutBlock(ArtifactModel):
    type: Literal["workout"] = "workout"
    block_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    emphasis: BlockEmphasis = "primary"
    objective_markdown: ShortMarkdownText


class IntervalRow(ArtifactModel):
    label: str = Field(min_length=1, max_length=120)
    duration: str = Field(min_length=1, max_length=120)
    prescription: str = Field(min_length=1, max_length=500)
    recovery: str | None = Field(default=None, max_length=300)


class IntervalTableBlock(ArtifactModel):
    type: Literal["interval_table"] = "interval_table"
    block_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    emphasis: BlockEmphasis = "primary"
    intervals: list[IntervalRow] = Field(min_length=1, max_length=30)


class FuelingBlock(ArtifactModel):
    type: Literal["fueling"] = "fueling"
    block_id: str = Field(min_length=1, max_length=200)
    session_id: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    emphasis: BlockEmphasis = "secondary"
    before_markdown: ShortMarkdownText | None = None
    during_markdown: ShortMarkdownText | None = None
    after_markdown: ShortMarkdownText | None = None

    @model_validator(mode="after")
    def validate_guidance_present(self) -> FuelingBlock:
        if self.before_markdown is None and self.during_markdown is None and self.after_markdown is None:
            raise ValueError("Fueling blocks require before, during, or after guidance")
        return self


class RecoveryBlock(ArtifactModel):
    type: Literal["recovery"] = "recovery"
    block_id: str = Field(min_length=1, max_length=200)
    session_id: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    emphasis: BlockEmphasis = "secondary"
    markdown: ShortMarkdownText


class NotesBlock(ArtifactModel):
    type: Literal["notes"] = "notes"
    block_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    emphasis: BlockEmphasis = "subtle"
    markdown: MarkdownText


class TimelineMilestone(ArtifactModel):
    phase_id: str = Field(min_length=1, max_length=200)
    label: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class PhaseTimelineBlock(ArtifactModel):
    type: Literal["phase_timeline"] = "phase_timeline"
    block_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    emphasis: BlockEmphasis = "primary"
    milestones: list[TimelineMilestone] = Field(min_length=1, max_length=20)


class DisclosureBlock(ArtifactModel):
    type: Literal["disclosure"] = "disclosure"
    block_id: str = Field(min_length=1, max_length=200)
    label: str = Field(min_length=1, max_length=200)
    emphasis: BlockEmphasis = "subtle"
    summary_markdown: MarkdownText
    default_open: bool = False


SemanticBlock = Annotated[
    NarrativeBlock
    | CalloutBlock
    | ChecklistBlock
    | DataTableBlock
    | WorkoutBlock
    | IntervalTableBlock
    | FuelingBlock
    | RecoveryBlock
    | NotesBlock
    | PhaseTimelineBlock
    | DisclosureBlock,
    Field(discriminator="type"),
]


class ArtifactSection(ArtifactModel):
    section_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    summary_markdown: ShortMarkdownText | None = None
    emphasis: BlockEmphasis = "secondary"
    disclosure_intent: DisclosureIntent = "summary_first"
    blocks: list[SemanticBlock] = Field(default_factory=list, max_length=30)


class DecisionLedgerEntry(ArtifactModel):
    decision_id: str = Field(min_length=1, max_length=200)
    decided_at: datetime
    title: str = Field(min_length=1, max_length=300)
    rationale_markdown: MarkdownText
    changes_markdown: MarkdownText
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class SeasonPhase(ArtifactModel):
    phase_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    objective_markdown: MarkdownText
    success_signals: list[str] = Field(default_factory=list, max_length=20)
    blocks: list[SemanticBlock] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_date_order(self) -> SeasonPhase:
        if self.end_date < self.start_date:
            raise ValueError("Season phase end date must not precede its start date")
        return self


class TrainingSession(ArtifactModel):
    session_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    sport: str = Field(min_length=1, max_length=100)
    objective_markdown: MarkdownText
    prescription_markdown: MarkdownText
    duration_min: int = Field(ge=1, le=1_440)
    intensity: TrainingIntensity
    distance_km: float | None = Field(default=None, ge=0.0)
    blocks: list[SemanticBlock] = Field(default_factory=list, max_length=30)


class ExecutionDay(ArtifactModel):
    day_id: str = Field(min_length=1, max_length=200)
    date: date
    label: str = Field(min_length=1, max_length=200)
    focus_type: str = Field(min_length=1, max_length=100)
    intensity: TrainingIntensity
    total_duration_min: int = Field(ge=0, le=1_440)
    sessions: list[TrainingSession] = Field(default_factory=list, max_length=4)
    blocks: list[SemanticBlock] = Field(default_factory=list, max_length=30)
    is_completed: bool = False

    @model_validator(mode="after")
    def validate_total_duration(self) -> ExecutionDay:
        if self.total_duration_min != sum(session.duration_min for session in self.sessions):
            raise ValueError("Execution-day total duration must equal the sum of its session durations")
        return self


class ExecutionWeek(ArtifactModel):
    week_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    intent_markdown: MarkdownText
    days: list[ExecutionDay] = Field(min_length=7, max_length=7)
    blocks: list[SemanticBlock] = Field(default_factory=list, max_length=30)


class SeasonStrategyArtifactV3(ArtifactModel):
    type: Literal["season_plan"] = "season_plan"
    schema_version: Literal[3] = 3
    plan_id: str = Field(min_length=1, max_length=200)
    version: int = Field(ge=1)
    athlete_name: str = Field(min_length=1, max_length=200)
    created_at: datetime
    title: str = Field(min_length=1, max_length=300)
    summary_markdown: MarkdownText
    start_date: date
    end_date: date
    goal_event_ids: list[str] = Field(default_factory=list, max_length=100)
    phases: list[SeasonPhase] = Field(min_length=1, max_length=20)
    sections: list[ArtifactSection] = Field(default_factory=list, max_length=30)
    assumptions: list[CoachAssumption] = Field(default_factory=list, max_length=50)
    evidence: list[EvidenceProvenance] = Field(default_factory=list, max_length=100)
    safety_concerns: list[CoachSafetyConcern] = Field(default_factory=list, max_length=50)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=50)
    decision_ledger_entry: DecisionLedgerEntry

    @model_validator(mode="after")
    def validate_structure(self) -> SeasonStrategyArtifactV3:
        if self.end_date < self.start_date:
            raise ValueError("Season end date must not precede its start date")
        phase_ids = [phase.phase_id for phase in self.phases]
        if len(phase_ids) != len(set(phase_ids)):
            raise ValueError("Season phase IDs must be unique")
        if any(phase.start_date < self.start_date or phase.end_date > self.end_date for phase in self.phases):
            raise ValueError("Season phases must remain within the season date range")
        _validate_unique_artifact_ids(self.sections, self.phases)
        return self


class ExecutionPlanArtifactV3(ArtifactModel):
    type: Literal["weekly_plan"] = "weekly_plan"
    schema_version: Literal[3] = 3
    plan_id: str = Field(min_length=1, max_length=200)
    season_plan_id: str = Field(min_length=1, max_length=200)
    version: int = Field(ge=1)
    athlete_name: str = Field(min_length=1, max_length=200)
    created_at: datetime
    title: str = Field(min_length=1, max_length=300)
    summary_markdown: MarkdownText
    start_date: date
    end_date: date
    weeks: list[ExecutionWeek] = Field(min_length=4, max_length=4)
    sections: list[ArtifactSection] = Field(default_factory=list, max_length=30)
    assumptions: list[CoachAssumption] = Field(default_factory=list, max_length=50)
    evidence: list[EvidenceProvenance] = Field(default_factory=list, max_length=100)
    safety_concerns: list[CoachSafetyConcern] = Field(default_factory=list, max_length=50)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=50)
    decision_ledger_entry: DecisionLedgerEntry

    @model_validator(mode="after")
    def validate_28_day_calendar(self) -> ExecutionPlanArtifactV3:
        days = [day for week in self.weeks for day in week.days]
        day_ids = [day.day_id for day in days]
        if len(day_ids) != len(set(day_ids)):
            raise ValueError("Execution-plan day IDs must be unique")
        session_ids = [session.session_id for day in days for session in day.sessions]
        if len(session_ids) != len(set(session_ids)):
            raise ValueError("Execution-plan session IDs must be unique")
        expected_dates = [self.start_date + timedelta(days=offset) for offset in range(28)]
        if self.end_date != self.start_date + timedelta(days=27) or [day.date for day in days] != expected_dates:
            raise ValueError("Execution plan must contain exactly 28 consecutive days")
        for week_index, week in enumerate(self.weeks):
            expected_start = self.start_date + timedelta(days=week_index * 7)
            if week.start_date != expected_start or week.end_date != expected_start + timedelta(days=6):
                raise ValueError("Execution week boundaries must match their seven calendar days")
            if [day.date for day in week.days] != [expected_start + timedelta(days=offset) for offset in range(7)]:
                raise ValueError("Execution week days must be chronological and match the week range")
        _validate_unique_artifact_ids(self.sections, self.weeks)
        return self


HeadCoachArtifactV3 = SeasonStrategyArtifactV3 | ExecutionPlanArtifactV3


def _validate_unique_artifact_ids(
    sections: list[ArtifactSection],
    containers: list[SeasonPhase] | list[ExecutionWeek],
):
    section_ids = [section.section_id for section in sections]
    if len(section_ids) != len(set(section_ids)):
        raise ValueError("Artifact section IDs must be unique")
    blocks = [block for section in sections for block in section.blocks]
    for container in containers:
        blocks.extend(container.blocks)
        if isinstance(container, ExecutionWeek):
            for day in container.days:
                blocks.extend(day.blocks)
                for session in day.sessions:
                    blocks.extend(session.blocks)
    block_ids = [block.block_id for block in blocks]
    if len(block_ids) != len(set(block_ids)):
        raise ValueError("Semantic block IDs must be unique across an artifact")
