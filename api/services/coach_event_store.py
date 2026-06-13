from __future__ import annotations

import uuid
from datetime import UTC

from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.coach_event import CoachEvent
from api.models.coach_proposal import CoachProposal
from api.models.coach_thread import CoachThread
from api.models.weekly_recap_run import WeeklyRecapRun
from api.services.coach_quota import get_coach_weekly_quota
from api.services.connected_coaching import resolve_connected_coaching_gate
from api.services.full_run_policy import evaluate_weekly_recap_availability
from api.services.integration_status import IntegrationsStatus, load_integrations_status
from api.services.local_usage import get_local_usage_context, has_weekly_recap_feature_access
from core.recap_schedule import compute_recap_week_anchor_utc

EVENT_USER_MESSAGE = "user_message"
EVENT_COACH_MESSAGE = "coach_message"
EVENT_RECAP_NARRATIVE = "recap_narrative"
EVENT_RECAP_RESPONSE = "recap_response"
EVENT_PROPOSAL_CREATED = "proposal_created"
EVENT_PROPOSAL_ACCEPTED = "proposal_accepted"
EVENT_PROPOSAL_REJECTED = "proposal_rejected"
EVENT_PROACTIVE_ALERT = "proactive_alert"
EVENT_FULL_RUN_REQUESTED = "full_run_requested"
EVENT_TOOL_TRACE = "tool_trace"
THREAD_STATUS_ACTIVE = "active"
THREAD_STATUS_ARCHIVED = "archived"


def resolve_recap_gate_state(
    *,
    recap_feature_enabled: bool,
    recap_window_open: bool,
    integrations_status: IntegrationsStatus,
) -> tuple[bool, str | None, str | None]:
    gate = resolve_connected_coaching_gate(
        feature_enabled=recap_feature_enabled,
        integrations_status=integrations_status,
        locked_message="Weekly recap is not available on this plan.",
    )
    if recap_window_open:
        return gate.allowed, gate.attention_message, gate.gate_target
    if gate.attention_message:
        return False, gate.attention_message, gate.gate_target or "settings"
    return False, None, None


def resolve_coach_chat_gate_state(*, quota: dict[str, object]) -> tuple[bool, str | None, str | None]:
    if not bool(quota.get("is_limited")):
        return True, None, None

    remaining = quota.get("remaining")
    if not isinstance(remaining, int) or remaining > 0:
        return True, None, None

    return False, "Daily coach message limit reached. Your coaching allowance resets tomorrow.", None


def safe_event_payload(event: CoachEvent) -> dict:
    payload = event.payload
    return payload if isinstance(payload, dict) else {}


async def get_or_create_coach_thread(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread_id: uuid.UUID | None = None,
    for_update: bool = False,
) -> CoachThread:
    if thread_id is not None:
        query = select(CoachThread).where(
            CoachThread.id == thread_id,
            CoachThread.user_id == user_id,
        )
        if for_update:
            query = query.with_for_update()
        row = await db.execute(query)
        thread = row.scalar_one_or_none()
        if thread is None or thread.status != THREAD_STATUS_ACTIVE:
            raise HTTPException(status_code=404, detail="Thread not found")
        return thread

    thread = CoachThread(user_id=user_id, latest_seq=0, status=THREAD_STATUS_ACTIVE)
    db.add(thread)
    await db.flush()
    return thread


async def get_coach_thread_by_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
    for_update: bool = False,
) -> CoachThread | None:
    query = select(CoachThread).where(
        CoachThread.id == thread_id,
        CoachThread.user_id == user_id,
    )
    if for_update:
        query = query.with_for_update()
    row = await db.execute(query)
    return row.scalar_one_or_none()


async def get_latest_active_coach_thread(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    for_update: bool = False,
) -> CoachThread | None:
    query = (
        select(CoachThread)
        .where(
            CoachThread.user_id == user_id,
            CoachThread.status == THREAD_STATUS_ACTIVE,
        )
        .order_by(CoachThread.updated_at.desc(), CoachThread.created_at.desc())
        .limit(1)
    )
    if for_update:
        query = query.with_for_update()
    row = await db.execute(query)
    return row.scalar_one_or_none()


async def get_latest_coach_thread(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    for_update: bool = False,
) -> CoachThread | None:
    query = (
        select(CoachThread)
        .where(CoachThread.user_id == user_id)
        .order_by(CoachThread.updated_at.desc(), CoachThread.created_at.desc())
        .limit(1)
    )
    if for_update:
        query = query.with_for_update()
    row = await db.execute(query)
    return row.scalar_one_or_none()


async def list_coach_threads(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[CoachThread]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    row = await db.execute(
        select(CoachThread)
        .where(CoachThread.user_id == user_id)
        .order_by(
            case((CoachThread.status == THREAD_STATUS_ACTIVE, 0), else_=1).asc(),
            CoachThread.updated_at.desc(),
            CoachThread.created_at.desc(),
        )
        .offset(safe_offset)
        .limit(safe_limit)
    )
    return list(row.scalars().all())


async def archive_coach_thread(
    db: AsyncSession,
    *,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CoachThread:
    thread = await get_coach_thread_by_id(
        db,
        user_id=user_id,
        thread_id=thread_id,
        for_update=True,
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread.status = THREAD_STATUS_ARCHIVED
    db.add(thread)
    await db.flush()
    return thread


async def append_coach_events(
    db: AsyncSession,
    *,
    thread: CoachThread,
    items: list[tuple[str, str, dict]],
) -> list[CoachEvent]:
    locked_row = await db.execute(
        select(CoachThread.latest_seq)
        .where(CoachThread.id == thread.id)
        .with_for_update()
    )
    current_seq = locked_row.scalar_one()
    created: list[CoachEvent] = []
    next_seq = current_seq
    for event_type, actor, payload in items:
        next_seq += 1
        event = CoachEvent(
            thread_id=thread.id,
            seq=next_seq,
            event_type=event_type,
            actor=actor,
            payload=payload,
        )
        db.add(event)
        created.append(event)
    thread.latest_seq = next_seq
    db.add(thread)
    await db.flush()
    return created


async def get_thread_events(
    db: AsyncSession,
    *,
    thread_id: uuid.UUID,
    after_seq: int | None = None,
    limit: int = 200,
) -> list[CoachEvent]:
    query = select(CoachEvent).where(CoachEvent.thread_id == thread_id)
    if after_seq is not None:
        query = query.where(CoachEvent.seq > after_seq)
    query = query.order_by(CoachEvent.seq.asc()).limit(max(1, min(limit, 500)))
    row = await db.execute(query)
    return list(row.scalars().all())


def _serialize_text_message(event: CoachEvent, *, role: str, text: str) -> dict:
    return {
        "id": f"coach-event:{event.id}",
        "seq": event.seq,
        "kind": "text",
        "role": role,
        "created_at": event.created_at.astimezone(UTC).isoformat(),
        "text": text,
    }


def _serialize_recap_narrative(event: CoachEvent, payload: dict) -> dict | None:
    recap = payload.get("recap")
    if not isinstance(recap, dict):
        return None
    return {
        "id": f"coach-event:{event.id}",
        "seq": event.seq,
        "kind": "recap",
        "role": "coach",
        "created_at": event.created_at.astimezone(UTC).isoformat(),
        "recap": recap,
    }


def _serialize_proposal_created(
    event: CoachEvent,
    payload: dict,
    *,
    proposal_status_by_id: dict[str, str],
) -> dict | None:
    proposal_id = payload.get("proposal_id")
    if not isinstance(proposal_id, str):
        return None
    normalized_status = proposal_status_by_id.get(proposal_id, str(payload.get("status", "pending")))
    return {
        "id": f"coach-event:{event.id}",
        "seq": event.seq,
        "kind": "proposal",
        "role": "coach",
        "created_at": event.created_at.astimezone(UTC).isoformat(),
        "proposal_id": proposal_id,
        "origin": str(payload.get("origin", "coach_turn")),
        "status": normalized_status,
        "assistant_message": str(payload.get("assistant_message", "")),
        "ops": payload.get("ops", []),
        "base_weekly_plan": payload.get("base_weekly_plan"),
        "preview_weekly_plan": payload.get("preview_weekly_plan"),
    }


def _serialize_text_event(event: CoachEvent, payload: dict, *, role: str, text_key: str) -> dict | None:
    text = str(payload.get(text_key, "")).strip()
    if not text:
        return None
    return _serialize_text_message(event, role=role, text=text)


def serialize_thread_event(event: CoachEvent, *, proposal_status_by_id: dict[str, str]) -> dict | None:
    payload = safe_event_payload(event)
    if event.event_type == EVENT_USER_MESSAGE:
        return _serialize_text_event(event, payload, role="athlete", text_key="text")
    if event.event_type in {EVENT_COACH_MESSAGE, EVENT_PROACTIVE_ALERT}:
        return _serialize_text_event(event, payload, role="coach", text_key="text")
    if event.event_type == EVENT_RECAP_RESPONSE:
        return None
    if event.event_type == EVENT_RECAP_NARRATIVE:
        return _serialize_recap_narrative(event, payload)
    if event.event_type == EVENT_PROPOSAL_CREATED:
        return _serialize_proposal_created(event, payload, proposal_status_by_id=proposal_status_by_id)
    return None


def _collect_recap_run_ids(messages_by_thread: dict[str, list[dict]]) -> list[uuid.UUID]:
    run_ids: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()

    for messages in messages_by_thread.values():
        for message in messages:
            if message.get("kind") != "recap":
                continue
            recap = message.get("recap")
            if not isinstance(recap, dict):
                continue
            raw_run_id = recap.get("run_id")
            if not isinstance(raw_run_id, str):
                continue
            try:
                run_id = uuid.UUID(raw_run_id)
            except ValueError:
                continue
            if run_id in seen:
                continue
            seen.add(run_id)
            run_ids.append(run_id)

    return run_ids


async def hydrate_recap_messages_by_thread(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    messages_by_thread: dict[str, list[dict]],
) -> dict[str, list[dict]]:
    recap_run_ids = _collect_recap_run_ids(messages_by_thread)
    if not recap_run_ids:
        return messages_by_thread

    recap_rows = await db.execute(
        select(
            WeeklyRecapRun.id,
            WeeklyRecapRun.follow_up_question,
            WeeklyRecapRun.athlete_response,
        ).where(
            WeeklyRecapRun.user_id == user_id,
            WeeklyRecapRun.id.in_(recap_run_ids),
        )
    )
    recap_fields_by_id = {
        str(run_id): {
            "follow_up_question": follow_up_question,
            "athlete_response": athlete_response,
        }
        for run_id, follow_up_question, athlete_response in recap_rows.all()
    }
    if not recap_fields_by_id:
        return messages_by_thread

    hydrated_by_thread: dict[str, list[dict]] = {}
    for thread_id, messages in messages_by_thread.items():
        hydrated_messages: list[dict] = []
        for message in messages:
            if message.get("kind") != "recap":
                hydrated_messages.append(message)
                continue
            recap = message.get("recap")
            if not isinstance(recap, dict):
                hydrated_messages.append(message)
                continue
            run_id = recap.get("run_id")
            if not isinstance(run_id, str) or run_id not in recap_fields_by_id:
                hydrated_messages.append(message)
                continue
            hydrated_messages.append(
                {
                    **message,
                    "recap": {
                        **recap,
                        **recap_fields_by_id[run_id],
                    },
                }
            )
        hydrated_by_thread[thread_id] = hydrated_messages

    return hydrated_by_thread


async def build_thread_projection(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    after_seq: int | None = None,
    limit: int = 200,
) -> dict:
    thread_snapshot_row = await db.execute(
        select(
            CoachThread.id,
            CoachThread.status,
            CoachThread.title,
            CoachThread.latest_seq,
            CoachThread.updated_at,
        ).where(CoachThread.id == thread.id)
    )
    thread_snapshot = thread_snapshot_row.one_or_none()
    if thread_snapshot is None:
        raise RuntimeError("Coach thread not found while building projection")

    events = await get_thread_events(db, thread_id=thread.id, after_seq=after_seq, limit=limit)
    proposal_status_rows = await db.execute(
        select(CoachProposal.id, CoachProposal.status).where(
            CoachProposal.user_id == user_id,
            CoachProposal.thread_id == thread.id,
        )
    )
    proposal_status_by_id = {str(proposal_id): status for proposal_id, status in proposal_status_rows.all()}
    messages = [
        serialized
        for event in events
        if (serialized := serialize_thread_event(event, proposal_status_by_id=proposal_status_by_id)) is not None
    ]
    hydrated_messages_by_thread = await hydrate_recap_messages_by_thread(
        db,
        user_id=user_id,
        messages_by_thread={str(thread.id): messages},
    )
    messages = hydrated_messages_by_thread[str(thread.id)]

    pending_proposals_row = await db.execute(
        select(CoachProposal.id).where(
            CoachProposal.user_id == user_id,
            CoachProposal.status == "pending",
            CoachProposal.thread_id == thread.id,
        )
    )
    pending_ids = [str(item) for item in pending_proposals_row.scalars().all()]

    recap_availability = await evaluate_weekly_recap_availability(db, user_id=user_id)
    usage_context = await get_local_usage_context(db, user_id=user_id)
    recap_feature_enabled = has_weekly_recap_feature_access(usage_context)
    integrations_status = await load_integrations_status(db, user_id=user_id)
    anchor = compute_recap_week_anchor_utc()
    quota = await get_coach_weekly_quota(db, user_id=user_id, week_anchor_utc=anchor)
    can_send_message, coach_gate_message, coach_gate_target = resolve_coach_chat_gate_state(
        quota=quota,
    )
    can_trigger_recap, training_provider_message, recap_gate_target = resolve_recap_gate_state(
        recap_feature_enabled=recap_feature_enabled,
        recap_window_open=recap_availability.allowed,
        integrations_status=integrations_status,
    )

    return {
        "thread": {
            "id": str(thread_snapshot.id),
            "status": thread_snapshot.status,
            "title": thread_snapshot.title,
            "latest_seq": thread_snapshot.latest_seq,
            "updated_at": thread_snapshot.updated_at.astimezone(UTC).isoformat(),
        },
        "messages": messages,
        "quota": quota,
        "can_send_message": can_send_message,
        "coach_gate_message": coach_gate_message,
        "coach_gate_target": coach_gate_target,
        "has_pending_proposal": len(pending_ids) > 0,
        "pending_proposal_ids": pending_ids,
        "can_trigger_recap": can_trigger_recap,
        "training_provider_message": training_provider_message,
        "recap_gate_target": recap_gate_target,
        "next_after_seq": events[-1].seq if events else after_seq,
    }
