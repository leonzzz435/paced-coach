import asyncio
import os
import types
import uuid
from unittest.mock import MagicMock, patch

import openai
import pytest
from billiard.exceptions import SoftTimeLimitExceeded  # type: ignore[import-untyped]

from api.models.job import JobStatus

_NO_FAKE_RESULT = object()


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _fake_workflow_result() -> dict:
    class FakeAnalysisResult:
        def model_dump(self, *args, **kwargs):
            return {"type": "analysis", "analysis_id": "analysis_1"}

    class FakeWeeklyResult:
        def model_dump(self, *args, **kwargs):
            return {"type": "weekly_plan", "plan_id": "weekly_1"}

    class FakeSeasonResult:
        def model_dump(self, *args, **kwargs):
            return {"type": "season_plan", "plan_id": "season_1"}

    empty_output: dict[str, dict[str, dict[str, list[object]]]] = {
        "output": {
            "for_synthesis": {"signals": [], "evidence": [], "implications": []},
            "for_season_planner": {"signals": [], "evidence": [], "implications": []},
            "for_weekly_planner": {"signals": [], "evidence": [], "implications": []},
        }
    }
    return {
        "analysis_blocks": FakeAnalysisResult(),
        "weekly_plan_blocks": FakeWeeklyResult(),
        "season_plan_blocks": FakeSeasonResult(),
        "metrics_outputs": empty_output,
        "activity_outputs": empty_output,
        "physiology_outputs": empty_output,
        "weekly_plan_html": "<html></html>",
        "season_plan_html": "<html></html>",
        "analysis_html": "<html></html>",
        "season_plan": "season",
        "weekly_plan": "weekly",
        "execution_id": "exec_1",
        "cost_summary": {"total_cost_usd": 0.0, "total_tokens": 0},
        "execution_metadata": {
            "trace_id": "trace_1",
            "root_run_id": "root_1",
            "execution_time_seconds": 123.4,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "node_timings_seconds": {"analysis_formatter": 91.4},
        },
    }


def _make_fake_job(job_id: uuid.UUID):
    return types.SimpleNamespace(
        id=job_id,
        user_id=uuid.uuid4(),
        status=JobStatus.PENDING.value,
        config={
            "activities_days": 7,
            "metrics_days": 14,
            "athlete_name": "Test",
            "run_overrides": {
                "analysis_notes": "",
                "planning_notes": "",
                "temporary_constraints": "",
            },
            "competitions": [],
            "enable_plotting": False,
        },
        result=None,
        cost_usd=None,
        tokens_used=None,
        completed_at=None,
        error_message=None,
        progress_steps=None,
    )


def _make_fake_strava_credentials(user_id: uuid.UUID):
    return types.SimpleNamespace(
        user_id=user_id,
        encrypted_access_token=b"encrypted-access",
        encrypted_refresh_token=b"encrypted-refresh",
        expires_at=None,
        scope="read",
    )


def _make_fake_active_weekly_plan():
    return types.SimpleNamespace(
        version=3,
        source_job_id=None,
        plan_data={
            "type": "weekly_plan",
            "plan_id": "weekly_previous",
            "version": 3,
            "athlete_name": "Test",
            "plan_brief": "Previous block intentionally absorbed fatigue with easy days.",
            "weeks": [
                {
                    "week_id": "wk-2026-05-04",
                    "week_label": "Transition Week",
                    "week_theme": "Absorb and sharpen",
                    "start_date": "2026-05-04",
                    "end_date": "2026-05-10",
                    "days": [
                        {
                            "day_id": "2026-05-09",
                            "date": "2026-05-09",
                            "day_label": "Saturday",
                            "workout_title": "Easy aerobic run",
                            "focus_type": "easy",
                            "estimated_duration_min": 35,
                            "estimated_intensity": "low",
                        },
                        {
                            "day_id": "2026-05-10",
                            "date": "2026-05-10",
                            "day_label": "Sunday",
                            "workout_title": "Rest day",
                            "estimated_intensity": "rest",
                        },
                    ],
                }
            ],
        },
    )


def _fake_worker_query_result(
    sql: str,
    *,
    fake_job,
    fake_strava_creds,
    fake_active_analysis,
    fake_active_weekly,
):
    if sql.startswith("select analysis_jobs.cancel_requested_at"):
        return _FakeScalarResult(None)
    if "from analysis_jobs" in sql:
        return _FakeScalarResult(fake_job)
    if "from strava_credentials" in sql:
        return _FakeScalarResult(fake_strava_creds)
    if "from whoop_credentials" in sql:
        return _FakeScalarResult(None)
    if "from active_analyses" in sql:
        return _FakeScalarResult(fake_active_analysis)
    if "from active_weekly_plans" in sql:
        return _FakeScalarResult(fake_active_weekly)
    if "from local_usage_events" in sql:
        return _FakeScalarResult(None)
    return _NO_FAKE_RESULT


def _fake_season_result(sql: str, *, fake_active_season, state: dict[str, bool]):
    if "from active_season_plans" not in sql:
        return _NO_FAKE_RESULT
    if not state["season_lookup_done"]:
        state["season_lookup_done"] = True
        return _FakeScalarResult(None)
    return _FakeScalarResult(fake_active_season)


def _build_fake_session(
    *,
    fake_job,
    fake_strava_creds,
    fake_active_analysis=None,
    fake_active_season=None,
    fake_active_weekly=None,
):
    state = {"season_lookup_done": False}

    def fake_execute(statement):
        sql = str(statement).lower()
        season_result = _fake_season_result(sql, fake_active_season=fake_active_season, state=state)
        if season_result is not _NO_FAKE_RESULT:
            return season_result
        result = _fake_worker_query_result(
            sql,
            fake_job=fake_job,
            fake_strava_creds=fake_strava_creds,
            fake_active_analysis=fake_active_analysis,
            fake_active_weekly=fake_active_weekly,
        )
        if result is not _NO_FAKE_RESULT:
            return result
        return _FakeScalarResult(None)

    fake_session = MagicMock()
    fake_session.__enter__.return_value = fake_session
    fake_session.__exit__.return_value = None
    fake_session.execute.side_effect = fake_execute
    return fake_session


def test_run_override_contexts_propagate_planning_notes_to_experts_and_planners():
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")

    from worker.tasks import _build_run_override_contexts

    analysis_context, planning_context = _build_run_override_contexts(
        {
            "analysis_notes": "Legs feel stale.",
            "planning_notes": "Add one playful hill challenge each week.",
            "temporary_constraints": "No gym access.",
        }
    )

    assert "Run overrides (analysis focus)" in analysis_context
    assert "Custom planning instructions for downstream planner fields" in analysis_context
    assert "Add one playful hill challenge each week." in analysis_context
    assert "`for_season_planner` and `for_weekly_planner`" in analysis_context
    assert "Custom planning instructions for this run" in planning_context
    assert "must preserve unless unsafe" in planning_context
    assert "Temporary constraints for this run (must constrain analysis and planning)" in analysis_context
    assert "Temporary constraints for this run (must constrain analysis and planning)" in planning_context


def test_worker_serializes_plan_blocks_into_job_result():
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    job_id = uuid.uuid4()
    fake_job = _make_fake_job(job_id)
    fake_strava_creds = _make_fake_strava_credentials(fake_job.user_id)

    fake_active_analysis = types.SimpleNamespace(
        version=1,
        analysis_data=None,
        expert_context=None,
        source_job_id=None,
    )
    fake_active_season = types.SimpleNamespace(
        version=1,
        plan_data=None,
        source_job_id=None,
    )
    fake_active_weekly = types.SimpleNamespace(
        version=1,
        plan_data=None,
        source_job_id=None,
    )
    fake_session = _build_fake_session(
        fake_job=fake_job,
        fake_strava_creds=fake_strava_creds,
        fake_active_analysis=fake_active_analysis,
        fake_active_season=fake_active_season,
        fake_active_weekly=fake_active_weekly,
    )

    from worker.tasks import run_analysis_task

    def fake_asyncio_run(coro):
        if asyncio.iscoroutine(coro):
            coro.close()
        return _fake_workflow_result()

    with patch("worker.tasks.get_sync_session", return_value=fake_session):
        with patch("worker.tasks.asyncio.run", side_effect=fake_asyncio_run):
            run_analysis_task(str(job_id))

    assert fake_job.status == JobStatus.COMPLETED.value
    assert isinstance(fake_job.result, dict)
    assert fake_job.result["analysis_blocks"]["analysis_id"] == "analysis_1"
    assert fake_job.result["weekly_plan_blocks"]["plan_id"] == "weekly_1"
    assert fake_job.result["season_plan_blocks"]["plan_id"] == "season_1"
    assert fake_job.result["execution_metadata"]["node_timings_seconds"] == {"analysis_formatter": 91.4}
    assert "planning_html" not in fake_job.result

    assert fake_active_analysis.version == 2
    assert fake_active_season.version == 2
    assert fake_active_weekly.version == 2
    assert fake_active_analysis.analysis_data == {"type": "analysis", "analysis_id": "analysis_1", "version": 2}
    assert fake_active_season.plan_data == {"type": "season_plan", "plan_id": "season_1", "version": 2}
    assert fake_active_weekly.plan_data == {"type": "weekly_plan", "plan_id": "weekly_1", "version": 2}
    assert isinstance(fake_active_analysis.expert_context, dict)
    assert "metrics_outputs" in fake_active_analysis.expert_context


def test_worker_passes_provider_free_transition_context_with_active_weekly_plan_to_workflow():
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    job_id = uuid.uuid4()
    fake_job = _make_fake_job(job_id)
    fake_strava_creds = _make_fake_strava_credentials(fake_job.user_id)
    fake_active_weekly = _make_fake_active_weekly_plan()
    fake_session = _build_fake_session(
        fake_job=fake_job,
        fake_strava_creds=fake_strava_creds,
        fake_active_weekly=fake_active_weekly,
    )

    captured_kwargs = {}

    async def fake_run_complete_analysis_and_planning(**kwargs):
        captured_kwargs.update(kwargs)
        return _fake_workflow_result()

    from worker.tasks import run_analysis_task

    with patch("worker.tasks.get_sync_session", return_value=fake_session):
        with patch(
            "worker.tasks.run_complete_analysis_and_planning",
            side_effect=fake_run_complete_analysis_and_planning,
        ):
            run_analysis_task(str(job_id))

    assert fake_job.status == JobStatus.COMPLETED.value
    assert "transition_context" in captured_kwargs
    assert "No recent executed sessions in the extracted window" in captured_kwargs["transition_context"]
    assert "Existing Active Weekly Plan" in captured_kwargs["transition_context"]
    assert "Easy aerobic run" in captured_kwargs["transition_context"]
    assert "intensity=rest" in captured_kwargs["transition_context"]
    assert "first 3-7 days" in captured_kwargs["transition_context"]
    assert captured_kwargs["existing_weekly_plan"] is not None


def test_worker_marks_job_failed_on_soft_time_limit(monkeypatch):
    monkeypatch.setenv("ANALYSIS_TASK_TIME_LIMIT_SECONDS", "1800")
    monkeypatch.setenv("ANALYSIS_TASK_SOFT_TIME_LIMIT_SECONDS", "1770")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    job_id = uuid.uuid4()
    fake_job = _make_fake_job(job_id)
    fake_strava_creds = _make_fake_strava_credentials(fake_job.user_id)
    fake_session = _build_fake_session(fake_job=fake_job, fake_strava_creds=fake_strava_creds)

    from worker.tasks import run_analysis_task

    def fake_asyncio_run(coro):
        if asyncio.iscoroutine(coro):
            coro.close()
        raise SoftTimeLimitExceeded()

    with patch("worker.tasks.get_sync_session", return_value=fake_session):
        with patch("worker.tasks.asyncio.run", side_effect=fake_asyncio_run):
            with pytest.raises(SoftTimeLimitExceeded):
                run_analysis_task(str(job_id))

    assert fake_job.status == JobStatus.FAILED.value
    assert fake_job.completed_at is not None
    assert fake_job.error_message == "Job timed out (soft time limit exceeded after 1770s)"


def test_worker_formats_openai_insufficient_quota_as_actionable_error():
    from worker.tasks import _format_analysis_task_error_message

    error = RuntimeError("Required AI stage failed: OpenAI error code: insufficient_quota")

    assert _format_analysis_task_error_message(error) == (
        "OpenAI API quota exhausted. Add billing credit or configure another supported LLM provider, then retry."
    )


def test_worker_defers_terminal_failure_while_autoretry_attempts_remain():
    from worker.tasks import _should_defer_failure_to_autoretry

    exc = openai.APITimeoutError.__new__(openai.APITimeoutError)
    task = types.SimpleNamespace(
        request=types.SimpleNamespace(retries=0),
        max_retries=2,
    )

    assert _should_defer_failure_to_autoretry(task, exc) is True


def test_worker_marks_retryable_error_terminal_after_final_attempt():
    from worker.tasks import _should_defer_failure_to_autoretry

    exc = openai.APITimeoutError.__new__(openai.APITimeoutError)
    task = types.SimpleNamespace(
        request=types.SimpleNamespace(retries=2),
        max_retries=2,
    )

    assert _should_defer_failure_to_autoretry(task, exc) is False
