from datetime import UTC, datetime

from api.services.status_messages import (
    current_analysis_step,
    initial_head_coach_progress_steps,
    mark_analysis_progress_step_started,
    normalize_analysis_progress_steps,
)


def test_head_coach_progress_uses_only_product_lifecycle_nodes() -> None:
    steps = initial_head_coach_progress_steps()

    assert [step["node"] for step in steps] == [
        "head_coach_understanding_context",
        "head_coach_designing_strategy",
        "head_coach_reviewing_constraints",
        "head_coach_awaiting_input",
        "head_coach_building_execution_block",
        "head_coach_saving_plan",
    ]
    assert all(step["status"] == "pending" for step in steps)


def test_normalize_progress_preserves_head_coach_timestamps() -> None:
    normalized = normalize_analysis_progress_steps(
        [
            {
                "node": "head_coach_designing_strategy",
                "status": "completed",
                "actual_started_at": "2026-07-19T20:00:00+00:00",
                "actual_completed_at": "2026-07-19T20:01:30+00:00",
                "duration_seconds": 90.0,
            }
        ]
    )

    step = next(step for step in normalized if step["node"] == "head_coach_designing_strategy")
    assert step["actual_started_at"] == "2026-07-19T20:00:00+00:00"
    assert step["actual_completed_at"] == "2026-07-19T20:01:30+00:00"
    assert step["duration_seconds"] == 90.0


def test_started_progress_exposes_product_copy() -> None:
    started_at = datetime(2026, 7, 19, 21, 0, 0, tzinfo=UTC)
    progress_steps, label = mark_analysis_progress_step_started(
        None,
        node_name="head_coach_understanding_context",
        timestamp=started_at,
    )

    assert label == "Understanding your goals and constraints..."
    assert current_analysis_step(progress_steps) == label
