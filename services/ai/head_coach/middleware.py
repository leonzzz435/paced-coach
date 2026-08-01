from __future__ import annotations

from datetime import datetime
from enum import Enum

from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
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


def build_head_coach_middleware(profile: HeadCoachRunProfile) -> list:
    return [
        ModelCallLimitMiddleware(
            run_limit=profile.model_call_limit,
            exit_behavior="error",
        ),
        ToolCallLimitMiddleware(
            run_limit=profile.tool_call_limit,
            exit_behavior="error",
        ),
        ModelRetryMiddleware(max_retries=2, on_failure="error"),
        ToolRetryMiddleware(max_retries=2, on_failure="error"),
    ]
