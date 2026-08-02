from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from services.ai.head_coach.agent import build_head_coach_agent, invoke_head_coach_agent
from services.ai.head_coach.schemas import RunProfileName


class _ConfidenceScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: str = Field(..., min_length=1, max_length=120)
    confidence: float = Field(..., ge=0.0, le=1.0)


class _TransientStateNote(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    topic: str = Field(..., min_length=1, max_length=120)
    status: str = Field(default="unknown", min_length=1, max_length=40)
    summary: str = Field(..., min_length=1, max_length=500)
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None


class AthleteModelSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    training_preferences: list[str] = Field(default_factory=list)
    schedule_constraints: list[str] = Field(default_factory=list)
    response_patterns: list[str] = Field(default_factory=list)
    injury_risk_notes: list[str] = Field(default_factory=list)
    transient_state_notes: list[_TransientStateNote] = Field(default_factory=list)
    motivation_style: str | None = None
    goal_state: str | None = None
    confidence_by_field: list[_ConfidenceScore] = Field(default_factory=list)
    memory_summary: str = Field(..., min_length=1, max_length=2500)


ATHLETE_MODEL_SYSTEM_PROMPT = """You maintain a compact long-term athlete model for a coaching thread.

Rules:
- Summarize only evidence-backed behavior from the provided events.
- Keep memory_summary concise and concrete.
- Track short-lived states (illness, acute pain, temporary constraints) in transient_state_notes.
- For each transient state, keep status and observed timestamps using event created_at evidence.
- Resolve or remove transient states once evidence indicates they no longer apply.
- confidence_by_field entries must include field_name and confidence in [0.0, 1.0].
- Do not hallucinate injuries/goals; if uncertain, keep fields empty.
"""


async def summarize_athlete_model(
    *,
    previous_model: dict,
    recent_events: list[dict],
    invoke_config: dict[str, Any] | None = None,
) -> AthleteModelSummary:
    agent = build_head_coach_agent(
        profile_name=RunProfileName.MEMORY_EXTRACTION,
        response_schema=AthleteModelSummary,
        tools=[],
        task_instructions=ATHLETE_MODEL_SYSTEM_PROMPT,
        name="athlete_model_summary",
    )
    return await invoke_head_coach_agent(
        agent=agent,
        user_prompt=json.dumps(
            {"previous_model": previous_model, "recent_events": recent_events},
            ensure_ascii=False,
            default=str,
        ),
        response_schema=AthleteModelSummary,
        invoke_config=invoke_config
        or {
            "run_name": "athlete_model_summary",
            "tags": ["agent:athlete_model", "feature:coach_memory"],
        },
    )
