import datetime as dt

from services.ai.coach.patch_apply import apply_update_day_fields, apply_upsert_day_block
from services.ai.coach.schemas import UpdateDayFieldsOp, UpsertDayBlockOp
from services.ai.langgraph.schemas.ui_blocks import UiDayPlan, UiDisclosureNode, UiHtmlBlock, UiWeeklyPlan, UiWeekPlan


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
