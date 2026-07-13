import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from api.services.ongoing_tools import OngoingToolRegistry


@pytest.mark.asyncio
async def test_get_current_analysis_returns_rendered_payload_when_present():
    user_id = uuid.uuid4()
    active = SimpleNamespace(
        analysis_data={"type": "analysis", "schema_version": 2, "analysis_id": "a1"},
        version=4,
        updated_at=datetime(2026, 2, 27, 12, 0, tzinfo=UTC),
    )
    row = MagicMock()
    row.scalar_one_or_none.return_value = active
    db = AsyncMock()
    db.execute.return_value = row
    registry = OngoingToolRegistry(db=db, user_id=user_id, providers={})

    payload = await registry.get_current_analysis()

    assert payload["analysis_id"] == "a1"
    assert payload["version"] == 4
    assert payload["updated_at"] == "2026-02-27T12:00:00+00:00"


@pytest.mark.asyncio
async def test_get_current_analysis_returns_empty_payload_when_missing():
    user_id = uuid.uuid4()
    row = MagicMock()
    row.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute.return_value = row
    registry = OngoingToolRegistry(db=db, user_id=user_id, providers={})

    payload = await registry.get_current_analysis()

    assert payload == {}


@pytest.mark.asyncio
async def test_get_athlete_profile_includes_memory_freshness_metadata():
    user_id = uuid.uuid4()
    updated_at = "2026-02-20T12:00:00+00:00"
    row = MagicMock()
    row.scalar_one_or_none.return_value = SimpleNamespace(
        memory_summary="Athlete responds well to short cues.",
        athlete_model={
            "goal_state": "build",
            "transient_state_notes": [
                {
                    "topic": "illness",
                    "status": "active",
                    "summary": "Sore throat and low sleep quality this week.",
                    "first_observed_at": "2026-02-19T06:30:00+00:00",
                    "last_observed_at": "2026-02-20T06:30:00+00:00",
                }
            ],
            "_meta": {"updated_at": updated_at},
        },
    )
    db = AsyncMock()
    db.execute.return_value = row
    registry = OngoingToolRegistry(db=db, user_id=user_id, providers={})

    payload = await registry.get_athlete_profile()

    assert payload["memory_summary"] == "Athlete responds well to short cues."
    assert payload["athlete_model"]["goal_state"] == "build"
    assert payload["transient_state_notes"][0]["topic"] == "illness"
    assert payload["transient_state_notes"][0]["status"] == "active"
    assert payload["memory_updated_at"] == updated_at
    expected_age = max((datetime.now(UTC) - datetime.fromisoformat(updated_at)).days, 0)
    assert payload["memory_age_days"] == expected_age


def test_create_langchain_tools_exposes_context_retrieval_tools():
    registry = OngoingToolRegistry(db=AsyncMock(), user_id=uuid.uuid4(), providers={})

    tool_names = {tool.name for tool in registry.create_langchain_tools()}

    assert "get_current_analysis" in tool_names
    assert "get_current_weekly_plan" in tool_names
    assert "get_current_season_plan" in tool_names
    assert "get_expert_output" in tool_names
    assert "get_athlete_profile" in tool_names


def test_get_observability_snapshot_is_provider_free():
    registry = OngoingToolRegistry(db=AsyncMock(), user_id=uuid.uuid4(), providers={})

    snapshot = registry.get_observability_snapshot()

    providers = snapshot["provider"]["training_providers"]
    assert providers == {}
    assert snapshot["evidence_profile"]["connected_mode"] == "none"
    assert snapshot["evidence_profile"]["claims_policy"]["can_make_readiness_claims"] is False


class _GoodProvider:
    async def get_recent_activities(self, date_from: date, date_to: date, sport_filters=None) -> list[dict]:
        _ = (date_from, date_to, sport_filters)
        return [
            {
                "activity_id": 123,
                "activity_type": "cycling",
                "activity_name": "Aerobic ride",
                "start_time": "2026-03-06T07:00:00Z",
            }
        ]

    async def get_training_load_history(self, days: int) -> list[dict]:
        _ = days
        return [{"date": "2026-03-06", "daily_load": 88}]

    async def get_recovery_readiness_signals(self, days: int) -> dict:
        _ = days
        return {"recoveries": [{"score": 78}]}

    async def get_activity_detail(self, activity_id: int | str) -> dict | None:
        _ = activity_id
        return None


class _ExpiredWhoopProvider:
    async def get_recent_activities(self, date_from: date, date_to: date, sport_filters=None) -> list[dict]:
        _ = (date_from, date_to, sport_filters)
        raise HTTPException(status_code=401, detail="WHOOP connection expired. Please reconnect WHOOP.")

    async def get_training_load_history(self, days: int) -> list[dict]:
        _ = days
        raise HTTPException(status_code=401, detail="WHOOP connection expired. Please reconnect WHOOP.")

    async def get_recovery_readiness_signals(self, days: int) -> dict:
        _ = days
        raise HTTPException(status_code=401, detail="WHOOP connection expired. Please reconnect WHOOP.")

    async def get_activity_detail(self, activity_id: int | str) -> dict | None:
        _ = activity_id
        raise HTTPException(status_code=401, detail="WHOOP connection expired. Please reconnect WHOOP.")


@pytest.mark.asyncio
async def test_training_snapshot_degrades_when_whoop_expires(monkeypatch):
    registry = OngoingToolRegistry(
        db=AsyncMock(),
        user_id=uuid.uuid4(),
        providers={
            "strava": _GoodProvider(),
            "whoop": _ExpiredWhoopProvider(),
        },
    )

    registry.get_current_weekly_plan = AsyncMock(return_value={"weeks": []})  # type: ignore[method-assign]
    registry.get_upcoming_competitions = AsyncMock(return_value=[])  # type: ignore[method-assign]

    payload = await registry.get_training_snapshot()

    assert payload["sessions_7d"] == 1
    assert payload["sessions_7d_by_source"] == {"strava": 1}
    assert payload["provider_status"]["strava"]["available"] is True
    assert payload["provider_status"]["whoop"]["available"] is False
    assert payload["provider_status"]["whoop"]["status_code"] == 401
    assert "expired" in str(payload["provider_status"]["whoop"]["last_error"]).lower()
    assert payload["evidence_profile"]["connected_mode"] == "strava_only"
    assert payload["evidence_profile"]["dimensions"]["readiness_guidance"]["availability"] == "proxy_only"
    assert payload["evidence_profile"]["claims_policy"]["can_make_activity_completeness_claims"] is True
    assert payload["evidence_profile"]["claims_policy"]["can_make_readiness_claims"] is False


@pytest.mark.asyncio
async def test_recovery_signals_degrade_when_whoop_expires():
    registry = OngoingToolRegistry(
        db=AsyncMock(),
        user_id=uuid.uuid4(),
        providers={
            "strava": _GoodProvider(),
            "whoop": _ExpiredWhoopProvider(),
        },
    )

    payload = await registry.get_recovery_readiness_signals(days=7)

    assert set(payload["sources"].keys()) == {"strava"}
    assert payload["provider_status"]["whoop"]["available"] is False
    assert payload["provider_status"]["whoop"]["status_code"] == 401
    assert payload["evidence_profile"]["connected_mode"] == "strava_only"
    assert payload["evidence_profile"]["claims_policy"]["should_frame_guidance_as_proxy_based"] is True
