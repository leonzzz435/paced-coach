from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

ATTEMPT_STARTED_AT_KEY = "_head_coach_attempt_started_at"


def with_attempt_started_at(config: dict[str, Any], *, started_at: datetime) -> dict[str, Any]:
    value = started_at if started_at.tzinfo is not None else started_at.replace(tzinfo=UTC)
    return {**config, ATTEMPT_STARTED_AT_KEY: value.astimezone(UTC).isoformat()}


def get_attempt_started_at(config: object, *, fallback: datetime) -> datetime:
    if isinstance(config, dict):
        raw_value = config.get(ATTEMPT_STARTED_AT_KEY)
        if isinstance(raw_value, str):
            try:
                parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            except ValueError:
                parsed = None
            if parsed is not None and parsed.tzinfo is not None:
                return parsed.astimezone(UTC)
    return fallback if fallback.tzinfo is not None else fallback.replace(tzinfo=UTC)
