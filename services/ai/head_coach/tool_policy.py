from __future__ import annotations

from collections.abc import Collection
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from services.ai.head_coach.run_profiles import HeadCoachRunProfile
from services.ai.head_coach.schemas import ToolCapability


class ToolAccess(str, Enum):
    READ = "read"
    PROPOSE = "propose"
    WRITE = "write"


class HeadCoachToolSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    capability: ToolCapability
    access: ToolAccess


class HeadCoachToolRegistry(Protocol):
    @classmethod
    def registered_tool_names(cls) -> set[str]: ...

    def create_langchain_tools(self, *, allowed_tool_names: Collection[str] | None = None) -> list: ...

    def get_observability_snapshot(self) -> dict: ...


_TOOL_CATALOG = {
    "get_athlete_profile": HeadCoachToolSpec(
        name="get_athlete_profile", capability=ToolCapability.ATHLETE_PROFILE, access=ToolAccess.READ
    ),
    "get_upcoming_competitions": HeadCoachToolSpec(
        name="get_upcoming_competitions", capability=ToolCapability.COMPETITIONS, access=ToolAccess.READ
    ),
    "get_current_weekly_plan": HeadCoachToolSpec(
        name="get_current_weekly_plan", capability=ToolCapability.ACTIVE_PLANS, access=ToolAccess.READ
    ),
    "get_current_season_plan": HeadCoachToolSpec(
        name="get_current_season_plan", capability=ToolCapability.ACTIVE_PLANS, access=ToolAccess.READ
    ),
}

_LOCAL_RUNTIME_CAPABILITIES = frozenset(
    {
        ToolCapability.ATHLETE_PROFILE,
        ToolCapability.COMPETITIONS,
        ToolCapability.ACTIVE_PLANS,
        ToolCapability.CALENDAR,
        ToolCapability.COACH_HISTORY,
    }
)


def select_tool_names(
    profile: HeadCoachRunProfile,
    *,
    available_capabilities: frozenset[ToolCapability] | set[ToolCapability],
    registered_tool_names: set[str],
) -> set[str]:
    unknown_tools = registered_tool_names - _TOOL_CATALOG.keys()
    if unknown_tools:
        raise ValueError(f"Unclassified Head Coach tools: {sorted(unknown_tools)!r}")

    effective_capabilities = profile.allowed_tool_capabilities & available_capabilities
    return {name for name in registered_tool_names if _TOOL_CATALOG[name].capability in effective_capabilities}


def tool_specs_for_names(names: set[str]) -> list[HeadCoachToolSpec]:
    unknown_tools = names - _TOOL_CATALOG.keys()
    if unknown_tools:
        raise ValueError(f"Unclassified Head Coach tools: {sorted(unknown_tools)!r}")
    return [_TOOL_CATALOG[name] for name in sorted(names)]


def build_profile_tools(
    profile: HeadCoachRunProfile,
    *,
    tool_registry: HeadCoachToolRegistry | None,
) -> list:
    if tool_registry is None:
        return []

    capabilities = set(_LOCAL_RUNTIME_CAPABILITIES)
    selected_names = select_tool_names(
        profile,
        available_capabilities=capabilities,
        registered_tool_names=tool_registry.registered_tool_names(),
    )
    return tool_registry.create_langchain_tools(allowed_tool_names=selected_names)
