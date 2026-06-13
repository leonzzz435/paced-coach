import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

from api.models.job import JobStatus
from api.routers.analysis import get_job_status


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeAsyncSession:
    def __init__(self, job):
        self.job = job
        self.commit_calls = 0

    async def execute(self, *_args, **_kwargs):
        return _FakeScalarResult(self.job)

    async def commit(self):
        self.commit_calls += 1


@pytest.mark.asyncio
async def test_get_job_status_auto_fails_stale_running_job(monkeypatch):
    monkeypatch.setenv("ANALYSIS_TASK_TIME_LIMIT_SECONDS", "1200")
    monkeypatch.setenv("ANALYSIS_TASK_STALE_GRACE_SECONDS", "60")

    now = datetime.now(UTC)
    job = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        status=JobStatus.RUNNING.value,
        created_at=now - timedelta(seconds=1261),
        completed_at=None,
        cost_usd=None,
        tokens_used=None,
        error_message=None,
    )
    db = cast("Any", _FakeAsyncSession(job))

    response = await get_job_status(job.id, db, job.user_id)

    assert response.status == JobStatus.FAILED.value
    assert job.status == JobStatus.FAILED.value
    assert job.error_message == "Job timed out (exceeded maximum execution time of 1200s)"
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_get_job_status_keeps_running_job_when_timeouts_are_disabled(monkeypatch):
    monkeypatch.delenv("ANALYSIS_TASK_TIME_LIMIT_SECONDS", raising=False)
    monkeypatch.delenv("ANALYSIS_TASK_SOFT_TIME_LIMIT_SECONDS", raising=False)
    monkeypatch.delenv("ANALYSIS_TASK_STALE_GRACE_SECONDS", raising=False)

    now = datetime.now(UTC)
    job = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        status=JobStatus.RUNNING.value,
        created_at=now - timedelta(days=2),
        completed_at=None,
        cost_usd=None,
        tokens_used=None,
        error_message=None,
    )
    db = cast("Any", _FakeAsyncSession(job))

    response = await get_job_status(job.id, db, job.user_id)

    assert response.status == JobStatus.RUNNING.value
    assert db.commit_calls == 0
