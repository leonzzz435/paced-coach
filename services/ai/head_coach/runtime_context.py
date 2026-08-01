from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from services.ai.head_coach.run_profiles import HeadCoachRunProfile
from services.ai.head_coach.schemas import HeadCoachBrief, ToolCapability


class StatusWriter(Protocol):
    async def __call__(self, event: dict[str, object]) -> None: ...


@dataclass(frozen=True, slots=True)
class HeadCoachRuntimeContext:
    """Invocation-only dependencies that must never be stored in graph state."""

    owner_id: str
    database: object
    tool_registry: object
    available_capabilities: frozenset[ToolCapability]
    status_writer: StatusWriter | None = None


def build_head_coach_brief(
    *,
    owner_id: str,
    run_id: str,
    profile: HeadCoachRunProfile,
    context_pack: dict[str, Any],
) -> HeadCoachBrief:
    raw_as_of = context_pack.get("now_utc")
    if not isinstance(raw_as_of, str):
        raise ValueError("Head Coach context requires a string now_utc value")
    try:
        as_of_utc = datetime.fromisoformat(raw_as_of)
    except ValueError as exc:
        raise ValueError("Head Coach context now_utc must be ISO 8601") from exc
    if as_of_utc.tzinfo is None:
        raise ValueError("Head Coach context now_utc must include a timezone")

    return HeadCoachBrief(
        owner_id=owner_id,
        run_id=run_id,
        profile_name=profile.name,
        as_of_utc=as_of_utc,
        local_context=context_pack,
    )
