import datetime as dt

import pytest
from pydantic import ValidationError

from api.services.active_plans import set_day_completion
from api.services.coach_patch_ops import apply_ops, parse_patch_ops, parse_weekly_plan
from services.ai.coach.patch_apply import apply_update_day_fields, apply_upsert_day_block
from services.ai.coach.schemas import (
    ReplaceV3SemanticBlockOp,
    UpdateDayFieldsOp,
    UpsertDayBlockOp,
)
from services.ai.head_coach.artifacts import (
    ArtifactSection,
    DecisionLedgerEntry,
    ExecutionDay,
    ExecutionPlanArtifactV3,
    ExecutionWeek,
    NarrativeBlock,
    TrainingSession,
)
from services.ai.langgraph.schemas.ui_blocks import UiDayPlan, UiDisclosureNode, UiHtmlBlock, UiWeeklyPlan, UiWeekPlan


def _v3_plan() -> ExecutionPlanArtifactV3:
    start = dt.date(2026, 8, 3)
    weeks = []
    for week_index in range(4):
        week_start = start + dt.timedelta(days=week_index * 7)
        days = []
        for day_index in range(7):
            day_date = week_start + dt.timedelta(days=day_index)
            sessions = []
            if day_index == 0:
                sessions = [
                    TrainingSession(
                        session_id=f"session-{week_index + 1}",
                        title="Aerobic run",
                        sport="running",
                        objective_markdown="Build calm aerobic durability.",
                        prescription_markdown="Run conversationally and finish relaxed.",
                        duration_min=45,
                        intensity="low",
                    )
                ]
            days.append(
                ExecutionDay(
                    day_id=f"day-{day_date.isoformat()}",
                    date=day_date,
                    label=day_date.strftime("%A"),
                    focus_type="aerobic" if sessions else "rest",
                    intensity="low" if sessions else "rest",
                    total_duration_min=45 if sessions else 0,
                    sessions=sessions,
                )
            )
        weeks.append(
            ExecutionWeek(
                week_id=f"week-{week_index + 1}",
                title=f"Week {week_index + 1}",
                start_date=week_start,
                end_date=week_start + dt.timedelta(days=6),
                intent_markdown="Protect repeatability.",
                days=days,
            )
        )
    return ExecutionPlanArtifactV3(
        plan_id="execution-1",
        season_plan_id="season-1",
        version=1,
        athlete_name="Sample Athlete",
        created_at=dt.datetime(2026, 8, 3, 9, tzinfo=dt.UTC),
        title="28 days of repeatable work",
        summary_markdown="Keep the work repeatable.",
        start_date=start,
        end_date=start + dt.timedelta(days=27),
        weeks=weeks,
        sections=[
            ArtifactSection(
                section_id="rules",
                title="Execution rules",
                blocks=[NarrativeBlock(block_id="rule-1", markdown="Keep easy days genuinely easy.")],
            )
        ],
        decision_ledger_entry=DecisionLedgerEntry(
            decision_id="decision-1",
            decided_at=dt.datetime(2026, 8, 3, 9, tzinfo=dt.UTC),
            title="Start with consistency",
            rationale_markdown="Repeatable work compounds.",
            changes_markdown="Created the initial execution block.",
        ),
    )


def test_apply_upsert_day_block_replaces_content_html_by_day_id():
    plan = UiWeeklyPlan(
        plan_id="weekly_1",
        athlete_name="Test",
        version=1,
        created_at=None,
        weeks=[
            UiWeekPlan(
                week_id="w1",
                week_label=None,
                start_date=dt.date(2026, 2, 10),
                end_date=dt.date(2026, 2, 16),
                days=[
                    UiDayPlan(
                        day_id="d1",
                        date=dt.date(2026, 2, 10),
                        day_label=None,
                        blocks=[UiHtmlBlock(key="main", variant="workout", content_html="A")],
                    ),
                    UiDayPlan(
                        day_id="d2",
                        date=dt.date(2026, 2, 11),
                        day_label="Tue",
                        workout_title="Old tempo session",
                        focus_type="tempo",
                        focus_color="#F97316",
                        blocks=[UiHtmlBlock(key="main", variant="workout", content_html="B")],
                        estimated_duration_min=50,
                        estimated_intensity="high",
                        readiness_note="Go as written — recovery strong.",
                    ),
                ],
            )
        ],
    )

    op = UpsertDayBlockOp(
        day_id="d2",
        block=UiHtmlBlock(key="main", variant="workout", content_html="<div>Updated</div>"),
    )
    res = apply_upsert_day_block(plan, op)

    assert res.changed is True
    updated_day = res.updated_plan.weeks[0].days[1]
    assert updated_day.blocks[0].content_html == "<div>Updated</div>"
    assert updated_day.date == dt.date(2026, 2, 11)
    assert updated_day.day_label == "Tue"
    assert updated_day.workout_title == "Old tempo session"
    assert updated_day.focus_type == "tempo"
    assert updated_day.focus_color == "#F97316"
    assert updated_day.estimated_duration_min == 50
    assert updated_day.estimated_intensity == "high"
    assert updated_day.readiness_note == "Go as written — recovery strong."


def test_apply_update_day_fields_updates_only_provided_fields():
    plan = UiWeeklyPlan(
        plan_id="weekly_1",
        athlete_name="Test",
        version=1,
        created_at=None,
        weeks=[
            UiWeekPlan(
                week_id="w1",
                week_label=None,
                start_date=dt.date(2026, 2, 10),
                end_date=dt.date(2026, 2, 16),
                days=[
                    UiDayPlan(
                        day_id="d2",
                        date=dt.date(2026, 2, 11),
                        day_label="Tue",
                        workout_title="Old tempo session",
                        focus_type="tempo",
                        focus_color="#F97316",
                        blocks=[UiHtmlBlock(key="main", variant="workout", content_html="B")],
                        estimated_duration_min=50,
                        estimated_intensity="high",
                        readiness_note="Go as written — recovery strong.",
                    ),
                ],
            )
        ],
    )

    op = UpdateDayFieldsOp(
        day_id="d2",
        workout_title="Controlled aerobic ride",
        estimated_duration_min=35,
        estimated_intensity="moderate",
        readiness_note="Dial it back — sleep was short.",
    )
    res = apply_update_day_fields(plan, op)

    assert res.changed is True
    updated_day = res.updated_plan.weeks[0].days[0]
    assert updated_day.day_label == "Tue"
    assert updated_day.workout_title == "Controlled aerobic ride"
    assert updated_day.focus_type == "tempo"
    assert updated_day.focus_color == "#F97316"
    assert updated_day.blocks[0].content_html == "B"
    assert updated_day.estimated_duration_min == 35
    assert updated_day.estimated_intensity == "moderate"
    assert updated_day.readiness_note == "Dial it back — sleep was short."


def test_apply_update_day_fields_noop_when_all_updates_are_null():
    plan = UiWeeklyPlan(
        plan_id="weekly_1",
        athlete_name="Test",
        version=1,
        created_at=None,
        weeks=[
            UiWeekPlan(
                week_id="w1",
                week_label=None,
                start_date=dt.date(2026, 2, 10),
                end_date=dt.date(2026, 2, 16),
                days=[
                    UiDayPlan(
                        day_id="d2",
                        date=dt.date(2026, 2, 11),
                        day_label="Tue",
                        workout_title="Old tempo session",
                        focus_type="tempo",
                        focus_color="#F97316",
                        blocks=[UiHtmlBlock(key="main", variant="workout", content_html="B")],
                        estimated_duration_min=50,
                        estimated_intensity="high",
                        readiness_note="Go as written — recovery strong.",
                    ),
                ],
            )
        ],
    )

    op = UpdateDayFieldsOp(day_id="d2", readiness_note=None)
    res = apply_update_day_fields(plan, op)

    assert res.changed is False
    updated_day = res.updated_plan.weeks[0].days[0]
    assert updated_day.workout_title == "Old tempo session"
    assert updated_day.readiness_note == "Go as written — recovery strong."


def test_apply_upsert_day_block_flattens_nodes_only_day_into_blocks():
    plan = UiWeeklyPlan(
        plan_id="weekly_1",
        athlete_name="Test",
        version=1,
        created_at=None,
        weeks=[
            UiWeekPlan(
                week_id="w1",
                week_label=None,
                start_date=dt.date(2026, 2, 10),
                end_date=dt.date(2026, 2, 16),
                days=[
                    UiDayPlan(
                        day_id="d2",
                        date=dt.date(2026, 2, 11),
                        day_label="Tue",
                        nodes=[
                            UiDisclosureNode(
                                node_id="root",
                                title="Session",
                                blocks=[
                                    UiHtmlBlock(key="main", variant="workout", content_html="B"),
                                    UiHtmlBlock(key="aux", variant="support", content_html="Aux"),
                                ],
                                children=[
                                    UiDisclosureNode(
                                        node_id="child",
                                        title="Cool-down",
                                        blocks=[UiHtmlBlock(key="cooldown", variant="support", content_html="CD")],
                                    )
                                ],
                            )
                        ],
                    ),
                ],
            )
        ],
    )

    op = UpsertDayBlockOp(
        day_id="d2",
        block=UiHtmlBlock(key="main", variant="workout", content_html="<div>Updated</div>"),
    )
    res = apply_upsert_day_block(plan, op)

    assert res.changed is True
    updated_day = res.updated_plan.weeks[0].days[0]
    assert updated_day.nodes == []
    by_key = {block.key: block for block in updated_day.blocks}
    assert set(by_key.keys()) == {"main", "aux", "cooldown"}
    assert by_key["main"].content_html == "<div>Updated</div>"
    assert by_key["aux"].content_html == "Aux"
    assert by_key["cooldown"].content_html == "CD"


def test_schema_v3_patch_updates_session_and_revalidates_full_artifact():
    plan = _v3_plan()
    ops = parse_patch_ops(
        [
            {
                "op": "update_session_fields_v3",
                "session_id": "session-1",
                "title": "Controlled progression run",
                "duration_min": 50,
                "intensity": "moderate",
            }
        ],
        schema_version=3,
    )

    updated, changed = apply_ops(plan, ops)

    assert changed is True
    assert isinstance(updated, ExecutionPlanArtifactV3)
    session = updated.weeks[0].days[0].sessions[0]
    assert session.title == "Controlled progression run"
    assert session.duration_min == 50
    assert session.intensity == "moderate"
    assert updated.weeks[0].days[0].total_duration_min == 50
    assert plan.weeks[0].days[0].sessions[0].title == "Aerobic run"


def test_schema_v3_rejects_day_total_that_disagrees_with_sessions():
    payload = _v3_plan().model_dump(mode="python")
    payload["weeks"][0]["days"][0]["total_duration_min"] = 10

    with pytest.raises(ValidationError, match="sum of its session durations"):
        ExecutionPlanArtifactV3.model_validate(payload)


def test_schema_v3_semantic_patch_rejects_raw_html_before_application():
    with pytest.raises(ValidationError, match="raw HTML"):
        ReplaceV3SemanticBlockOp(
            container_id="section:rules",
            block_id="rule-1",
            block=NarrativeBlock(block_id="rule-1", markdown="<b>Go hard</b>"),
        )


def test_patch_application_rejects_cross_schema_operations():
    plan = _v3_plan()
    legacy_op = UpdateDayFieldsOp(day_id=plan.weeks[0].days[0].day_id, workout_title="Wrong schema")

    with pytest.raises(ValueError, match="Schema-v1 patch operations"):
        apply_ops(plan, [legacy_op])


def test_weekly_plan_parser_dispatches_strictly_by_schema_version():
    plan = _v3_plan()

    assert parse_weekly_plan(plan.model_dump(mode="json")) == plan
    with pytest.raises(ValueError, match="Unsupported weekly-plan schema version"):
        parse_weekly_plan({"schema_version": 2})


def test_schema_v3_unknown_patch_operation_fails_visibly():
    with pytest.raises(ValueError, match="Unknown schema-v3 patch operation"):
        parse_patch_ops([{"op": "invent_workout_v3"}], schema_version=3)


def test_schema_v3_completion_round_trip_preserves_identity_and_version():
    plan = _v3_plan()
    target = plan.weeks[0].days[0]

    updated_payload = set_day_completion(
        plan.model_dump(mode="json"),
        day_id=target.day_id,
        is_completed=True,
    )
    updated = ExecutionPlanArtifactV3.model_validate(updated_payload)

    assert updated.plan_id == plan.plan_id
    assert updated.version == plan.version
    assert updated.weeks[0].days[0].date == target.date
    assert updated.weeks[0].days[0].is_completed is True
    assert plan.weeks[0].days[0].is_completed is False
