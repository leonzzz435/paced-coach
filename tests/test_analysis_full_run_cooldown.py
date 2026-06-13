import sys
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.models.job import JobStatus
from api.routers import analysis
from api.services.full_run_policy import FullRunAvailability
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
async def test_ensure_plan_generation_available_returns_cooldown_when_faster_plan_would_unlock_now(monkeypatch):
    next_allowed_at = datetime(2026, 3, 21, 8, 0, tzinfo=UTC)
    free_plan = SimpleNamespace(plan_generation_cooldown_days=28)

    async def _fake_usage_context(*_args, **_kwargs):
        return SimpleNamespace(has_access=False, effective_plan=free_plan)

    call_count = {"count": 0}

    async def _fake_availability(*_args, **_kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return FullRunAvailability(
                allowed=False,
                last_run_at=datetime(2026, 2, 21, 8, 0, tzinfo=UTC),
                next_allowed_at=next_allowed_at,
            )
        return FullRunAvailability(
            allowed=True,
            last_run_at=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
            next_allowed_at=None,
        )

    monkeypatch.setenv("WEB_APP_URL", "https://test.paced.coach")
    monkeypatch.setattr(
        "api.services.local_usage.limits.get_settings",
        lambda: SimpleNamespace(local_usage_dev_bypass=False, web_app_url="https://test.paced.coach"),
    )
    async def _no_active_plan_generation_job(*_args, **_kwargs):
        return None

    monkeypatch.setattr("api.services.local_usage.limits._find_active_plan_generation_job", _no_active_plan_generation_job)
    monkeypatch.setattr("api.services.local_usage.limits.get_local_usage_context", _fake_usage_context)
    monkeypatch.setattr("api.services.local_usage.limits.evaluate_full_run_availability", _fake_availability)

    with pytest.raises(HTTPException) as exc:
        await analysis.ensure_plan_generation_available(
            object(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 429
    assert "Next allowed at" in str(exc.value.detail)


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
    assert "already running" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_run_analysis_allows_providerless_free_generation(monkeypatch):
    fake_db = _FakeDb()
    delay_calls: dict[str, object] = {}

    async def _fake_plan_generation_access(*_args, **_kwargs):
        return PlanGenerationAccess(
            mode="free",
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
    assert fake_db.job.config["_plan_generation_access_mode"] == "free"
    assert fake_db.job.config["athlete_profile"]["physiology"]["ftp"] == 250
    assert fake_db.job.config["competitions"][0]["name"] == "Test Race"


@pytest.mark.asyncio
async def test_run_analysis_returns_wait_message_when_free_cadence_still_cooling_down(monkeypatch):
    async def _reject_generation(*_args, **_kwargs):
        raise HTTPException(
            status_code=429,
            detail="Free plan generation is limited to once every 28 days. Next allowed at 2026-04-18T08:00:00+00:00.",
        )

    monkeypatch.setattr(analysis, "ensure_plan_generation_available", _reject_generation)
    monkeypatch.setattr(analysis, "has_llm_provider_key", lambda: True)

    with pytest.raises(HTTPException) as exc:
        await analysis.run_analysis(
            analysis.AnalysisConfig(),
            db=object(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 429
    assert "once every 28 days" in str(exc.value.detail)


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
