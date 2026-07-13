from datetime import UTC, date, datetime
from typing import Any, cast

import pytest
from fastapi import HTTPException

from api.models.credentials import StravaCredentials, WhoopCredentials
from api.services import ongoing_providers
from api.services.ongoing_tools import build_ongoing_tool_registry


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _StubDbSession:
    pass


@pytest.mark.asyncio
async def test_strava_provider_aggregates_training_load_history():
    provider = ongoing_providers.StravaProvider(db=cast("Any", _StubDbSession()), user_id="user-1")

    async def _fake_get_access_token() -> str:
        return "token"

    def _fake_list_activities_sync(*, access_token: str, after: int, before: int) -> list[dict]:
        _ = (access_token, after, before)
        return [
            {
                "id": 1,
                "sport_type": "Run",
                "start_date_local": "2026-03-05T07:00:00Z",
                "distance": 10000,
                "moving_time": 3600,
                "relative_effort": 65,
            },
            {
                "id": 2,
                "sport_type": "Ride",
                "start_date_local": "2026-03-05T15:00:00Z",
                "distance": 30000,
                "moving_time": 5400,
                "suffer_score": 40,
            },
        ]

    provider._get_access_token = _fake_get_access_token  # type: ignore[method-assign]
    provider._list_activities_sync = _fake_list_activities_sync  # type: ignore[method-assign]

    payload = await provider.get_training_load_history(days=7)

    assert payload == [
        {
            "date": "2026-03-05",
            "activity_count": 2,
            "relative_effort_total": 65.0,
            "suffer_score_total": 40.0,
            "moving_time_minutes_total": 150.0,
            "distance_m_total": 40000.0,
            "load_type": "strava_relative_effort",
            "load_value": 65.0,
        }
    ]


@pytest.mark.asyncio
async def test_strava_provider_paginates_recent_activities(monkeypatch):
    provider = ongoing_providers.StravaProvider(db=cast("Any", _StubDbSession()), user_id="user-1")

    async def _fake_get_access_token() -> str:
        return "token"

    provider._get_access_token = _fake_get_access_token  # type: ignore[method-assign]

    class _FakeClient:
        def __init__(self):
            self.calls: list[int] = []

        def list_activities(self, *, page: int, per_page: int, after: int, before: int) -> list[dict]:
            _ = (per_page, after, before)
            self.calls.append(page)
            if page == 1:
                return [{"id": page * 1000 + idx, "sport_type": "Run"} for idx in range(100)]
            if page == 2:
                return [{"id": page * 1000 + idx, "sport_type": "Run"} for idx in range(25)]
            return []

        def close(self) -> None:
            return None

    fake_client = _FakeClient()
    monkeypatch.setattr(ongoing_providers, "StravaApiClient", lambda access_token: fake_client)
    activities = await provider.get_recent_activities(date(2026, 3, 1), date(2026, 3, 7))

    assert len(activities) == 125
    assert fake_client.calls == [1, 2]


@pytest.mark.asyncio
async def test_build_ongoing_tool_registry_is_provider_free():
    async with build_ongoing_tool_registry(
        cast("Any", object()),
        user_id="user-1",
        require_training_provider=False,
    ) as registry:
        snapshot = registry.get_observability_snapshot()
        assert snapshot["provider"]["training_providers"] == {}

    with pytest.raises(HTTPException) as exc:
        async with build_ongoing_tool_registry(
            cast("Any", object()),
            user_id="user-1",
            require_training_provider=True,
        ):
            raise AssertionError("Should not enter context when a provider is required and none are connected")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_whoop_provider_caches_access_token_failure(monkeypatch):
    provider = ongoing_providers.WhoopProvider(db=cast("Any", _StubDbSession()), user_id="user-1")
    token_calls = 0

    async def _fake_ensure_valid_access_token(_db, *, user_id):
        nonlocal token_calls
        _ = user_id
        token_calls += 1
        raise HTTPException(status_code=401, detail="WHOOP connection expired. Please reconnect WHOOP.")

    monkeypatch.setattr(ongoing_providers, "ensure_valid_access_token", _fake_ensure_valid_access_token)

    with pytest.raises(HTTPException) as first_exc:
        await provider.get_training_load_history(days=7)
    with pytest.raises(HTTPException) as second_exc:
        await provider.get_recent_activities(date(2026, 3, 1), date(2026, 3, 2))

    assert first_exc.value.status_code == 401
    assert second_exc.value.status_code == 401
    assert token_calls == 1


@pytest.mark.asyncio
async def test_build_ongoing_strava_provider_returns_strava_provider():
    class _Db:
        async def execute(self, statement):
            assert "FROM strava_credentials" in str(statement)
            return _ScalarResult(
                StravaCredentials(
                    user_id="user-1",
                    encrypted_access_token=b"access-token",
                    encrypted_refresh_token=b"refresh-token",
                    expires_at=datetime(2026, 3, 22, tzinfo=UTC),
                    scope="activity:read_all",
                    strava_athlete_id=4242,
                )
            )

    provider = await ongoing_providers.build_ongoing_strava_provider(cast("Any", _Db()), user_id="user-1")

    assert isinstance(provider, ongoing_providers.StravaProvider)


@pytest.mark.asyncio
async def test_build_ongoing_whoop_provider_returns_whoop_provider():
    class _Db:
        async def execute(self, statement):
            assert "FROM whoop_credentials" in str(statement)
            return _ScalarResult(
                WhoopCredentials(
                    user_id="user-1",
                    encrypted_access_token=b"access-token",
                    encrypted_refresh_token=b"refresh-token",
                    expires_at=datetime(2026, 3, 22, tzinfo=UTC),
                    scope="offline",
                    whoop_user_id=42,
                )
            )

    provider = await ongoing_providers.build_ongoing_whoop_provider(cast("Any", _Db()), user_id="user-1")

    assert isinstance(provider, ongoing_providers.WhoopProvider)
