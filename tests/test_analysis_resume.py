import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from api.models.job import JobStatus
from api.routers.analysis import ResumeAnalysisRequest, resume_analysis
from api.services.analysis_resume import hash_resume_answer


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

    def add(self, _value):
        return None

    async def commit(self):
        self.commit_calls += 1


@pytest.mark.asyncio
async def test_resume_is_owned_durable_and_idempotent(monkeypatch):
    from worker.tasks import run_analysis_task

    delay = MagicMock()
    monkeypatch.setattr(run_analysis_task, "delay", delay)
    user_id = uuid.uuid4()
    job = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        status=JobStatus.AWAITING_INPUT.value,
        created_at=datetime.now(UTC),
        completed_at=None,
        progress_steps=[],
        config={
            "_workflow_version": "head_coach_v1",
            "_head_coach_interrupt": {
                "question": "Which days are reliably available?",
                "reason_markdown": "Availability changes the weekly structure.",
                "requested_field": "availability",
            },
        },
    )
    db = cast("Any", _FakeAsyncSession(job))
    request = ResumeAnalysisRequest(answer="Monday, Thursday, Saturday", idempotency_key="resume-1")

    first = await resume_analysis(job.id, request, db, user_id)
    second = await resume_analysis(job.id, request, db, user_id)

    assert first.status == JobStatus.PENDING.value
    assert second.status == JobStatus.PENDING.value
    assert job.config["_head_coach_resume"] == {
        "answer": "Monday, Thursday, Saturday",
        "answer_hash": hash_resume_answer("Monday, Thursday, Saturday"),
        "idempotency_key": "resume-1",
    }
    delay.assert_called_once_with(str(job.id))
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_resume_key_cannot_alias_a_different_answer(monkeypatch):
    from worker.tasks import run_analysis_task

    monkeypatch.setattr(run_analysis_task, "delay", MagicMock())
    user_id = uuid.uuid4()
    job = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        status=JobStatus.COMPLETED.value,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        progress_steps=[],
        config={
            "_head_coach_resume": {
                "answer_hash": hash_resume_answer("Monday and Friday"),
                "idempotency_key": "resume-1",
            }
        },
    )

    same = await resume_analysis(
        job.id,
        ResumeAnalysisRequest(answer="Monday and Friday", idempotency_key="resume-1"),
        cast("Any", _FakeAsyncSession(job)),
        user_id,
    )
    assert same.status == JobStatus.COMPLETED.value

    with pytest.raises(HTTPException) as exc:
        await resume_analysis(
            job.id,
            ResumeAnalysisRequest(answer="Tuesday", idempotency_key="resume-1"),
            cast("Any", _FakeAsyncSession(job)),
            user_id,
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_resume_enqueue_failure_restores_resumable_state(monkeypatch):
    from worker.tasks import run_analysis_task

    monkeypatch.setattr(run_analysis_task, "delay", MagicMock(side_effect=RuntimeError("broker down")))
    user_id = uuid.uuid4()
    interrupt = {
        "question": "Which days are reliably available?",
        "reason_markdown": "Availability changes the weekly structure.",
        "requested_field": "availability",
    }
    job = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        status=JobStatus.AWAITING_INPUT.value,
        created_at=datetime.now(UTC),
        completed_at=None,
        progress_steps=[],
        config={"_workflow_version": "head_coach_v1", "_head_coach_interrupt": interrupt},
    )
    db = cast("Any", _FakeAsyncSession(job))

    with pytest.raises(HTTPException) as exc:
        await resume_analysis(
            job.id,
            ResumeAnalysisRequest(answer="Monday and Friday", idempotency_key="resume-retryable"),
            db,
            user_id,
        )

    assert exc.value.status_code == 503
    assert job.status == JobStatus.AWAITING_INPUT.value
    assert job.config["_head_coach_interrupt"] == interrupt
    assert "_head_coach_resume" not in job.config
    assert db.commit_calls == 2
