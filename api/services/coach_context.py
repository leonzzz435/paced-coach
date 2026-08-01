from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.coach_event import CoachEvent
from api.models.coach_thread import CoachThread
from api.models.user import User
from api.services.coach_event_store import EVENT_TOOL_TRACE, safe_event_payload
from api.services.coach_memory_metadata import derive_memory_freshness, extract_transient_state_notes
from api.services.ongoing_tools import OngoingToolRegistry, build_ongoing_tool_registry, nearest_competition_days
from services.ai.head_coach.run_profiles import RunProfileName, get_run_profile
from services.ai.head_coach.runtime_context import build_head_coach_brief
from services.ai.head_coach.schemas import HeadCoachBrief

logger = logging.getLogger(__name__)

_SALIENT_KEYWORDS = {
    "injury",
    "injured",
    "pain",
    "ache",
    "sick",
    "ill",
    "fever",
    "medication",
    "race goal",
    "goal change",
}


def package_head_coach_brief(
    *,
    owner_id: str,
    run_id: str,
    profile_name: RunProfileName | str,
    context_pack: dict,
) -> HeadCoachBrief:
    """Wrap the existing complete context pack in the shared serializable contract."""
    return build_head_coach_brief(
        owner_id=owner_id,
        run_id=run_id,
        profile=get_run_profile(profile_name),
        context_pack=context_pack,
    )


def _behavior_patterns(events: list[CoachEvent]) -> dict:
    rejected = 0
    accepted = 0
    recap_responses = 0
    athlete_messages = 0
    for event in events:
        if event.event_type == "proposal_rejected":
            rejected += 1
        elif event.event_type == "proposal_accepted":
            accepted += 1
        elif event.event_type == "recap_response":
            recap_responses += 1
        elif event.event_type == "user_message":
            athlete_messages += 1
    return {
        "proposal_acceptance_ratio": (accepted / (accepted + rejected)) if (accepted + rejected) else None,
        "recap_response_count": recap_responses,
        "athlete_message_count": athlete_messages,
    }


def _contains_salient_text(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in _SALIENT_KEYWORDS)


def is_salient_event(*, message: str, proposal_changed: bool) -> bool:
    return proposal_changed or _contains_salient_text(message)


def _serialize_plan_scalar(value: object) -> str | int | bool | None:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _summarize_v1_day(raw_day: dict) -> dict[str, object]:
    return {
        "day_id": _serialize_plan_scalar(raw_day.get("day_id")),
        "date": _serialize_plan_scalar(raw_day.get("date")),
        "day_label": _serialize_plan_scalar(raw_day.get("day_label")),
        "workout_title": _serialize_plan_scalar(raw_day.get("workout_title")),
        "focus_type": _serialize_plan_scalar(raw_day.get("focus_type")),
        "estimated_duration_min": raw_day.get("estimated_duration_min"),
        "estimated_intensity": _serialize_plan_scalar(raw_day.get("estimated_intensity")),
        "is_completed": raw_day.get("is_completed"),
    }


def _summarize_v3_day(raw_day: dict) -> dict[str, object]:
    raw_sessions = raw_day.get("sessions")
    return {
        "day_id": _serialize_plan_scalar(raw_day.get("day_id")),
        "date": _serialize_plan_scalar(raw_day.get("date")),
        "label": _serialize_plan_scalar(raw_day.get("label")),
        "focus_type": _serialize_plan_scalar(raw_day.get("focus_type")),
        "total_duration_min": raw_day.get("total_duration_min"),
        "intensity": _serialize_plan_scalar(raw_day.get("intensity")),
        "is_completed": raw_day.get("is_completed"),
        "sessions": [
            {
                "session_id": _serialize_plan_scalar(raw_session.get("session_id")),
                "title": _serialize_plan_scalar(raw_session.get("title")),
                "duration_min": raw_session.get("duration_min"),
                "intensity": _serialize_plan_scalar(raw_session.get("intensity")),
            }
            for raw_session in raw_sessions
            if isinstance(raw_session, dict)
        ]
        if isinstance(raw_sessions, list)
        else [],
    }


def _summarize_current_weekly_plan_identity(weekly_plan: dict | None) -> dict | None:
    if not isinstance(weekly_plan, dict):
        return None

    raw_weeks = weekly_plan.get("weeks")
    if not isinstance(raw_weeks, list) or not raw_weeks:
        return None

    schema_version = weekly_plan.get("schema_version", 1)
    if schema_version not in {1, 3}:
        return None

    weeks: list[dict[str, object]] = []
    for raw_week in raw_weeks:
        if not isinstance(raw_week, dict):
            continue
        raw_days = raw_week.get("days")
        summarized_days: list[dict[str, object]] = []
        if isinstance(raw_days, list):
            for raw_day in raw_days:
                if not isinstance(raw_day, dict):
                    continue
                summarize_day = _summarize_v3_day if schema_version == 3 else _summarize_v1_day
                summarized_days.append(summarize_day(raw_day))
        weeks.append(
            {
                "week_id": _serialize_plan_scalar(raw_week.get("week_id")),
                "title" if schema_version == 3 else "week_label": _serialize_plan_scalar(
                    raw_week.get("title" if schema_version == 3 else "week_label")
                ),
                "start_date": _serialize_plan_scalar(raw_week.get("start_date")),
                "end_date": _serialize_plan_scalar(raw_week.get("end_date")),
                "days": summarized_days,
            }
        )

    if not weeks:
        return None

    return {
        "schema_version": schema_version,
        "plan_id": _serialize_plan_scalar(weekly_plan.get("plan_id")),
        "version": weekly_plan.get("version"),
        "updated_at": _serialize_plan_scalar(weekly_plan.get("updated_at")),
        "weeks": weeks,
    }


def _serialize_recent_conversation_events(recent_events: list[CoachEvent]) -> list[dict]:
    return [
        {
            "seq": event.seq,
            "event_type": event.event_type,
            "actor": event.actor,
            "payload": safe_event_payload(event),
            "created_at": event.created_at.astimezone(UTC).isoformat(),
        }
        for event in recent_events
    ]


def _serialize_recent_tool_results(recent_events: list[CoachEvent]) -> list[dict]:
    serialized: list[dict] = []
    for event in recent_events:
        if event.event_type != EVENT_TOOL_TRACE:
            continue
        payload = safe_event_payload(event)
        serialized.append(
            {
                "seq": event.seq,
                "turn_seq_anchor": payload.get("turn_seq_anchor"),
                "tool_name": payload.get("tool_name"),
                "args": payload.get("args"),
                "result_preview": payload.get("result_preview"),
                "char_len": payload.get("char_len"),
                "truncated": payload.get("truncated"),
                "result_hash": payload.get("result_hash"),
                "created_at": event.created_at.astimezone(UTC).isoformat(),
            }
        )
    return serialized


async def _load_user_long_term_memory(db: AsyncSession, *, user_id: uuid.UUID) -> tuple[str, dict]:
    row = await db.execute(select(User).where(User.id == user_id))
    user_row = row.scalar_one_or_none()
    if user_row is None:
        return "", {}
    memory_summary = user_row.memory_summary or ""
    athlete_model = user_row.athlete_model or {}
    return memory_summary, athlete_model


def _build_tool_budget(recent_events: list[CoachEvent]) -> dict:
    tool_trace_events = [event for event in recent_events if event.event_type == EVENT_TOOL_TRACE]
    if not tool_trace_events:
        return {
            "tools_called_current_turn_pre_call": 0,
            "tools_called_last_turn": 0,
            "tools_called_prior_turns": 0,
        }

    anchors: list[int] = []
    for event in tool_trace_events:
        payload = safe_event_payload(event)
        anchor_value = payload.get("turn_seq_anchor")
        if isinstance(anchor_value, int):
            anchors.append(anchor_value)
    if not anchors:
        return {
            "tools_called_current_turn_pre_call": 0,
            "tools_called_last_turn": 0,
            "tools_called_prior_turns": len(tool_trace_events),
        }

    latest_anchor = max(anchors)
    tools_called_last_turn = 0
    for event in tool_trace_events:
        payload = safe_event_payload(event)
        anchor_value = payload.get("turn_seq_anchor")
        if isinstance(anchor_value, int) and anchor_value == latest_anchor:
            tools_called_last_turn += 1
    return {
        "tools_called_current_turn_pre_call": 0,
        "tools_called_last_turn": tools_called_last_turn,
        "tools_called_prior_turns": len(tool_trace_events),
    }


async def _build_turn_context_with_registry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    recent_events: list[CoachEvent],
    tool_registry: OngoingToolRegistry,
    mode: Literal["coach_chat", "proactive_eval"],
    user_message: str,
    ui_context: dict | None = None,
) -> dict:
    now = datetime.now(UTC)
    today = now.date()
    tool_snapshot = tool_registry.get_observability_snapshot()
    memory_summary, athlete_model = await _load_user_long_term_memory(db, user_id=user_id)
    memory_updated_at, memory_age_days = derive_memory_freshness(athlete_model, now=now)
    transient_state_notes = extract_transient_state_notes(athlete_model)

    # The registry shares this request's AsyncSession. Keep the prefetches
    # sequential: AsyncSession is a mutable transaction and cannot service
    # concurrent execute() calls safely.
    upcoming_competitions = await tool_registry.get_upcoming_competitions()
    current_weekly_plan = await tool_registry.get_current_weekly_plan()
    current_season_plan = await tool_registry.get_current_season_plan()
    competition_proximity_days = nearest_competition_days(upcoming_competitions, today)

    current_weekly_plan_identity = _summarize_current_weekly_plan_identity(current_weekly_plan)

    return {
        "mode": mode,
        "now_utc": now.isoformat(),
        "today_date": today.isoformat(),
        "user_message": user_message,
        "ui_context": ui_context,
        "athlete_model": athlete_model,
        "memory_summary": memory_summary,
        "long_term_memory": {
            "memory_summary": memory_summary,
            "athlete_model": athlete_model,
            "transient_state_notes": transient_state_notes,
            "memory_updated_at": memory_updated_at,
            "memory_age_days": memory_age_days,
        },
        "derived_context": {
            "competition_context": {
                "competition_proximity_days": competition_proximity_days,
                "upcoming_competitions": upcoming_competitions,
            },
            "behavior_context": _behavior_patterns(recent_events),
        },
        "tool_budget": _build_tool_budget(recent_events),
        "current_weekly_plan_identity": current_weekly_plan_identity,
        "current_season_plan": current_season_plan,
        "recent_events": _serialize_recent_conversation_events(recent_events),
        "recent_tool_results": _serialize_recent_tool_results(recent_events),
        "tool_observability": tool_snapshot,
    }


async def build_turn_context(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    recent_events: list[CoachEvent],
    mode: Literal["coach_chat", "proactive_eval"],
    tool_registry: OngoingToolRegistry | None = None,
    user_message: str = "",
    ui_context: dict | None = None,
) -> dict:
    if tool_registry is not None:
        return await _build_turn_context_with_registry(
            db,
            user_id=user_id,
            thread=thread,
            recent_events=recent_events,
            tool_registry=tool_registry,
            mode=mode,
            user_message=user_message,
            ui_context=ui_context,
        )

    async with build_ongoing_tool_registry(db, user_id=user_id) as registry:
        return await _build_turn_context_with_registry(
            db,
            user_id=user_id,
            thread=thread,
            recent_events=recent_events,
            tool_registry=registry,
            mode=mode,
            user_message=user_message,
            ui_context=ui_context,
        )
