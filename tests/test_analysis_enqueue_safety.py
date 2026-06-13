import sys
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from api.models.job import JobStatus
from api.routers import analysis


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeCompetitionResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


class _FakeDb:
    def __init__(self, *, fail_on_competitions_query: bool = False):
        self.commit_calls = 0
        self.rollback_calls = 0
        self.job: Any | None = None
        self.profile = SimpleNamespace(profile={"physiology": {"ftp": 250}})
        self.fail_on_competitions_query = fail_on_competitions_query
        self.competitions = [
            SimpleNamespace(
                id=uuid.uuid4(),
                name="Test Race",
                date=None,
                date_text="Mid-October 2026",
                race_type="Half Marathon",
                priority="A",
                target_time="01:40:00",
                notes="Note",
            )
        ]

    async def execute(self, statement, *_args, **_kwargs):
        sql = str(statement)
        if "FROM athlete_profiles" in sql:
            return _FakeScalarResult(self.profile)
        if "FROM competitions" in sql:
            if self.fail_on_competitions_query:
                raise RuntimeError("competition lookup failed")
            return _FakeCompetitionResult(self.competitions)
        raise AssertionError(f"Unexpected SQL: {sql}")

    def add(self, obj):
        if hasattr(obj, "config") and hasattr(obj, "user_id"):
            self.job = obj

    async def flush(self):
        if self.job is None:
            return
        if getattr(self.job, "id", None) is None:
            self.job.id = uuid.uuid4()
        if getattr(self.job, "status", None) is None:
            self.job.status = JobStatus.PENDING.value
        if getattr(self.job, "created_at", None) is None:
            self.job.created_at = datetime(2026, 3, 21, tzinfo=UTC)

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1


def _patch_common_dependencies(monkeypatch):
    async def _fake_plan_generation_access(*_args, **_kwargs):
        return SimpleNamespace(
            mode="dev_bypass",
            usage_context=None,
            initial_draft_claim_source_id=None,
        )

    monkeypatch.setattr(analysis, "ensure_plan_generation_available", _fake_plan_generation_access)
    monkeypatch.setattr(analysis, "has_llm_provider_key", lambda: True)


@pytest.mark.asyncio
async def test_run_analysis_commits_before_enqueue(monkeypatch):
    _patch_common_dependencies(monkeypatch)
    fake_db = _FakeDb()
    delay_calls: dict[str, object] = {}

    def _fake_delay(job_id: str):
        delay_calls["job_id"] = job_id
        delay_calls["commit_calls_at_delay"] = fake_db.commit_calls

    monkeypatch.setitem(
        sys.modules,
        "worker.tasks",
        SimpleNamespace(run_analysis_task=SimpleNamespace(delay=_fake_delay)),
    )

    response = await analysis.run_analysis(
        analysis.AnalysisConfig(),
        db=fake_db,  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
    )

    assert delay_calls["job_id"] == response.job_id
    assert delay_calls["commit_calls_at_delay"] == 1
    assert fake_db.commit_calls == 1


@pytest.mark.asyncio
async def test_run_analysis_marks_job_failed_when_enqueue_fails(monkeypatch):
    _patch_common_dependencies(monkeypatch)
    fake_db = _FakeDb()

    def _failing_delay(_job_id: str):
        raise RuntimeError("broker unavailable")

    monkeypatch.setitem(
        sys.modules,
        "worker.tasks",
        SimpleNamespace(run_analysis_task=SimpleNamespace(delay=_failing_delay)),
    )

    with pytest.raises(HTTPException) as exc:
        await analysis.run_analysis(
            analysis.AnalysisConfig(),
            db=fake_db,  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 503
    assert fake_db.commit_calls == 2
    assert fake_db.job is not None
    assert fake_db.job.status == JobStatus.FAILED.value
    assert fake_db.job.error_message == "Failed to enqueue analysis job"
    assert fake_db.job.completed_at is not None


@pytest.mark.asyncio
async def test_run_analysis_surfaces_setup_errors_without_extra_claim_cleanup(monkeypatch):
    fake_db = _FakeDb(fail_on_competitions_query=True)

    async def _fake_plan_generation_access(*_args, **_kwargs):
        return SimpleNamespace(
            mode="free",
            usage_context=None,
            initial_draft_claim_source_id=None,
        )

    monkeypatch.setattr(analysis, "ensure_plan_generation_available", _fake_plan_generation_access)
    monkeypatch.setattr(analysis, "has_llm_provider_key", lambda: True)

    with pytest.raises(RuntimeError, match="competition lookup failed"):
        await analysis.run_analysis(
            analysis.AnalysisConfig(),
            db=fake_db,  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
        )

    assert fake_db.commit_calls == 0
    assert fake_db.rollback_calls == 0
