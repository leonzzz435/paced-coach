import uuid
from datetime import UTC, datetime

import pytest


class FakeAthleteProfile:
    def __init__(self, profile: dict):
        self.profile = profile


class FakeJob:
    def __init__(self, user_id: uuid.UUID, config: dict):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.status = "pending"
        self.config = config
        self.result = {"weekly_plan_html": "<h1>plan</h1>"}
        self.error_message = None
        self.cost_usd = 0.0
        self.tokens_used = 0
        self.created_at = datetime.now()
        self.completed_at = None
        self.cancel_requested_at = None


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return []


class FakeCompetition:
    def __init__(self):
        self.id = uuid.uuid4()
        self.name = "Test Race"
        self.date = None
        self.date_text = "Mid-October 2026"
        self.race_type = "Half Marathon"
        self.priority = "A"
        self.target_time = "01:40:00"
        self.notes = "Note"


class FakeWhoopCredentials:
    def __init__(self):
        self.encrypted_access_token = b"access-token"
        self.encrypted_refresh_token = b"refresh-token"
        self.expires_at = datetime(2099, 12, 31, tzinfo=UTC)
        self.scope = "offline read:recovery"
        self.whoop_user_id = 12345


class FakeCompetitionResult:
    def __init__(self, competitions: list[FakeCompetition]):
        self._competitions = competitions

    def scalars(self):
        return FakeScalars(self._competitions)


class FakeScalars:
    def __init__(self, items: list[FakeCompetition]):
        self._items = items

    def all(self):
        return self._items


class FakeAsyncSession:
    def __init__(self):
        self.user_id = uuid.uuid4()
        self.job: FakeJob | None = None
        self._last_added = None
        self.profile = FakeAthleteProfile({"physiology": {"ftp": 250}})
        self.competitions = [FakeCompetition()]
        self.whoop = FakeWhoopCredentials()

    async def execute(self, *args, **_kwargs):
        sql = str(args[0])
        if "FROM whoop_credentials" in sql:
            return FakeScalarResult(self.whoop)
        if "FROM analysis_jobs" in sql:
            return FakeScalarResult(self.job)
        if "FROM competitions" in sql:
            return FakeCompetitionResult(self.competitions)
        if "FROM athlete_profiles" in sql:
            return FakeScalarResult(self.profile)
        return FakeScalarResult(None)

    def add(self, obj):
        self._last_added = obj
        if hasattr(obj, "config"):
            self.job = FakeJob(user_id=obj.user_id, config=obj.config)
            obj.id = self.job.id
            obj.status = self.job.status
            obj.created_at = self.job.created_at

    async def flush(self):
        return None

    async def commit(self):
        return None


def _configure_local_usage_bypass(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_USAGE_DEV_BYPASS", "true")
    monkeypatch.setenv("local_usage_dev_bypass", "true")
    monkeypatch.setenv("WEB_APP_URL", "http://localhost:3000")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    import api.config as config_module

    config_module.get_settings.cache_clear()


def _build_smoke_test_client(monkeypatch, fake_session: FakeAsyncSession):
    from fastapi.testclient import TestClient

    import api.deps as deps_module
    import worker.tasks as worker_tasks
    from api.main import create_app
    from api.routers import analysis as analysis_router
    from api.routers import competitions as competitions_router
    from api.routers import plans as plans_router

    async def fake_get_db():
        yield fake_session

    async def fake_get_current_user():
        return fake_session.user_id

    monkeypatch.setattr(analysis_router, "get_db", fake_get_db)
    monkeypatch.setattr(analysis_router, "get_current_user", fake_get_current_user)
    monkeypatch.setattr(plans_router, "get_db", fake_get_db)
    monkeypatch.setattr(plans_router, "get_current_user", fake_get_current_user)
    monkeypatch.setattr(competitions_router, "get_db", fake_get_db)
    monkeypatch.setattr(competitions_router, "get_current_user", fake_get_current_user)
    monkeypatch.setattr(analysis_router, "has_llm_provider_key", lambda: True)
    monkeypatch.setattr(worker_tasks.run_analysis_task, "delay", lambda *_args, **_kwargs: None)

    app = create_app()
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    return TestClient(app)


def _post_analysis_run(client):
    return client.post(
        "/api/analysis/run",
        json={
            "athlete_name": "Test",
            "activities_days": 7,
            "metrics_days": 14,
            "plan_start_date": "2026-03-01",
            "run_overrides": {
                "analysis_notes": "Legs feel heavy from travel.",
                "planning_notes": "Keep first week conservative.",
                "temporary_constraints": "No pool access for 5 days.",
            },
        },
        headers={"Authorization": "Bearer test"},
    )


def _assert_immutable_snapshot_written(fake_session: FakeAsyncSession) -> None:
    assert fake_session.job is not None
    assert "athlete_profile" in fake_session.job.config
    assert fake_session.job.config["athlete_profile"]["physiology"]["ftp"] == 250
    assert "competitions" in fake_session.job.config
    assert len(fake_session.job.config["competitions"]) == 1
    assert fake_session.job.config["competitions"][0]["name"] == "Test Race"
    assert fake_session.job.config["competitions"][0]["date_text"] == "Mid-October 2026"
    assert fake_session.job.config["plan_start_date"] == "2026-03-01"
    assert fake_session.job.config["run_overrides"]["planning_notes"] == "Keep first week conservative."


@pytest.mark.integration
def test_api_smoke_analysis_job_lifecycle_without_ai(monkeypatch):
    """End-to-end-ish smoke test without LLM calls."""
    _configure_local_usage_bypass(monkeypatch)
    fake_session = FakeAsyncSession()
    client = _build_smoke_test_client(monkeypatch, fake_session)

    run_res = _post_analysis_run(client)
    assert run_res.status_code == 202
    job_id = run_res.json()["job_id"]
    _assert_immutable_snapshot_written(fake_session)

    status_res = client.get(f"/api/analysis/{job_id}", headers={"Authorization": "Bearer test"})
    assert status_res.status_code == 200
    assert status_res.json()["job_id"] == job_id

    plans_res = client.get("/api/plans/active", headers={"Authorization": "Bearer test"})
    assert plans_res.status_code == 404
