from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from services.ai.ai_settings import AgentRole
from services.ai.model_config import ModelSelector
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff
from services.ai.utils.structured_output import coerce_structured_output

logger = logging.getLogger(__name__)

DIGEST_SYSTEM_PROMPT = """\
You are a sports science data analyst preparing a concise briefing for a head coach.

Given the athlete's raw connected-provider signals and their message, produce a coaching-relevant digest.

Rules:
- Focus on what matters for the athlete's question or situation.
- Include key metrics by name and value (HRV, RHR, sleep score, ACWR, load, etc.).
- Flag anything the coach should pay attention to (below-baseline HRV, high load spike, poor sleep trend, injury risk).
- Summarize activity patterns (volume, intensity distribution, discipline mix) rather than listing each activity.
- Omit raw lap splits, per-lap HR, individual weather entries, zone boundary values, and respiration/stress metrics unless directly relevant to the athlete's question.
- Be concise: the coach will use this briefing to craft personalized advice.
"""


class SignalDigest(BaseModel):
    training_narrative: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Coaching-relevant summary of the athlete's recent training, recovery, and status. Tailored to the context of the athlete's message.",
    )
    key_metrics: dict[str, float | int | str | None] = Field(
        default_factory=dict,
        description="Extracted numeric/categorical metrics the coach needs (e.g. hrv_last_night, rhr, acwr, sleep_score, sessions_7d).",
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Notable signals for coach attention (e.g. hrv_below_baseline, high_volume_week, poor_sleep_trend).",
    )


def _build_digest_prompt(
    *,
    activities: list[dict],
    recovery: dict,
    load: list[dict],
    weekly_plan: dict,
    competitions: list[dict],
    user_message: str,
    athlete_model: dict,
) -> str:
    sections = [f"Athlete message:\n{user_message}"]

    if athlete_model:
        sections.append(f"Athlete model:\n{json.dumps(athlete_model, ensure_ascii=False, default=str)}")

    if activities:
        sections.append(f"Recent activities ({len(activities)} total):\n{json.dumps(activities, ensure_ascii=False, default=str)}")

    if recovery:
        sections.append(f"Recovery & readiness signals:\n{json.dumps(recovery, ensure_ascii=False, default=str)}")

    if load:
        sections.append(f"Training load history ({len(load)} days):\n{json.dumps(load, ensure_ascii=False, default=str)}")

    if weekly_plan:
        sections.append(f"Current weekly plan:\n{json.dumps(weekly_plan, ensure_ascii=False, default=str)}")

    if competitions:
        sections.append(f"Upcoming competitions:\n{json.dumps(competitions, ensure_ascii=False, default=str)}")

    return "\n\n".join(sections)


async def run_signal_digest(
    *,
    activities: list[dict],
    recovery: dict,
    load: list[dict],
    weekly_plan: dict,
    competitions: list[dict],
    user_message: str,
    athlete_model: dict,
) -> SignalDigest:
    llm = ModelSelector.get_llm(AgentRole.COACH_TRIAGE)
    llm_structured = llm.with_structured_output(SignalDigest, method="json_schema")

    user_prompt = _build_digest_prompt(
        activities=activities,
        recovery=recovery,
        load=load,
        weekly_plan=weekly_plan,
        competitions=competitions,
        user_message=user_message,
        athlete_model=athlete_model,
    )

    async def call_digest():
        return await llm_structured.ainvoke(
            [
                {"role": "system", "content": DIGEST_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            config={
                "run_name": "signal_digest",
                "tags": ["agent:signal_digest", "feature:coach_turn"],
            },
        )

    logger.info("Running signal digest agent")
    response = await retry_with_backoff(call_digest, AI_ANALYSIS_CONFIG, "Signal Digest")
    return coerce_structured_output(response, SignalDigest)
