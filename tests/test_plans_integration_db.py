import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import create_async_engine


async def _is_db_reachable(database_url: str) -> bool:
    try:
        engine = create_async_engine(database_url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL_ASYNC")
    if not database_url:
        pytest.skip("Set DATABASE_URL_ASYNC to run DB integration tests")
    if os.getenv("ALLOW_DESTRUCTIVE_INTEGRATION_DB", "").lower() != "true":
        pytest.skip(
            "Set ALLOW_DESTRUCTIVE_INTEGRATION_DB=true to run destructive DB integration tests"
        )
    if "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    return database_url


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_active_plans_returns_200_when_rows_exist(monkeypatch):
    database_url = _require_database_url()
    if not await _is_db_reachable(database_url):
        pytest.skip("Postgres not reachable; start `docker compose up -d db` and run migrations")

    import api.config as config_module
    import api.deps as deps_module
    from api.main import create_app

    monkeypatch.setenv("DATABASE_URL_ASYNC", database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    config_module.get_settings.cache_clear()

    user_id = uuid.uuid4()
    source_job_id = uuid.uuid4()

    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE active_weekly_plans, active_season_plans, active_analyses, analysis_jobs, users "
                "RESTART IDENTITY CASCADE"
            )
        )

        from api.models.active_analysis import ActiveAnalysis
        from api.models.active_season_plan import ActiveSeasonPlan
        from api.models.active_weekly_plan import ActiveWeeklyPlan
        from api.models.job import AnalysisJob
        from api.models.user import User

        await conn.execute(
            insert(User).values(
                id=user_id,
                local_owner_key="test-owner",
                email="test@example.com",
                credits=1,
            )
        )
        await conn.execute(
            insert(AnalysisJob).values(
                id=source_job_id,
                user_id=user_id,
                status="completed",
                config={},
                result={},
            )
        )
        await conn.execute(
            insert(ActiveAnalysis).values(
                id=uuid.uuid4(),
                user_id=user_id,
                version=1,
                analysis_data={
                    "type": "analysis",
                    "schema_version": 2,
                    "version": 1,
                    "analysis_id": "test",
                    "athlete_name": "Test",
                    "kpis": [],
                    "sections": [],
                },
                expert_context={
                    "metrics_outputs": None,
                    "activity_outputs": None,
                    "physiology_outputs": None,
                },
                source_job_id=source_job_id,
            )
        )
        await conn.execute(
            insert(ActiveSeasonPlan).values(
                id=uuid.uuid4(),
                user_id=user_id,
                version=1,
                plan_data={
                    "type": "season_plan",
                    "schema_version": 2,
                    "version": 1,
                    "plan_id": "test",
                    "athlete_name": "Test",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "phases": [],
                },
                source_job_id=source_job_id,
            )
        )
        await conn.execute(
            insert(ActiveWeeklyPlan).values(
                id=uuid.uuid4(),
                user_id=user_id,
                version=1,
                plan_data={
                    "type": "weekly_plan",
                    "schema_version": 2,
                    "version": 1,
                    "plan_id": "test",
                    "athlete_name": "Test",
                    "weeks": [],
                },
                source_job_id=source_job_id,
            )
        )

    async def fake_get_current_user():
        return user_id

    app = create_app()
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user
    client = TestClient(app)

    res = client.get("/api/plans/active", headers={"Authorization": "Bearer test"})
    assert res.status_code == 200
    body = res.json()
    assert body["analysis"]["analysis"]["type"] == "analysis"
    assert body["weekly"]["weekly_plan"]["type"] == "weekly_plan"
    assert body["season"]["season_plan"]["type"] == "season_plan"
