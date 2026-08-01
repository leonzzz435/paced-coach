from typing import Any, cast

import pytest

from api.services.ongoing_tools import OngoingToolRegistry
from services.ai.head_coach.run_profiles import RunProfileName, get_run_profile
from services.ai.head_coach.tool_policy import (
    ToolAccess,
    ToolCapability,
    select_tool_names,
    tool_specs_for_names,
)

LOCAL_CAPABILITIES = frozenset(
    {
        ToolCapability.ATHLETE_PROFILE,
        ToolCapability.COMPETITIONS,
        ToolCapability.ACTIVE_PLANS,
    }
)


def test_provider_free_initial_planning_exposes_only_local_read_tools():
    profile = get_run_profile(RunProfileName.INITIAL_PLANNING)
    selected = select_tool_names(
        profile,
        available_capabilities=LOCAL_CAPABILITIES,
        registered_tool_names=OngoingToolRegistry.registered_tool_names(),
    )

    assert selected == {
        "get_athlete_profile",
        "get_current_season_plan",
        "get_current_weekly_plan",
        "get_upcoming_competitions",
    }
    assert all(spec.access is ToolAccess.READ for spec in tool_specs_for_names(selected))


def test_coach_turn_exposes_only_local_sources():
    profile = get_run_profile(RunProfileName.COACH_TURN)
    selected = select_tool_names(
        profile,
        available_capabilities=LOCAL_CAPABILITIES,
        registered_tool_names=OngoingToolRegistry.registered_tool_names(),
    )

    assert selected == OngoingToolRegistry.registered_tool_names()


def test_unclassified_registry_tool_fails_closed():
    profile = get_run_profile(RunProfileName.COACH_TURN)

    with pytest.raises(ValueError, match="Unclassified Head Coach tools"):
        select_tool_names(
            profile,
            available_capabilities=LOCAL_CAPABILITIES,
            registered_tool_names={"surprise_write_tool"},
        )


def test_registry_filters_constructed_tools_by_policy():
    registry = OngoingToolRegistry(
        db=cast("Any", object()),
        user_id="owner-1",
    )

    tools = registry.create_langchain_tools(allowed_tool_names={"get_athlete_profile", "get_current_weekly_plan"})

    assert {cast("Any", tool).name for tool in tools} == {
        "get_athlete_profile",
        "get_current_weekly_plan",
    }
