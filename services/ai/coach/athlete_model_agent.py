from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from services.ai.ai_settings import AgentRole
from services.ai.model_config import ModelSelector
from services.ai.utils.retry_handler import QUICK_RETRY_CONFIG, retry_with_backoff
from services.ai.utils.structured_output import coerce_structured_output


class _ConfidenceScore(BaseModel):
    field_name: str = Field(..., min_length=1, max_length=120)
    confidence: float = Field(..., ge=0.0, le=1.0)


class _TransientStateNote(BaseModel):
    topic: str = Field(..., min_length=1, max_length=120)
    status: str = Field(default="unknown", min_length=1, max_length=40)
    summary: str = Field(..., min_length=1, max_length=500)
    first_observed_at: str | None = Field(default=None, max_length=64)
    last_observed_at: str | None = Field(default=None, max_length=64)


class AthleteModelSummary(BaseModel):
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


def _normalize_timestamp(raw_value: object) -> str | None:
    if isinstance(raw_value, datetime):
        parsed = raw_value
    elif isinstance(raw_value, str):
        try:
            parsed = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _normalize_transient_state_notes(raw_notes: object) -> list[dict[str, str | None]]:
    if not isinstance(raw_notes, list):
        return []
    normalized: list[dict[str, str | None]] = []
    for note in raw_notes:
        if not isinstance(note, dict):
            continue
        topic = str(note.get("topic", "")).strip()
        summary = str(note.get("summary", "")).strip()
        if not topic or not summary:
            continue
        status = str(note.get("status", "unknown")).strip().lower() or "unknown"
        normalized.append(
            {
                "topic": topic,
                "status": status,
                "summary": summary,
                "first_observed_at": _normalize_timestamp(note.get("first_observed_at")),
                "last_observed_at": _normalize_timestamp(note.get("last_observed_at")),
            }
        )
    return normalized[:12]


async def summarize_athlete_model(
    *,
    previous_model: dict,
    recent_events: list[dict],
    invoke_config: dict[str, Any] | None = None,
) -> AthleteModelSummary:
    llm = ModelSelector.get_llm(AgentRole.COACH)
    llm_with_structure = llm.with_structured_output(AthleteModelSummary, method="json_schema")

    prompt = {
        "previous_model": previous_model,
        "recent_events": recent_events,
    }

    async def call_summary():
        return await llm_with_structure.ainvoke(
            [
                {"role": "system", "content": ATHLETE_MODEL_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            config=invoke_config
            or {
                "run_name": "athlete_model_summary",
                "tags": ["agent:athlete_model", "feature:coach_memory"],
            },
        )

    response = await retry_with_backoff(call_summary, QUICK_RETRY_CONFIG, "Athlete Model Summary")
    payload = coerce_structured_output(response, AthleteModelSummary).model_dump(mode="json")
    payload["transient_state_notes"] = _normalize_transient_state_notes(payload.get("transient_state_notes"))
    confidence_rows = payload.get("confidence_by_field") or []
    normalized_confidence: list[dict[str, float | str]] = []
    for row in confidence_rows:
        if not isinstance(row, dict):
            continue
        field_name = str(row.get("field_name", "")).strip()
        if not field_name:
            continue
        raw_confidence = row.get("confidence")
        if raw_confidence is None:
            continue
        try:
            confidence_value = float(raw_confidence)
        except (TypeError, ValueError):
            continue
        normalized_confidence.append(
            {
                "field_name": field_name,
                "confidence": min(1.0, max(0.0, confidence_value)),
            }
        )
    payload["confidence_by_field"] = normalized_confidence
    return AthleteModelSummary.model_validate(payload)
