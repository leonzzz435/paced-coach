import sys
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.models.job import JobStatus
from api.routers import analysis
from api.services.local_usage import PlanGenerationAccess


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
    def __init__(self):
        self.job = None
        self.profile = SimpleNamespace(profile={"physiology": {"ftp": 250}})
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
        if "pg_advisory_xact_lock" in sql:
            return _FakeScalarResult(None)
        if "FROM athlete_profiles" in sql:
            return _FakeScalarResult(self.profile)
        if "FROM competitions" in sql:
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
        return None


class _FakeJobStatusDb:
    def __init__(self, job):
        self.job = job
        self.commit_calls = 0

    async def execute(self, statement, *_args, **_kwargs):
        sql = str(statement)
        if "FROM analysis_jobs" in sql:
            return _FakeScalarResult(self.job)
        raise AssertionError(f"Unexpected SQL: {sql}")

    async def commit(self):
        self.commit_calls += 1


@pytest.mark.asyncio
async def test_ensure_plan_generation_available_allows_repeat_generation(monkeypatch):
    async def _no_active_plan_generation_job(*_args, **_kwargs):
        return None

    prior_run_at = datetime(2026, 3, 21, 8, 0, tzinfo=UTC)

    async def _latest_full_run(*_args, **_kwargs):
        return prior_run_at

    monkeypatch.setattr("api.services.local_usage.limits._find_active_plan_generation_job", _no_active_plan_generation_job)
    monkeypatch.setattr("api.services.local_usage.limits.get_latest_full_run_created_at", _latest_full_run)

    access = await analysis.ensure_plan_generation_available(
        object(),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
    )

    assert access.mode == "free"


@pytest.mark.asyncio
async def test_ensure_plan_generation_available_blocks_active_job(monkeypatch):
    monkeypatch.setattr(
        "api.services.local_usage.limits.get_settings",
        lambda: SimpleNamespace(
            auth_mode="local",
            local_usage_safety_bypass=False,
            local_usage_dev_bypass=False,
            web_app_url="http://localhost:3000",
        ),
    )

    class _FakeResult:
        def scalar_one_or_none(self):
            return SimpleNamespace(id=uuid.uuid4(), status=JobStatus.RUNNING.value)

    class _FakeDb:
        async def execute(self, _stmt):
            return _FakeResult()

    with pytest.raises(HTTPException) as exc:
        await analysis.ensure_plan_generation_available(
            _FakeDb(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 409
    assert "already active or waiting for your clarification" in str(exc.value.detail)


@pytest.mark.asyncio
@pytest.mark.parametrize("access_mode", ["free_initial", "free"])
async def test_run_analysis_routes_every_generation_through_head_coach(monkeypatch, access_mode):
    fake_db = _FakeDb()
    delay_calls: dict[str, object] = {}

    async def _fake_plan_generation_access(*_args, **_kwargs):
        return PlanGenerationAccess(
            mode=access_mode,
            usage_context=None,
            initial_draft_claim_source_id=None,
        )

    def _fake_delay(job_id: str):
        delay_calls["job_id"] = job_id

    monkeypatch.setattr(analysis, "ensure_plan_generation_available", _fake_plan_generation_access)
    monkeypatch.setattr(analysis, "has_llm_provider_key", lambda: True)
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

    assert response.job_id == delay_calls["job_id"]
    assert fake_db.job is not None
    assert fake_db.job.config["_plan_generation_access_mode"] == access_mode
    assert fake_db.job.config["_workflow_version"] == "head_coach_v1"
    assert fake_db.job.config["athlete_profile"]["physiology"]["ftp"] == 250
    assert fake_db.job.config["competitions"][0]["name"] == "Test Race"


@pytest.mark.asyncio
async def test_run_analysis_requires_local_llm_key_before_claiming_generation(monkeypatch):
    async def _unexpected_plan_generation_access(*_args, **_kwargs):
        raise AssertionError("plan generation access should not be claimed without an LLM key")

    monkeypatch.setattr(analysis, "ensure_plan_generation_available", _unexpected_plan_generation_access)
    monkeypatch.setattr(analysis, "has_llm_provider_key", lambda: False)

    with pytest.raises(HTTPException) as exc:
        await analysis.run_analysis(
            analysis.AnalysisConfig(),
            db=object(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 503
    assert "OPENAI_API_KEY" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_get_job_status_releases_stale_free_initial_claim(monkeypatch):
    user_id = uuid.uuid4()
    job = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        status=JobStatus.RUNNING.value,
        created_at=datetime(2026, 3, 21, 8, 0, tzinfo=UTC),
        completed_at=None,
        cost_usd=None,
        tokens_used=None,
        progress_steps=[],
        error_message=None,
        config={"_plan_generation_access_mode": "free_initial"},
    )
    fake_db = _FakeJobStatusDb(job)
    release_calls: list[uuid.UUID] = []

    async def _fake_release_claim(_db, *, user_id):
        release_calls.append(user_id)
        return True

    monkeypatch.setenv("ANALYSIS_TASK_TIME_LIMIT_SECONDS", "1800")
    monkeypatch.setattr(analysis, "release_initial_draft_plan_claim", _fake_release_claim)

    response = await analysis.get_job_status(
        job.id,
        db=fake_db,  # type: ignore[arg-type]
        user_id=user_id,
    )

    assert response.status == JobStatus.FAILED.value
    assert job.error_message is not None
    assert "timed out" in job.error_message
    assert release_calls == [user_id]
    assert fake_db.commit_calls == 1


@pytest.mark.asyncio
async def test_cancel_job_releases_free_initial_claim(monkeypatch):
    user_id = uuid.uuid4()
    job = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        status=JobStatus.RUNNING.value,
        created_at=datetime(2026, 3, 21, 8, 0, tzinfo=UTC),
        completed_at=None,
        progress_steps=[],
        config={"_plan_generation_access_mode": "free_initial"},
    )
    fake_db = _FakeJobStatusDb(job)
    release_calls: list[uuid.UUID] = []

    async def _fake_release_claim(_db, *, user_id):
        release_calls.append(user_id)
        return True

    monkeypatch.setattr(analysis, "release_initial_draft_plan_claim", _fake_release_claim)

    response = await analysis.cancel_job(
        job.id,
        db=fake_db,  # type: ignore[arg-type]
        user_id=user_id,
    )

    assert response == {"job_id": str(job.id), "status": "cancelled"}
    assert release_calls == [user_id]
    assert fake_db.commit_calls == 1
