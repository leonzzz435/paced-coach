from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.ai_run_cost import AiRunCost
from api.models.coach_event import CoachEvent
from api.models.coach_thread import CoachThread
from api.models.user import User
from api.services.ai_run_costs import (
    build_ai_run_cost_record,
    capture_langsmith_run_costs,
    finish_ai_root_trace,
    start_ai_root_trace,
)
from api.services.coach_event_store import EVENT_TOOL_TRACE, safe_event_payload
from services.ai.coach.athlete_model_agent import summarize_athlete_model

logger = logging.getLogger(__name__)

_SUMMARY_EVENT_BATCH = 20
_MEMORY_EXCLUDED_EVENT_TYPES = {EVENT_TOOL_TRACE, "context_summary"}


def _thread_last_summary_seq_map(athlete_model: dict) -> dict[str, int]:
    meta = athlete_model.get("_meta")
    if not isinstance(meta, dict):
        return {}
    by_thread = meta.get("thread_last_summary_seq")
    if not isinstance(by_thread, dict):
        return {}
    return {
        thread_id: last_seq
        for thread_id, last_seq in by_thread.items()
        if isinstance(thread_id, str) and isinstance(last_seq, int) and last_seq >= 0
    }


def _extract_last_summary_seq(athlete_model: dict | None, *, thread_id: str) -> int:
    if not isinstance(athlete_model, dict):
        return 0
    return _thread_last_summary_seq_map(athlete_model).get(thread_id, 0)


def _canonicalize_athlete_model(athlete_model: object) -> dict:
    if not isinstance(athlete_model, dict):
        return {}

    canonical_model = {key: value for key, value in athlete_model.items() if key != "_meta"}
    raw_meta = athlete_model.get("_meta")
    canonical_meta: dict[str, object] = {}
    if isinstance(raw_meta, dict):
        canonical_meta = {
            key: value
            for key, value in raw_meta.items()
            if key not in {"last_summary_seq", "thread_last_summary_seq"}
        }

    thread_progress = _thread_last_summary_seq_map(athlete_model)
    if thread_progress:
        canonical_meta["thread_last_summary_seq"] = thread_progress

    if canonical_meta:
        canonical_model["_meta"] = canonical_meta
    return canonical_model


def _as_event_summary(event: CoachEvent) -> dict:
    return {
        "seq": event.seq,
        "event_type": event.event_type,
        "actor": event.actor,
        "payload": safe_event_payload(event),
        "created_at": event.created_at.astimezone(UTC).isoformat(),
    }


async def maybe_update_thread_memory(
    db: AsyncSession,
    *,
    thread: CoachThread,
    force: bool = False,
    salient: bool = False,
) -> bool:
    user_row = await db.execute(select(User).where(User.id == thread.user_id).with_for_update())
    user = user_row.scalar_one_or_none()
    if user is None:
        return False

    athlete_model = _canonicalize_athlete_model(user.athlete_model)
    if user.athlete_model != athlete_model:
        user.athlete_model = athlete_model
        db.add(user)

    thread_key = str(thread.id)
    last_summary_seq = _extract_last_summary_seq(athlete_model, thread_id=thread_key)
    pending_events = thread.latest_seq - last_summary_seq
    if force and pending_events <= 0:
        return False
    if not force and not salient and pending_events < _SUMMARY_EVENT_BATCH:
        return False

    row = await db.execute(
        select(CoachEvent)
        .where(
            CoachEvent.thread_id == thread.id,
            CoachEvent.seq > last_summary_seq,
        )
        .order_by(CoachEvent.seq.asc())
        .limit(250)
    )
    events = [event for event in row.scalars().all() if event.event_type not in _MEMORY_EXCLUDED_EVENT_TYPES]
    if not events:
        return False

    ai_trace = start_ai_root_trace(
        run_name="athlete_model_summary",
        feature="coach_memory",
        user_id=str(thread.user_id),
        thread_id=str(thread.id),
        inputs={
            "thread_id": str(thread.id),
            "event_count": len(events),
            "max_seq": events[-1].seq,
        },
        tags=["agent:athlete_model"],
        metadata={
            "source_type": "coach_memory",
            "source_id": f"{thread.id}:{events[-1].seq}",
        },
    )
    try:
        with ai_trace.context_manager():
            summary = await summarize_athlete_model(
                previous_model=athlete_model,
                recent_events=[_as_event_summary(event) for event in events],
                invoke_config={
                    "run_name": "athlete_model_summary",
                    "tags": [
                        "agent:athlete_model",
                        "feature:coach_memory",
                        f"user:{thread.user_id}",
                        f"thread:{thread.id}",
                    ],
                    "metadata": {
                        "user_id": str(thread.user_id),
                        "thread_id": str(thread.id),
                        "max_seq": events[-1].seq,
                    },
                },
            )
        finish_ai_root_trace(
            ai_trace,
            outputs={
                "event_count": len(events),
                "memory_summary_length": len(summary.memory_summary),
                "transient_state_count": len(summary.transient_state_notes),
            },
        )
    except Exception as exc:
        finish_ai_root_trace(ai_trace, error=exc)
        logger.exception("Athlete model summarization failed for thread %s", thread.id)
        return False

    updated_model = {
        "training_preferences": summary.training_preferences,
        "schedule_constraints": summary.schedule_constraints,
        "response_patterns": summary.response_patterns,
        "injury_risk_notes": summary.injury_risk_notes,
        "transient_state_notes": [item.model_dump(mode="json") for item in summary.transient_state_notes],
        "motivation_style": summary.motivation_style,
        "goal_state": summary.goal_state,
        "confidence_by_field": {item.field_name: item.confidence for item in summary.confidence_by_field},
    }
    existing_meta = athlete_model.get("_meta")
    updated_meta = dict(existing_meta) if isinstance(existing_meta, dict) else {}
    updated_meta["thread_last_summary_seq"] = {
        **_thread_last_summary_seq_map(athlete_model),
        thread_key: events[-1].seq,
    }
    updated_meta["updated_at"] = datetime.now(UTC).isoformat()
    updated_model["_meta"] = updated_meta

    user.memory_summary = summary.memory_summary
    user.athlete_model = updated_model
    db.add(user)
    cost_source_id = f"{thread.id}:{events[-1].seq}"
    existing_cost = await db.execute(
        select(AiRunCost.id).where(AiRunCost.source_type == "coach_memory", AiRunCost.source_id == cost_source_id)
    )
    if existing_cost.scalar_one_or_none() is None:
        db.add(
            build_ai_run_cost_record(
                user_id=thread.user_id,
                thread_id=thread.id,
                feature="coach_memory",
                source_type="coach_memory",
                source_id=cost_source_id,
                run_name="athlete_model_summary",
                trace_metadata=ai_trace.trace_metadata(),
                cost_snapshot=capture_langsmith_run_costs(ai_trace.trace_metadata()),
                source_metadata={
                    "event_count": len(events),
                    "max_seq": events[-1].seq,
                    "forced": force,
                    "salient": salient,
                },
            )
        )
    await db.flush()
    return True
