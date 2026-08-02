import os
import uuid
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")

from api.models.active_season_plan import ActiveSeasonPlan
from api.models.job import AnalysisJob, JobStatus
from worker.tasks import (
    _artifact_commit_already_completed,
    _handle_analysis_task_exception,
    _persist_head_coach_interrupt,
    _prepare_analysis_job_for_run,
)


def test_completed_job_requires_both_active_plan_commit_receipts():
    job_id = uuid.uuid4()
    completed_job = SimpleNamespace(
        status=JobStatus.COMPLETED.value,
        cancel_requested_at=None,
    )
    matching_season = SimpleNamespace(source_job_id=job_id)

    with pytest.raises(RuntimeError, match="no matching active-plan commit receipt"):
        _artifact_commit_already_completed(
            current_job=cast("AnalysisJob", completed_job),
            season_row=cast("ActiveSeasonPlan", matching_season),
            weekly_row=None,
            job_uuid=job_id,
        )


def test_worker_persists_clarification_without_completing_job():
    job = SimpleNamespace(
        status=JobStatus.RUNNING.value,
        config={"_workflow_version": "head_coach_v1"},
    )
    db = MagicMock()
    db.execute.return_value.scalar_one.return_value = job

    paused = _persist_head_coach_interrupt(
        db,
        job_uuid=uuid.uuid4(),
        result={
            "__interrupt__": (
                SimpleNamespace(
                    value={
                        "question": "Which days are available?",
                        "reason_markdown": "This changes the weekly structure.",
                        "requested_field": "availability",
                    }
                ),
            )
        },
    )

    assert paused is True
    assert job.status == JobStatus.AWAITING_INPUT.value
    assert job.config["_head_coach_interrupt"]["requested_field"] == "availability"
    db.commit.assert_called_once_with()


def test_duplicate_delivery_cannot_resurrect_completed_or_paused_job():
    db = MagicMock()
    completed = SimpleNamespace(status=JobStatus.COMPLETED.value, config={})
    paused = SimpleNamespace(status=JobStatus.AWAITING_INPUT.value, config={"_head_coach_interrupt": {}})

    for job in (completed, paused):
        assert not _prepare_analysis_job_for_run(
            db,
            job=cast("AnalysisJob", job),
            job_uuid=uuid.uuid4(),
            job_id="job-1",
            celery_task_id="task-1",
            is_initial_draft_run=True,
        )

    db.commit.assert_not_called()


def test_duplicate_delivery_cannot_take_over_running_job():
    db = MagicMock()
    running = SimpleNamespace(
        status=JobStatus.RUNNING.value,
        config={"_celery_task_id": "owning-task"},
    )

    assert not _prepare_analysis_job_for_run(
        db,
        job=cast("AnalysisJob", running),
        job_uuid=uuid.uuid4(),
        job_id="job-1",
        celery_task_id="duplicate-task",
        is_initial_draft_run=False,
    )

    db.commit.assert_not_called()


def test_post_commit_checkpoint_failure_does_not_mark_job_failed():
    job = SimpleNamespace(id=uuid.uuid4(), status=JobStatus.RUNNING.value)
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = JobStatus.COMPLETED.value

    _handle_analysis_task_exception(
        SimpleNamespace(request=SimpleNamespace(retries=0)),
        db,
        job=cast("AnalysisJob", job),
        job_id=str(job.id),
        exc=RuntimeError("checkpoint write failed after domain commit"),
        is_initial_draft_run=False,
    )

    db.rollback.assert_called_once_with()
    db.expire_all.assert_called_once_with()
