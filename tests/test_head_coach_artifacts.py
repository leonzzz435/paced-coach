from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from services.ai.head_coach.artifact_rendering import ArtifactValidationError, validate_artifact_with_repair
from services.ai.head_coach.artifacts import (
    ArtifactSection,
    CalloutBlock,
    ChecklistBlock,
    ChecklistItem,
    DataTableBlock,
    DataTableColumn,
    DecisionLedgerEntry,
    DisclosureBlock,
    ExecutionDay,
    ExecutionPlanArtifactV3,
    ExecutionWeek,
    FuelingBlock,
    IntervalRow,
    IntervalTableBlock,
    NarrativeBlock,
    NotesBlock,
    PhaseTimelineBlock,
    RecoveryBlock,
    SeasonPhase,
    SeasonStrategyArtifactV3,
    TimelineMilestone,
    TrainingSession,
    WorkoutBlock,
)
from services.ai.head_coach.schemas import CoachAssumption


def _decision() -> DecisionLedgerEntry:
    return DecisionLedgerEntry(
        decision_id="decision-initial-plan",
        decided_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
        title="Build consistency before specificity",
        rationale_markdown="Four repeatable weeks create the base for later race-specific work.",
        changes_markdown="Created the initial season strategy and 28-day execution block.",
    )


def _execution_weeks() -> list[ExecutionWeek]:
    plan_start = date(2026, 8, 3)
    weeks: list[ExecutionWeek] = []
    for week_index in range(4):
        week_start = plan_start + timedelta(days=week_index * 7)
        days: list[ExecutionDay] = []
        for day_index in range(7):
            day_date = week_start + timedelta(days=day_index)
            is_rest = day_index in {2, 6}
            sessions = []
            if not is_rest:
                sessions = [
                    TrainingSession(
                        session_id=f"session-{day_date.isoformat()}",
                        title="Aerobic run",
                        sport="running",
                        objective_markdown="Accumulate calm aerobic work with relaxed mechanics.",
                        prescription_markdown="Run conversationally and finish feeling able to continue.",
                        duration_min=45,
                        intensity="low",
                    )
                ]
            days.append(
                ExecutionDay(
                    day_id=f"day-{day_date.isoformat()}",
                    date=day_date,
                    label=day_date.strftime("%A"),
                    focus_type="rest" if is_rest else "aerobic",
                    intensity="rest" if is_rest else "low",
                    total_duration_min=0 if is_rest else 45,
                    sessions=sessions,
                )
            )
        weeks.append(
            ExecutionWeek(
                week_id=f"week-{week_index + 1}",
                title=f"Week {week_index + 1}",
                start_date=week_start,
                end_date=week_start + timedelta(days=6),
                intent_markdown="Repeat the essentials and protect consistency.",
                days=days,
            )
        )
    return weeks


def test_schema_v3_artifacts_preserve_rich_semantics_without_html():
    season = SeasonStrategyArtifactV3(
        plan_id="season-synthetic",
        version=1,
        athlete_name="Sample Athlete",
        created_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
        title="A durable path to the autumn race",
        summary_markdown="Build consistency, then convert it into race-specific durability.",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 11, 1),
        phases=[
            SeasonPhase(
                phase_id="phase-foundation",
                title="Foundation",
                start_date=date(2026, 8, 3),
                end_date=date(2026, 8, 30),
                objective_markdown="Make training frequency feel normal and repeatable.",
                success_signals=["Four consistent weeks", "No compensatory hero sessions"],
            )
        ],
        sections=[
            ArtifactSection(
                section_id="strategy",
                title="How this season works",
                emphasis="primary",
                disclosure_intent="inline",
                blocks=[
                    NarrativeBlock(block_id="narrative", markdown="Consistency is the primary performance lever."),
                    CalloutBlock(block_id="callout", tone="warning", markdown="Do not make up missed sessions."),
                    ChecklistBlock(
                        block_id="checklist",
                        items=[ChecklistItem(item_id="check-1", label="Protect two rest windows")],
                    ),
                    DataTableBlock(
                        block_id="table",
                        columns=[DataTableColumn(key="phase", label="Phase"), DataTableColumn(key="intent", label="Intent")],
                        rows=[{"phase": "Foundation", "intent": "Repeatability"}],
                    ),
                    PhaseTimelineBlock(
                        block_id="timeline",
                        milestones=[TimelineMilestone(phase_id="phase-foundation", label="Foundation")],
                    ),
                    DisclosureBlock(
                        block_id="disclosure",
                        label="Why this comes first",
                        summary_markdown="Consistency expands the work you can absorb later.",
                    ),
                    NotesBlock(block_id="notes", markdown="Reassess after the first 28 days."),
                ],
            )
        ],
        assumptions=[
            CoachAssumption(
                statement="Four training days are normally available.",
                consequence="The plan prioritizes repeatable frequency over session density.",
                needs_confirmation=True,
            )
        ],
        decision_ledger_entry=_decision(),
    )
    execution = ExecutionPlanArtifactV3(
        plan_id="execution-synthetic",
        season_plan_id=season.plan_id,
        version=1,
        athlete_name="Sample Athlete",
        created_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
        title="28 days of repeatable work",
        summary_markdown="Keep the easy work easy and arrive fresh enough to repeat the week.",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 30),
        weeks=_execution_weeks(),
        sections=[
            ArtifactSection(
                section_id="execution-rules",
                title="Execution rules",
                blocks=[
                    WorkoutBlock(
                        block_id="workout",
                        session_id="session-2026-08-03",
                        title="Aerobic run",
                        objective_markdown="Relaxed aerobic accumulation.",
                    ),
                    IntervalTableBlock(
                        block_id="intervals",
                        session_id="session-2026-08-03",
                        intervals=[IntervalRow(label="Main", duration="35 min", prescription="Conversational")],
                    ),
                    FuelingBlock(block_id="fueling", during_markdown="Bring water when conditions are warm."),
                    RecoveryBlock(block_id="recovery", markdown="Finish with five quiet minutes of walking."),
                ],
            )
        ],
        decision_ledger_entry=_decision(),
    )

    assert season.schema_version == execution.schema_version == 3
    assert {block.type for block in season.sections[0].blocks} == {
        "narrative",
        "callout",
        "checklist",
        "data_table",
        "phase_timeline",
        "disclosure",
        "notes",
    }
    assert {block.type for block in execution.sections[0].blocks} == {
        "workout",
        "interval_table",
        "fueling",
        "recovery",
    }
    assert len(execution.weeks) == 4
    assert sum(len(week.days) for week in execution.weeks) == 28
    assert "content_html" not in execution.model_dump_json()


def test_schema_v3_rejects_raw_html_in_model_authored_markdown():
    with pytest.raises(ValidationError, match="raw HTML"):
        NarrativeBlock(block_id="unsafe", markdown="<div style='color:red'>Do this</div>")


def test_execution_plan_rejects_non_28_day_calendar():
    weeks = _execution_weeks()
    shortened_last_week = weeks[-1].model_copy(update={"days": weeks[-1].days[:-1]})

    with pytest.raises(ValidationError, match="exactly 28 consecutive days"):
        ExecutionPlanArtifactV3(
            plan_id="execution-invalid",
            season_plan_id="season-synthetic",
            version=1,
            athlete_name="Sample Athlete",
            created_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
            title="Invalid block",
            summary_markdown="This deliberately omits one day.",
            start_date=date(2026, 8, 3),
            end_date=date(2026, 8, 30),
            weeks=[*weeks[:-1], shortened_last_week],
            decision_ledger_entry=_decision(),
        )


def test_artifact_ids_must_be_unique_within_their_scope():
    weeks = _execution_weeks()
    duplicate_day = weeks[0].days[0].model_copy(update={"date": weeks[0].days[1].date})
    invalid_week = weeks[0].model_copy(update={"days": [weeks[0].days[0], duplicate_day, *weeks[0].days[2:]]})

    with pytest.raises(ValidationError, match="day IDs must be unique"):
        ExecutionPlanArtifactV3(
            plan_id=f"execution-{uuid4()}",
            season_plan_id="season-synthetic",
            version=1,
            athlete_name="Sample Athlete",
            created_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
            title="Invalid IDs",
            summary_markdown="Duplicate IDs are not safe for calendar mutation.",
            start_date=date(2026, 8, 3),
            end_date=date(2026, 8, 30),
            weeks=[invalid_week, *weeks[1:]],
            decision_ledger_entry=_decision(),
        )


@pytest.mark.asyncio
async def test_invalid_head_coach_artifact_is_returned_for_one_bounded_repair():
    valid = SeasonStrategyArtifactV3(
        plan_id="season-repaired",
        version=1,
        athlete_name="Sample Athlete",
        created_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
        title="Autumn foundation",
        summary_markdown="Build repeatability before specificity.",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 11, 1),
        phases=[
            SeasonPhase(
                phase_id="phase-foundation",
                title="Foundation",
                start_date=date(2026, 8, 3),
                end_date=date(2026, 8, 30),
                objective_markdown="Establish repeatable frequency.",
            )
        ],
        decision_ledger_entry=_decision(),
    ).model_dump(mode="json")
    invalid = {**valid, "summary_markdown": "<script>unsafe()</script>"}
    repair = AsyncMock(return_value=valid)

    artifact = await validate_artifact_with_repair(
        invalid,
        artifact_type="season_plan",
        repair=repair,
    )

    assert artifact.plan_id == "season-repaired"
    assert repair.await_args is not None
    request = repair.await_args.args[0]
    assert request["rejected_output"] == invalid
    assert request["validation_errors"]
    assert "fallback" not in request


@pytest.mark.asyncio
async def test_exhausted_head_coach_artifact_repair_fails_without_replacement():
    invalid = {"type": "weekly_plan", "schema_version": 3, "title": "Incomplete"}
    repair = AsyncMock(return_value=invalid)

    with pytest.raises(ArtifactValidationError, match="repair budget exhausted"):
        await validate_artifact_with_repair(
            invalid,
            artifact_type="weekly_plan",
            repair=repair,
        )

    repair.assert_awaited_once()
