from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from services.ai.ai_settings import AgentRole
from services.ai.head_coach.schemas import RunProfileName, ToolCapability

ReasoningEffort = Literal["low", "medium", "high", "xhigh"]


class MutationAuthority(str, Enum):
    NONE = "none"
    PROPOSE = "propose"
    INITIAL_COMMIT = "initial_commit"


class HeadCoachRunProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: RunProfileName
    model_role: AgentRole
    reasoning_effort: ReasoningEffort
    mutation_authority: MutationAuthority
    allowed_tool_capabilities: frozenset[ToolCapability]
    enable_native_web_search: bool = False
    model_call_limit: int = Field(ge=1)
    tool_call_limit: int = Field(ge=0)


_LOCAL_PLAN_READS = frozenset(
    {
        ToolCapability.ATHLETE_PROFILE,
        ToolCapability.COMPETITIONS,
        ToolCapability.ACTIVE_PLANS,
        ToolCapability.CALENDAR,
        ToolCapability.COACH_HISTORY,
    }
)

_RUN_PROFILES = {
    RunProfileName.INITIAL_PLANNING: HeadCoachRunProfile(
        name=RunProfileName.INITIAL_PLANNING,
        model_role=AgentRole.HEAD_COACH,
        reasoning_effort="medium",
        mutation_authority=MutationAuthority.INITIAL_COMMIT,
        allowed_tool_capabilities=_LOCAL_PLAN_READS | {ToolCapability.SPECIALIST_CONSULTATION},
        model_call_limit=6,
        tool_call_limit=12,
    ),
    RunProfileName.MATERIAL_REPLANNING: HeadCoachRunProfile(
        name=RunProfileName.MATERIAL_REPLANNING,
        model_role=AgentRole.HEAD_COACH,
        reasoning_effort="xhigh",
        mutation_authority=MutationAuthority.PROPOSE,
        allowed_tool_capabilities=_LOCAL_PLAN_READS | {ToolCapability.SPECIALIST_CONSULTATION},
        model_call_limit=6,
        tool_call_limit=12,
    ),
    RunProfileName.COACH_TURN: HeadCoachRunProfile(
        name=RunProfileName.COACH_TURN,
        model_role=AgentRole.HEAD_COACH,
        reasoning_effort="medium",
        mutation_authority=MutationAuthority.PROPOSE,
        allowed_tool_capabilities=_LOCAL_PLAN_READS | {ToolCapability.SPECIALIST_CONSULTATION},
        model_call_limit=4,
        tool_call_limit=10,
    ),
    RunProfileName.WEEKLY_RECAP: HeadCoachRunProfile(
        name=RunProfileName.WEEKLY_RECAP,
        model_role=AgentRole.HEAD_COACH,
        reasoning_effort="high",
        mutation_authority=MutationAuthority.PROPOSE,
        allowed_tool_capabilities=_LOCAL_PLAN_READS,
        model_call_limit=3,
        tool_call_limit=8,
    ),
    RunProfileName.DAILY_ADAPTATION: HeadCoachRunProfile(
        name=RunProfileName.DAILY_ADAPTATION,
        model_role=AgentRole.HEAD_COACH,
        reasoning_effort="high",
        mutation_authority=MutationAuthority.PROPOSE,
        allowed_tool_capabilities=_LOCAL_PLAN_READS,
        model_call_limit=3,
        tool_call_limit=8,
    ),
    RunProfileName.MEMORY_EXTRACTION: HeadCoachRunProfile(
        name=RunProfileName.MEMORY_EXTRACTION,
        model_role=AgentRole.MEMORY,
        reasoning_effort="low",
        mutation_authority=MutationAuthority.NONE,
        allowed_tool_capabilities=frozenset({ToolCapability.COACH_HISTORY}),
        model_call_limit=1,
        tool_call_limit=0,
    ),
    RunProfileName.RESEARCH_SPECIALIST: HeadCoachRunProfile(
        name=RunProfileName.RESEARCH_SPECIALIST,
        model_role=AgentRole.SPECIALIST,
        reasoning_effort="xhigh",
        mutation_authority=MutationAuthority.NONE,
        allowed_tool_capabilities=frozenset({ToolCapability.WEB_RESEARCH}),
        enable_native_web_search=True,
        model_call_limit=4,
        tool_call_limit=8,
    ),
    RunProfileName.UI_COMPOSER: HeadCoachRunProfile(
        name=RunProfileName.UI_COMPOSER,
        model_role=AgentRole.UI_COMPOSER,
        reasoning_effort="low",
        mutation_authority=MutationAuthority.NONE,
        allowed_tool_capabilities=frozenset(),
        model_call_limit=2,
        tool_call_limit=0,
    ),
}


def get_run_profile(profile_name: RunProfileName | str) -> HeadCoachRunProfile:
    try:
        normalized_name = RunProfileName(profile_name)
        return _RUN_PROFILES[normalized_name]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Unsupported Head Coach run profile: {profile_name!r}") from exc
