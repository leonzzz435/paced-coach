from datetime import UTC, datetime

from api.services.status_messages import (
    current_analysis_step,
    mark_analysis_progress_step_completed,
    mark_analysis_progress_step_started,
    normalize_analysis_progress_steps,
    record_analysis_step_timing,
)


def test_record_analysis_step_timing_adds_actual_timing_fields():
    completed_at = datetime(2026, 3, 5, 21, 0, 0, tzinfo=UTC)

    updated_steps = record_analysis_step_timing(
        None,
        node_name="analysis_formatter",
        duration_seconds=42.25,
        timestamp=completed_at,
    )

    step = next(step for step in updated_steps if step["node"] == "analysis_formatter")
    assert step["actual_completed_at"] == completed_at.isoformat()
    assert step["actual_started_at"] == datetime(2026, 3, 5, 20, 59, 17, 750000, tzinfo=UTC).isoformat()
    assert step["duration_seconds"] == 42.25


def test_normalize_analysis_progress_steps_preserves_actual_timing_fields():
    normalized = normalize_analysis_progress_steps(
        [
            {
                "node": "weekly_planner",
                "label": "Building your weekly plan...",
                "status": "completed",
                "actual_started_at": "2026-03-05T20:00:00+00:00",
                "actual_completed_at": "2026-03-05T20:01:30+00:00",
                "duration_seconds": 90.0,
            }
        ]
    )

    step = next(step for step in normalized if step["node"] == "weekly_planner")
    assert step["actual_started_at"] == "2026-03-05T20:00:00+00:00"
    assert step["actual_completed_at"] == "2026-03-05T20:01:30+00:00"
    assert step["duration_seconds"] == 90.0


def test_mark_analysis_progress_steps_supports_multiple_active_nodes():
    started_at = datetime(2026, 3, 5, 21, 0, 0, tzinfo=UTC)
    progress_steps, _ = mark_analysis_progress_step_started(
        None,
        node_name="metrics_summarizer",
        timestamp=started_at,
    )
    progress_steps, _ = mark_analysis_progress_step_started(
        progress_steps,
        node_name="physiology_summarizer",
        timestamp=started_at,
    )

    metrics_step = next(step for step in progress_steps if step["node"] == "metrics_summarizer")
    physiology_step = next(step for step in progress_steps if step["node"] == "physiology_summarizer")

    assert metrics_step["status"] == "active"
    assert physiology_step["status"] == "active"
    assert current_analysis_step(progress_steps) == "Summarizing training metrics... (+1 more)"


def test_mark_analysis_progress_step_completed_only_completes_target_node():
    timestamp = datetime(2026, 3, 5, 21, 0, 0, tzinfo=UTC)
    progress_steps, _ = mark_analysis_progress_step_started(
        None,
        node_name="metrics_summarizer",
        timestamp=timestamp,
    )
    progress_steps, _ = mark_analysis_progress_step_started(
        progress_steps,
        node_name="physiology_summarizer",
        timestamp=timestamp,
    )

    updated_steps = mark_analysis_progress_step_completed(
        progress_steps,
        node_name="metrics_summarizer",
        timestamp=timestamp,
    )

    metrics_step = next(step for step in updated_steps if step["node"] == "metrics_summarizer")
    physiology_step = next(step for step in updated_steps if step["node"] == "physiology_summarizer")

    assert metrics_step["status"] == "completed"
    assert metrics_step["completed_at"] == timestamp.isoformat()
    assert physiology_step["status"] == "active"
