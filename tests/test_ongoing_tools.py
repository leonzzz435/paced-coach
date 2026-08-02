import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.ongoing_tools import OngoingToolRegistry


@pytest.mark.asyncio
async def test_get_athlete_profile_includes_memory_freshness_metadata():
    updated_at = "2026-02-20T12:00:00+00:00"
    user_row = MagicMock()
    user_row.scalar_one_or_none.return_value = SimpleNamespace(
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
    profile_row = MagicMock()
    profile_row.scalar_one_or_none.return_value = {
        "experience": "intermediate",
        "availability": ["Monday", "Thursday"],
    }
    db = AsyncMock()
    db.execute.side_effect = [user_row, profile_row]
    registry = OngoingToolRegistry(db=db, user_id=uuid.uuid4())

    payload = await registry.get_athlete_profile()

    assert payload["memory_summary"] == "Athlete responds well to short cues."
    assert payload["profile"]["experience"] == "intermediate"
    assert payload["athlete_model"]["goal_state"] == "build"
    assert payload["transient_state_notes"][0]["topic"] == "illness"
    assert payload["memory_updated_at"] == updated_at
    assert payload["memory_age_days"] == max((datetime.now(UTC) - datetime.fromisoformat(updated_at)).days, 0)


def test_registry_exposes_only_athlete_owned_local_sources():
    registry = OngoingToolRegistry(db=AsyncMock(), user_id=uuid.uuid4())

    assert {tool.name for tool in registry.create_langchain_tools()} == {
        "get_athlete_profile",
        "get_current_season_plan",
        "get_current_weekly_plan",
        "get_upcoming_competitions",
    }
    assert registry.get_observability_snapshot()["source_of_truth"] == "local_athlete_owned"


def test_registry_rejects_removed_provider_tool_names():
    registry = OngoingToolRegistry(db=AsyncMock(), user_id=uuid.uuid4())

    with pytest.raises(ValueError, match="Unknown ongoing tool names"):
        registry.create_langchain_tools(allowed_tool_names={"get_recent_activities"})
