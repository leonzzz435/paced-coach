import uuid
from typing import Any, cast

import pytest


@pytest.mark.unit
def test_public_api_excludes_training_data_provider_routes(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "http://localhost:3000")

    from api.config import get_settings
    from api.main import create_app

    get_settings.cache_clear()
    route_paths = {path for route in create_app().routes if (path := getattr(route, "path", None)) is not None}

    excluded_paths = {
        "/api/oauth/strava/start",
        "/api/oauth/strava/callback",
        "/api/oauth/whoop/start",
        "/api/oauth/whoop/callback",
        "/api/integrations/status",
        "/api/account/strava/disconnect",
        "/api/account/whoop/disconnect",
        "/api/daily/run",
        "/api/weekly-recap/latest",
    }

    assert route_paths.isdisjoint(excluded_paths)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_coach_registry_never_loads_external_training_providers():
    from api.services.ongoing_tools import build_ongoing_tool_registry

    async with build_ongoing_tool_registry(
        cast("Any", object()),
        user_id=uuid.uuid4(),
        require_training_provider=False,
    ) as registry:
        assert registry._providers == {}


@pytest.mark.unit
def test_plan_worker_ignores_legacy_provider_credentials():
    from worker.tasks import _load_training_sources

    sources, source_gaps = _load_training_sources(
        cast("Any", object()),
        user_id=uuid.uuid4(),
        job_id="release-contract",
        activities_days=30,
        metrics_days=90,
    )

    assert sources == {}
    assert source_gaps == []
