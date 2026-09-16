from __future__ import annotations

from datetime import datetime
from enum import Enum

from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
from langchain_core.messages import ToolCall
from pydantic import BaseModel, ConfigDict, Field

from services.ai.head_coach.run_profiles import HeadCoachRunProfile
from services.ai.head_coach.schemas import RunProfileName


class LifecyclePhase(str, Enum):
    UNDERSTANDING_CONTEXT = "understanding_context"
    DESIGNING_STRATEGY = "designing_strategy"
    BUILDING_EXECUTION_BLOCK = "building_execution_block"
    REVIEWING_CONSTRAINTS = "reviewing_constraints"
    AWAITING_INPUT = "awaiting_input"
    SAVING_PLAN = "saving_plan"
    COMPLETED = "completed"
    FAILED = "failed"


class HeadCoachLifecycleEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase: LifecyclePhase
    run_id: str = Field(min_length=1, max_length=200)
    profile_name: RunProfileName
    occurred_at: datetime
    artifact_ids: list[str] = Field(default_factory=list)
    model_calls: int | None = Field(default=None, ge=0)
    tool_calls: int | None = Field(default=None, ge=0)
    tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0.0)


def build_lifecycle_event(
    *,
    phase: LifecyclePhase,
    run_id: str,
    profile_name: RunProfileName | str,
    occurred_at: datetime,
    artifact_ids: list[str] | None = None,
) -> HeadCoachLifecycleEvent:
    return HeadCoachLifecycleEvent(
        phase=phase,
        run_id=run_id,
        profile_name=RunProfileName(profile_name),
        occurred_at=occurred_at,
        artifact_ids=artifact_ids or [],
    )


class ApplicationToolCallLimitMiddleware(ToolCallLimitMiddleware):
    """Count application calls while excluding the registered response envelope.

    LangChain's ToolStrategy encodes the final typed answer as a tool call. It
    must not consume the execution budget, especially for zero-tool memory and
    presentation profiles. ModelCallLimitMiddleware still bounds answer retries.
    """

    def __init__(self, *, run_limit: int, response_tool_names: frozenset[str]):
        super().__init__(run_limit=run_limit, exit_behavior="error")
        self.response_tool_names = response_tool_names

    def _matches_tool_filter(self, tool_call: ToolCall) -> bool:
        # This LangChain extension point is exercised through create_agent in
        # our regression tests so dependency upgrades cannot silently bypass it.
        return tool_call["name"] not in self.response_tool_names


def build_head_coach_middleware(
    profile: HeadCoachRunProfile,
    *,
    response_tool_names: frozenset[str] = frozenset(),
) -> list:
    return [
        ModelCallLimitMiddleware(
            run_limit=profile.model_call_limit,
            exit_behavior="error",
        ),
        ApplicationToolCallLimitMiddleware(
            run_limit=profile.tool_call_limit,
            response_tool_names=response_tool_names,
        ),
        ModelRetryMiddleware(max_retries=2, on_failure="error"),
        ToolRetryMiddleware(max_retries=2, on_failure="error"),
    ]
