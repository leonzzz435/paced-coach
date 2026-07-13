from __future__ import annotations

import hashlib
import inspect
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.coach_event import CoachEvent
from api.models.coach_proposal import CoachProposal
from api.models.coach_thread import CoachThread
from api.models.coach_turn_request import CoachTurnRequest
from api.models.coach_turn_run import CoachTurnRun
from api.models.weekly_recap_run import WeeklyRecapRun
from api.services.ai_run_costs import build_ai_run_cost_record, capture_langsmith_run_costs, trace_metadata_from_values
from api.services.coach_context import build_turn_context, is_salient_event
from api.services.coach_event_store import (
    EVENT_COACH_MESSAGE,
    EVENT_FULL_RUN_REQUESTED,
    EVENT_PROPOSAL_ACCEPTED,
    EVENT_PROPOSAL_CREATED,
    EVENT_PROPOSAL_REJECTED,
    EVENT_RECAP_RESPONSE,
    EVENT_TOOL_TRACE,
    EVENT_USER_MESSAGE,
    THREAD_STATUS_ACTIVE,
    append_coach_events,
    archive_coach_thread,
    build_thread_projection,
    get_coach_thread_by_id,
    get_latest_active_coach_thread,
    get_or_create_coach_thread,
    get_thread_events,
    hydrate_recap_messages_by_thread,
    list_coach_threads,
    resolve_coach_chat_gate_state,
    resolve_recap_gate_state,
    serialize_thread_event,
)
from api.services.coach_memory import maybe_update_thread_memory
from api.services.coach_patch_ops import apply_ops, parse_patch_ops, sanitize_ops
from api.services.coach_quota import (
    consume_coach_weekly_quota,
    ensure_coach_weekly_quota_available,
    get_coach_weekly_quota,
)
from api.services.coach_thread_titles import generate_thread_title_from_exchange
from api.services.full_run_policy import evaluate_full_run_availability, evaluate_weekly_recap_availability
from api.services.integration_status import load_integrations_status
from api.services.local_usage import consume_adaptive_update, get_local_usage_context, has_weekly_recap_feature_access
from api.services.ongoing_tools import build_ongoing_tool_registry
from api.services.recap import execute_recap_turn
from core.recap_schedule import compute_recap_week_anchor_utc
from services.ai.coach.continuum_turn_agent import run_continuum_coach_turn
from services.ai.langgraph.schemas.ui_blocks import UiWeeklyPlan

_SAFETY_KEYWORDS = ("injury", "injured", "pain", "sick", "ill", "medication")
_MEDICAL_DISCLAIMER = (
    "I can help with training guidance, but this sounds health-related. "
    "Please consult a qualified medical professional for diagnosis or treatment decisions."
)
_IDEMPOTENCY_TTL = timedelta(days=14)
_IDEMPOTENCY_FAILED_TTL = timedelta(hours=1)

_IDEMPOTENCY_STATUS_IN_PROGRESS = "in_progress"
_IDEMPOTENCY_STATUS_COMPLETED = "completed"
_IDEMPOTENCY_STATUS_FAILED = "failed"
_TOOL_TRACE_RESULT_PREVIEW_LIMIT = 2000
_THREAD_ITERATION_LIMIT_REACHED_MESSAGE = "Thread iteration limit reached. Start a new thread to continue coaching."
StatusEmitter = Callable[[dict[str, object]], object]


async def _emit_turn_status(status_emitter: StatusEmitter | None, payload: dict[str, object]):
    if status_emitter is None:
        return
    status_result = status_emitter(payload)
    if inspect.isawaitable(status_result):
        await status_result


def _mentions_health_safety(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _SAFETY_KEYWORDS)


def _safety_flags_indicate_health_concern(safety_flags: list[str] | None) -> bool:
    if not safety_flags:
        return False
    return any(
        _mentions_health_safety(flag) or any(token in flag.lower() for token in ("health", "medical", "symptom"))
        for flag in safety_flags
    )


def _with_disclaimer_if_needed(
    *,
    base_message: str,
    user_message: str,
    requires_disclaimer: bool,
    safety_flags: list[str] | None = None,
) -> str:
    if not _mentions_health_safety(user_message) and not _safety_flags_indicate_health_concern(safety_flags):
        return base_message
    if _MEDICAL_DISCLAIMER in base_message:
        return base_message
    return f"{base_message}\n\n{_MEDICAL_DISCLAIMER}".strip()


def _thread_iteration_limit() -> int:
    configured = get_settings().coach_thread_iteration_limit
    return max(configured, 0)


async def _ensure_thread_iteration_limit(db: AsyncSession, *, thread: CoachThread):
    limit = _thread_iteration_limit()
    if limit <= 0:
        return

    row = await db.execute(
        select(func.count(CoachEvent.id)).where(
            CoachEvent.thread_id == thread.id,
            CoachEvent.event_type == EVENT_USER_MESSAGE,
        )
    )
    iterations_used = int(row.scalar_one() or 0)
    if iterations_used >= limit:
        raise HTTPException(status_code=409, detail=f"{_THREAD_ITERATION_LIMIT_REACHED_MESSAGE} (limit={limit})")


async def _get_active_weekly_plan(db: AsyncSession, *, user_id: uuid.UUID) -> ActiveWeeklyPlan:
    row = await db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id))
    active_weekly = row.scalar_one_or_none()
    if not active_weekly:
        raise HTTPException(status_code=404, detail="No active weekly plan found")
    return active_weekly


def _serialize_validated_ui_day_context(*, week, day) -> dict[str, object]:
    return {
        "source": "today_mission",
        "day": {
            "day_id": day.day_id,
            "date": day.date.isoformat(),
            "day_label": day.day_label,
            "workout_title": day.workout_title,
            "focus_type": day.focus_type,
            "estimated_duration_min": day.estimated_duration_min,
            "estimated_intensity": day.estimated_intensity,
            "readiness_note": day.readiness_note,
            "is_completed": day.is_completed,
            "week_id": week.week_id,
            "week_label": week.week_label,
            "week_theme": week.week_theme,
        },
    }


async def _resolve_turn_ui_context(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    ui_context: dict[str, object] | None,
) -> dict[str, object] | None:
    if not isinstance(ui_context, dict):
        return None

    source = str(ui_context.get("source") or "").strip()
    day_id = str(ui_context.get("day_id") or "").strip()
    if source != "today_mission" or not day_id:
        return None

    requested_week_id = str(ui_context.get("week_id") or "").strip() or None
    requested_date = str(ui_context.get("date") or "").strip() or None

    row = await db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id))
    active_weekly = row.scalar_one_or_none()
    if active_weekly is None:
        return None

    weekly_plan = UiWeeklyPlan.model_validate(active_weekly.plan_data)
    for week in weekly_plan.weeks:
        for day in week.days:
            if day.day_id != day_id:
                continue
            if requested_week_id and requested_week_id != week.week_id:
                return None
            if requested_date and requested_date != day.date.isoformat():
                return None
            return _serialize_validated_ui_day_context(week=week, day=day)
    return None


async def _get_proposal(
    db: AsyncSession, *, user_id: uuid.UUID, proposal_id: uuid.UUID, thread_id: uuid.UUID
) -> CoachProposal:
    row = await db.execute(
        select(CoachProposal).where(
            CoachProposal.user_id == user_id,
            CoachProposal.id == proposal_id,
            (CoachProposal.thread_id == thread_id) | (CoachProposal.thread_id.is_(None)),
        )
    )
    proposal = row.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.thread_id is None:
        proposal.thread_id = thread_id
        db.add(proposal)
        await db.flush()
    return proposal


async def _capture_recap_follow_up_response(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    response_text: str,
) -> list[CoachEvent]:
    recap_row = await db.execute(
        select(WeeklyRecapRun)
        .join(CoachEvent, WeeklyRecapRun.recap_event_id == CoachEvent.id)
        .where(
            WeeklyRecapRun.user_id == user_id,
            WeeklyRecapRun.status == "completed",
            WeeklyRecapRun.follow_up_question.is_not(None),
            WeeklyRecapRun.athlete_response.is_(None),
            CoachEvent.thread_id == thread.id,
        )
        .order_by(WeeklyRecapRun.updated_at.desc())
        .limit(1)
    )
    recap_run = recap_row.scalar_one_or_none()
    if recap_run is None:
        return []

    recap_run.athlete_response = response_text
    db.add(recap_run)
    await db.flush()
    return await append_coach_events(
        db,
        thread=thread,
        items=[
            (
                EVENT_RECAP_RESPONSE,
                "user",
                {
                    "recap_run_id": str(recap_run.id),
                    "response": response_text,
                },
            )
        ],
    )


def _build_turn_request_hash(
    *,
    action: str,
    thread_id: uuid.UUID | None,
    message: str | None,
    proposal_id: uuid.UUID | None,
    reason: str | None,
    ui_context: dict[str, object] | None,
) -> str:
    payload = {
        "action": action,
        "thread_id": str(thread_id) if thread_id else None,
        "message": (message or "").strip(),
        "proposal_id": str(proposal_id) if proposal_id else None,
        "reason": (reason or "").strip(),
        "ui_context": ui_context,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


async def _claim_idempotency_request(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    idempotency_key: str,
    request_hash: str,
) -> tuple[dict | None, bool]:
    now = datetime.now(UTC)
    expires_at = now + _IDEMPOTENCY_TTL
    try:
        async with db.begin_nested():
            db.add(
                CoachTurnRequest(
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    status=_IDEMPOTENCY_STATUS_IN_PROGRESS,
                    response_payload=None,
                    expires_at=expires_at,
                )
            )
            await db.flush()
            return None, True
    except IntegrityError:
        row = await db.execute(
            select(CoachTurnRequest)
            .where(
                CoachTurnRequest.user_id == user_id,
                CoachTurnRequest.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
        request_row = row.scalar_one_or_none()
        if request_row is None:
            raise HTTPException(status_code=409, detail="Conflicting idempotent request") from None
        if request_row.request_hash != request_hash:
            raise HTTPException(
                status_code=409, detail="Idempotency key reused with different request payload"
            ) from None
        if request_row.status == _IDEMPOTENCY_STATUS_COMPLETED and isinstance(request_row.response_payload, dict):
            return request_row.response_payload, False
        if request_row.status == _IDEMPOTENCY_STATUS_IN_PROGRESS and request_row.expires_at >= now:
            raise HTTPException(status_code=409, detail="Idempotent request already in progress") from None

        request_row.status = _IDEMPOTENCY_STATUS_IN_PROGRESS
        request_row.response_payload = None
        request_row.expires_at = expires_at
        db.add(request_row)
        await db.flush()
        return None, True


async def _complete_idempotency_request(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    idempotency_key: str,
    request_hash: str,
    response_payload: dict,
) -> dict:
    row = await db.execute(
        select(CoachTurnRequest)
        .where(
            CoachTurnRequest.user_id == user_id,
            CoachTurnRequest.idempotency_key == idempotency_key,
        )
        .with_for_update()
    )
    request_row = row.scalar_one_or_none()
    if request_row is None:
        raise HTTPException(status_code=409, detail="Idempotency claim missing")
    if request_row.request_hash != request_hash:
        raise HTTPException(status_code=409, detail="Idempotency key reused with different request payload")
    request_row.status = _IDEMPOTENCY_STATUS_COMPLETED
    request_row.response_payload = response_payload
    request_row.expires_at = datetime.now(UTC) + _IDEMPOTENCY_TTL
    db.add(request_row)
    await db.flush()
    return response_payload


async def _fail_idempotency_request(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    idempotency_key: str,
    request_hash: str,
):
    row = await db.execute(
        select(CoachTurnRequest)
        .where(
            CoachTurnRequest.user_id == user_id,
            CoachTurnRequest.idempotency_key == idempotency_key,
        )
        .with_for_update()
    )
    request_row = row.scalar_one_or_none()
    if request_row is None or request_row.request_hash != request_hash:
        return
    request_row.status = _IDEMPOTENCY_STATUS_FAILED
    request_row.expires_at = datetime.now(UTC) + _IDEMPOTENCY_FAILED_TTL
    db.add(request_row)
    await db.flush()


def _event_stubs(events: list) -> list[dict]:
    return [{"seq": event.seq, "event_type": event.event_type} for event in events]


def _assistant_message_from_turn_payload(turn_payload: dict) -> str | None:
    assistant_message = turn_payload.get("assistant_message")
    if not isinstance(assistant_message, str):
        return None
    cleaned = assistant_message.strip()
    return cleaned or None


async def _maybe_set_thread_title_from_first_exchange(
    db: AsyncSession,
    *,
    thread: CoachThread,
    user_message: str | None,
    turn_payload: dict,
):
    if thread.title and thread.title.strip():
        return
    trimmed_user_message = (user_message or "").strip()
    if not trimmed_user_message:
        return
    assistant_message = _assistant_message_from_turn_payload(turn_payload)
    if not assistant_message:
        return
    try:
        title = await generate_thread_title_from_exchange(
            user_message=trimmed_user_message,
            coach_reply=assistant_message,
        )
    except Exception:
        return
    if not title:
        return
    thread.title = title
    db.add(thread)
    await db.flush()


def _normalize_tool_trace_payload(trace: dict[str, object], *, turn_seq_anchor: int) -> dict:
    tool_name = str(trace.get("tool_name", "")).strip() or "unknown"
    args_payload = trace.get("args")
    try:
        args_json = json.loads(json.dumps(args_payload, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        args_json = {"value": str(args_payload)}

    result_preview_raw = str(trace.get("result_preview", ""))
    result_preview = result_preview_raw[:_TOOL_TRACE_RESULT_PREVIEW_LIMIT]
    char_len = trace.get("char_len")
    result_char_len = int(char_len) if isinstance(char_len, int) else len(result_preview_raw)
    truncated_flag = bool(trace.get("truncated")) or len(result_preview_raw) > len(result_preview)
    result_hash = hashlib.sha256(result_preview_raw.encode("utf-8")).hexdigest()
    return {
        "turn_seq_anchor": turn_seq_anchor,
        "tool_name": tool_name,
        "args": args_json,
        "result_preview": result_preview,
        "char_len": result_char_len,
        "truncated": truncated_flag,
        "result_hash": result_hash,
    }


async def _append_tool_trace_events(
    db: AsyncSession,
    *,
    thread: CoachThread,
    turn_seq_anchor: int,
    traces: list[dict[str, object]],
) -> list:
    if not traces:
        return []
    trace_items = [
        (EVENT_TOOL_TRACE, "system", _normalize_tool_trace_payload(trace, turn_seq_anchor=turn_seq_anchor))
        for trace in traces
    ]
    return await append_coach_events(db, thread=thread, items=trace_items)


def _primary_response_event(created_events: list[CoachEvent]) -> CoachEvent | None:
    for event in created_events:
        if event.event_type in {EVENT_COACH_MESSAGE, EVENT_PROPOSAL_CREATED}:
            return event
    return None


async def _record_coach_turn_run(
    db: AsyncSession,
    *,
    turn_run_id: uuid.UUID,
    user_id: uuid.UUID,
    thread: CoachThread,
    user_message_event: CoachEvent,
    created_events: list[CoachEvent],
    execution,
) -> CoachTurnRun:
    response_event = _primary_response_event(created_events)
    trace_metadata = execution.trace_metadata
    turn_run = CoachTurnRun(
        id=turn_run_id,
        user_id=user_id,
        thread_id=thread.id,
        turn_seq_anchor=user_message_event.seq,
        user_message_event_id=user_message_event.id,
        response_event_id=response_event.id if response_event is not None else None,
        langsmith_project=trace_metadata.project_name if trace_metadata is not None else None,
        langsmith_trace_id=trace_metadata.trace_id if trace_metadata is not None else None,
        langsmith_root_run_id=trace_metadata.root_run_id if trace_metadata is not None else None,
        run_name=trace_metadata.run_name if trace_metadata is not None else "continuum_coach_turn",
        attempt_count=trace_metadata.attempt_count if trace_metadata is not None else 1,
        status="completed",
    )
    db.add(turn_run)
    await db.flush()
    return turn_run


def _serialize_turn_run(turn_run: CoachTurnRun) -> dict[str, object]:
    return {
        "coach_thread_id": str(turn_run.thread_id),
        "coach_turn_run_id": str(turn_run.id),
        "user_message_event_id": str(turn_run.user_message_event_id),
        "response_event_id": str(turn_run.response_event_id) if turn_run.response_event_id is not None else None,
        "turn_seq_anchor": turn_run.turn_seq_anchor,
        "langsmith_project": turn_run.langsmith_project,
        "langsmith_trace_id": turn_run.langsmith_trace_id,
        "langsmith_root_run_id": turn_run.langsmith_root_run_id,
    }


async def _can_request_full_run(db: AsyncSession, *, user_id: uuid.UUID) -> bool:
    availability = await evaluate_full_run_availability(db, user_id=user_id)
    return availability.allowed


async def _projection_payload(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    after_seq: int | None = None,
    limit: int = 200,
) -> dict:
    projection = await build_thread_projection(db, user_id=user_id, thread=thread, after_seq=after_seq, limit=limit)
    return {
        "thread": projection["thread"],
        "messages": projection["messages"],
        "quota": projection["quota"],
        "can_send_message": projection["can_send_message"],
        "coach_gate_message": projection["coach_gate_message"],
        "coach_gate_target": projection["coach_gate_target"],
        "has_pending_proposal": projection["has_pending_proposal"],
        "can_trigger_recap": projection["can_trigger_recap"],
        "training_provider_message": projection["training_provider_message"],
        "recap_gate_target": projection["recap_gate_target"],
        "pending_proposal_ids": projection["pending_proposal_ids"],
        "next_after_seq": projection["next_after_seq"],
    }


async def _resolve_thread_for_turn(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    action: str,
    thread_id: uuid.UUID | None,
    proposal_id: uuid.UUID | None,
) -> CoachThread:
    if action in {"proposal_accept", "proposal_reject"} and proposal_id is None:
        raise HTTPException(status_code=400, detail="proposal_id is required for proposal action")

    if thread_id is not None:
        return await get_or_create_coach_thread(
            db,
            user_id=user_id,
            thread_id=thread_id,
        )

    if action in ("text", "recap"):
        return await get_or_create_coach_thread(db, user_id=user_id)

    if proposal_id is not None:
        row = await db.execute(
            select(CoachProposal).where(
                CoachProposal.user_id == user_id,
                CoachProposal.id == proposal_id,
            )
        )
        proposal = row.scalar_one_or_none()
        if proposal is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        if proposal.thread_id is not None:
            return await get_or_create_coach_thread(
                db,
                user_id=user_id,
                thread_id=proposal.thread_id,
            )
    return await get_or_create_coach_thread(db, user_id=user_id)


async def _handle_text_turn(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    message: str,
    quota_source_id: str,
    ui_context: dict[str, object] | None = None,
    status_emitter: StatusEmitter | None = None,
) -> tuple[dict, list]:
    trimmed_message = message.strip()
    if not trimmed_message:
        raise HTTPException(status_code=400, detail="message is required for text action")
    await _ensure_thread_iteration_limit(db, thread=thread)
    await ensure_coach_weekly_quota_available(db, user_id=user_id)

    created_events = await append_coach_events(
        db,
        thread=thread,
        items=[(EVENT_USER_MESSAGE, "user", {"text": trimmed_message})],
    )
    created_events.extend(
        await _capture_recap_follow_up_response(
            db,
            user_id=user_id,
            thread=thread,
            response_text=trimmed_message,
        )
    )
    user_message_event = created_events[0]
    turn_run_id = uuid.uuid4()
    recent_events = await get_thread_events(
        db,
        thread_id=thread.id,
        after_seq=None,
        limit=500,
    )
    await _emit_turn_status(
        status_emitter,
        {
            "step": "preparing",
            "message": "Preparing coaching context...",
        },
    )

    validated_ui_context = await _resolve_turn_ui_context(db, user_id=user_id, ui_context=ui_context)

    async with build_ongoing_tool_registry(db, user_id=user_id, require_training_provider=False) as tool_registry:
        context_pack = await build_turn_context(
            db,
            user_id=user_id,
            thread=thread,
            recent_events=recent_events,
            tool_registry=tool_registry,
            mode="coach_chat",
            user_message=trimmed_message,
            ui_context=validated_ui_context,
        )
        execution = await run_continuum_coach_turn(
            user_message=trimmed_message,
            context_pack=context_pack,
            tool_registry=tool_registry,
            thread_id=str(thread.id),
            user_id=str(user_id),
            status_emitter=status_emitter,
            root_run_id=str(turn_run_id),
        )
    model_output = execution.output

    quota = await consume_coach_weekly_quota(db, user_id=user_id, source_id=quota_source_id)

    user_turn_seq = user_message_event.seq
    trace_events = await _append_tool_trace_events(
        db,
        thread=thread,
        turn_seq_anchor=user_turn_seq,
        traces=execution.tool_traces,
    )
    created_events.extend(trace_events)

    assistant_message = _with_disclaimer_if_needed(
        base_message=model_output.assistant_message,
        user_message=trimmed_message,
        requires_disclaimer=model_output.requires_medical_disclaimer,
        safety_flags=model_output.safety_flags,
    )
    full_run_reason = model_output.full_run_reason.strip() if model_output.full_run_reason else None

    ops = sanitize_ops(model_output.proposal_ops)
    turn_payload: dict = {
        "kind": "message",
        "assistant_message": assistant_message,
        "ops": [],
        "changed": False,
        "base_weekly_plan": None,
        "preview_weekly_plan": None,
        "requests_full_run": model_output.requests_full_run,
        "full_run_reason": full_run_reason,
        "safety_flags": model_output.safety_flags,
    }
    proposal_changed = False

    if ops:
        active_weekly = await _get_active_weekly_plan(db, user_id=user_id)
        weekly_plan = UiWeeklyPlan.model_validate(active_weekly.plan_data)
        preview_plan, proposal_changed = apply_ops(weekly_plan, ops)
        proposal = CoachProposal(
            user_id=user_id,
            thread_id=thread.id,
            weekly_plan_version=active_weekly.version,
            assistant_message=assistant_message,
            ops={"ops": [item.model_dump(mode="json") for item in ops]},
            origin="coach_turn",
            status="pending",
        )
        db.add(proposal)
        await db.flush()

        proposal_event = await append_coach_events(
            db,
            thread=thread,
            items=[
                (
                    EVENT_PROPOSAL_CREATED,
                    "coach",
                    {
                        "proposal_id": str(proposal.id),
                        "assistant_message": assistant_message,
                        "ops": [item.model_dump(mode="json") for item in ops],
                        "base_weekly_plan": weekly_plan.model_dump(mode="json"),
                        "preview_weekly_plan": preview_plan.model_dump(mode="json"),
                        "origin": proposal.origin,
                        "status": proposal.status,
                    },
                )
            ],
        )
        created_events.extend(proposal_event)
        proposal.source_event_seq = proposal_event[0].seq
        db.add(proposal)
        turn_payload = {
            "kind": "proposal",
            "proposal_id": str(proposal.id),
            "assistant_message": assistant_message,
            "changed": proposal_changed,
            "base_weekly_plan": weekly_plan.model_dump(mode="json"),
            "preview_weekly_plan": preview_plan.model_dump(mode="json"),
            "ops": [item.model_dump(mode="json") for item in ops],
            "requests_full_run": model_output.requests_full_run,
            "full_run_reason": full_run_reason,
            "safety_flags": model_output.safety_flags,
        }
    else:
        coach_events = await append_coach_events(
            db,
            thread=thread,
            items=[(EVENT_COACH_MESSAGE, "coach", {"text": assistant_message})],
        )
        created_events.extend(coach_events)

    if model_output.requests_full_run and await _can_request_full_run(db, user_id=user_id):
        if full_run_reason:
            full_run_events = await append_coach_events(
                db,
                thread=thread,
                items=[(EVENT_FULL_RUN_REQUESTED, "coach", {"reason": full_run_reason})],
            )
            created_events.extend(full_run_events)

    turn_run = await _record_coach_turn_run(
        db,
        turn_run_id=turn_run_id,
        user_id=user_id,
        thread=thread,
        user_message_event=user_message_event,
        created_events=created_events,
        execution=execution,
    )
    turn_trace_metadata = trace_metadata_from_values(
        project_name=turn_run.langsmith_project,
        trace_id=turn_run.langsmith_trace_id,
        root_run_id=turn_run.langsmith_root_run_id,
        run_name=turn_run.run_name,
    )
    db.add(
        build_ai_run_cost_record(
            user_id=user_id,
            thread_id=thread.id,
            feature="coach_turn",
            source_type="coach_turn_run",
            source_id=turn_run.id,
            run_name=turn_run.run_name,
            trace_metadata=turn_trace_metadata,
            cost_snapshot=capture_langsmith_run_costs(turn_trace_metadata),
            source_metadata={
                "turn_seq_anchor": user_turn_seq,
                "tool_trace_count": len(execution.tool_traces),
                "attempt_count": turn_run.attempt_count,
            },
        )
    )
    await maybe_update_thread_memory(
        db,
        thread=thread,
        salient=is_salient_event(message=trimmed_message, proposal_changed=proposal_changed),
    )
    turn_payload["quota"] = quota
    turn_payload["provenance"] = _serialize_turn_run(turn_run)
    return turn_payload, created_events


async def _handle_accept_turn(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    proposal_id: uuid.UUID,
) -> tuple[dict, list]:
    proposal = await _get_proposal(db, user_id=user_id, proposal_id=proposal_id, thread_id=thread.id)
    if proposal.status == "accepted":
        projection = await _projection_payload(db, user_id=user_id, thread=thread)
        return {"status": "accepted", "changed": False, "quota": projection["quota"]}, []
    if proposal.status == "rejected":
        raise HTTPException(status_code=409, detail="Proposal already rejected")

    active_weekly = await _get_active_weekly_plan(db, user_id=user_id)
    if active_weekly.version != proposal.weekly_plan_version:
        raise HTTPException(status_code=409, detail="Weekly plan changed since proposal")

    weekly_plan = UiWeeklyPlan.model_validate(active_weekly.plan_data)
    raw_ops = proposal.ops.get("ops", []) if isinstance(proposal.ops, dict) else []
    parsed_ops = sanitize_ops(parse_patch_ops(raw_ops))
    updated_plan, changed = apply_ops(weekly_plan, parsed_ops)
    updated_payload = updated_plan.model_dump(mode="json")
    adaptive_usage = None
    if changed:
        adaptive_usage = await consume_adaptive_update(
            db,
            user_id=user_id,
            source_id=str(proposal.id),
            context=await get_local_usage_context(db, user_id=user_id),
        )
    if changed:
        active_weekly.version += 1
        updated_payload["version"] = active_weekly.version
        active_weekly.plan_data = updated_payload
        db.add(active_weekly)
    else:
        updated_payload["version"] = active_weekly.version

    proposal.status = "accepted"
    db.add(proposal)
    created_events = await append_coach_events(
        db,
        thread=thread,
        items=[
            (
                EVENT_PROPOSAL_ACCEPTED,
                "user",
                {
                    "proposal_id": str(proposal.id),
                    "changed": changed,
                    "weekly_version": active_weekly.version,
                },
            )
        ],
    )
    await maybe_update_thread_memory(db, thread=thread, salient=changed)
    quota = await get_coach_weekly_quota(db, user_id=user_id)
    return {
        "status": "accepted",
        "changed": changed,
        "weekly_plan": updated_payload,
        "weekly_version": active_weekly.version,
        "quota": quota,
        "adaptive_updates": adaptive_usage.model_dump(mode="json") if adaptive_usage is not None else None,
    }, created_events


async def _handle_reject_turn(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    proposal_id: uuid.UUID,
    reason: str,
) -> tuple[dict, list]:
    trimmed_reason = reason.strip()
    if not trimmed_reason:
        raise HTTPException(status_code=400, detail="reason is required for proposal_reject")

    proposal = await _get_proposal(db, user_id=user_id, proposal_id=proposal_id, thread_id=thread.id)
    if proposal.status == "accepted":
        raise HTTPException(status_code=409, detail="Proposal already accepted")
    if proposal.status == "rejected":
        quota = await get_coach_weekly_quota(db, user_id=user_id)
        return {"status": "rejected", "quota": quota}, []

    proposal.status = "rejected"
    proposal.rejection_reason = trimmed_reason[:500]
    db.add(proposal)
    created_events = await append_coach_events(
        db,
        thread=thread,
        items=[
            (
                EVENT_PROPOSAL_REJECTED,
                "user",
                {"proposal_id": str(proposal.id), "reason": proposal.rejection_reason},
            )
        ],
    )
    await maybe_update_thread_memory(db, thread=thread, salient=True)
    quota = await get_coach_weekly_quota(db, user_id=user_id)
    return {"status": "rejected", "quota": quota}, created_events


async def _run_turn_action(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    action: str,
    message: str | None,
    proposal_id: uuid.UUID | None,
    reason: str | None,
    quota_source_id: str,
    ui_context: dict[str, object] | None = None,
    status_emitter: StatusEmitter | None = None,
) -> tuple[dict, list]:
    if action == "text":
        return await _handle_text_turn(
            db,
            user_id=user_id,
            thread=thread,
            message=message or "",
            quota_source_id=quota_source_id,
            ui_context=ui_context,
            status_emitter=status_emitter,
        )
    if action == "proposal_accept":
        if proposal_id is None:
            raise HTTPException(status_code=400, detail="proposal_id is required for proposal_accept")
        return await _handle_accept_turn(
            db,
            user_id=user_id,
            thread=thread,
            proposal_id=proposal_id,
        )
    if action == "proposal_reject":
        if proposal_id is None:
            raise HTTPException(status_code=400, detail="proposal_id is required for proposal_reject")
        return await _handle_reject_turn(
            db,
            user_id=user_id,
            thread=thread,
            proposal_id=proposal_id,
            reason=reason or "",
        )
    if action == "recap":
        return await execute_recap_turn(
            db,
            user_id=user_id,
            thread=thread,
            status_emitter=status_emitter,
        )
    raise HTTPException(status_code=400, detail="action must be text, proposal_accept, proposal_reject, or recap")


async def post_coach_turn(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    action: str,
    idempotency_key: str,
    thread_id: uuid.UUID | None = None,
    message: str | None = None,
    proposal_id: uuid.UUID | None = None,
    reason: str | None = None,
    ui_context: dict[str, object] | None = None,
    status_emitter: StatusEmitter | None = None,
) -> dict:
    key = idempotency_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="idempotency_key is required")

    request_hash = _build_turn_request_hash(
        action=action,
        thread_id=thread_id,
        message=message,
        proposal_id=proposal_id,
        reason=reason,
        ui_context=ui_context,
    )
    existing_response, claimed = await _claim_idempotency_request(
        db,
        user_id=user_id,
        idempotency_key=key,
        request_hash=request_hash,
    )
    if existing_response is not None:
        return existing_response

    try:
        thread = await _resolve_thread_for_turn(
            db,
            user_id=user_id,
            action=action,
            thread_id=thread_id,
            proposal_id=proposal_id,
        )
        should_set_title_from_first_exchange = (
            action == "text" and thread.latest_seq == 0 and (thread.title is None or not thread.title.strip())
        )

        turn_payload, created_events = await _run_turn_action(
            db,
            user_id=user_id,
            thread=thread,
            action=action,
            message=message,
            proposal_id=proposal_id,
            reason=reason,
            quota_source_id=f"{user_id}:{key}",
            ui_context=ui_context,
            status_emitter=status_emitter if action in ("text", "recap") else None,
        )
        if should_set_title_from_first_exchange:
            await _maybe_set_thread_title_from_first_exchange(
                db,
                thread=thread,
                user_message=message,
                turn_payload=turn_payload,
            )

        projection = await _projection_payload(db, user_id=user_id, thread=thread)
        projection_payload = {
            "messages": projection["messages"],
            "quota": projection["quota"],
            "can_send_message": projection["can_send_message"],
            "coach_gate_message": projection["coach_gate_message"],
            "coach_gate_target": projection["coach_gate_target"],
            "has_pending_proposal": projection["has_pending_proposal"],
            "can_trigger_recap": projection["can_trigger_recap"],
            "training_provider_message": projection["training_provider_message"],
            "recap_gate_target": projection["recap_gate_target"],
            "pending_proposal_ids": projection["pending_proposal_ids"],
            "next_after_seq": projection["next_after_seq"],
        }
        response_payload = {
            "thread": projection["thread"],
            "events_appended": _event_stubs(created_events),
            "projection": projection_payload,
            "turn": turn_payload,
        }
        return await _complete_idempotency_request(
            db,
            user_id=user_id,
            idempotency_key=key,
            request_hash=request_hash,
            response_payload=response_payload,
        )
    except Exception:
        if claimed:
            await _fail_idempotency_request(
                db,
                user_id=user_id,
                idempotency_key=key,
                request_hash=request_hash,
            )
        raise


async def get_coach_thread_v2(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread_id: uuid.UUID | None = None,
    after_seq: int | None = None,
    limit: int = 200,
) -> dict:
    if thread_id is None:
        thread = await get_latest_active_coach_thread(db, user_id=user_id)
        if thread is None:
            anchor = compute_recap_week_anchor_utc()
            quota = await get_coach_weekly_quota(db, user_id=user_id, week_anchor_utc=anchor)
            recap_availability = await evaluate_weekly_recap_availability(db, user_id=user_id)
            usage_context = await get_local_usage_context(db, user_id=user_id)
            integrations_status = await load_integrations_status(db, user_id=user_id)
            can_send_message, coach_gate_message, coach_gate_target = resolve_coach_chat_gate_state(
                quota=quota,
            )
            can_trigger_recap, training_provider_message, recap_gate_target = resolve_recap_gate_state(
                recap_feature_enabled=has_weekly_recap_feature_access(usage_context),
                recap_window_open=recap_availability.allowed,
                integrations_status=integrations_status,
            )
            return {
                "thread": None,
                "messages": [],
                "quota": quota,
                "can_send_message": can_send_message,
                "coach_gate_message": coach_gate_message,
                "coach_gate_target": coach_gate_target,
                "has_pending_proposal": False,
                "can_trigger_recap": can_trigger_recap,
                "training_provider_message": training_provider_message,
                "recap_gate_target": recap_gate_target,
                "pending_proposal_ids": [],
                "next_after_seq": after_seq,
                "week_anchor_utc": anchor.astimezone(UTC).isoformat(),
            }
    else:
        thread = await get_coach_thread_by_id(db, user_id=user_id, thread_id=thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")

    projection = await _projection_payload(db, user_id=user_id, thread=thread, after_seq=after_seq, limit=limit)
    return {
        "thread": projection["thread"],
        "messages": projection["messages"],
        "quota": projection["quota"],
        "can_send_message": projection["can_send_message"],
        "coach_gate_message": projection["coach_gate_message"],
        "coach_gate_target": projection["coach_gate_target"],
        "has_pending_proposal": projection["has_pending_proposal"],
        "can_trigger_recap": projection["can_trigger_recap"],
        "training_provider_message": projection["training_provider_message"],
        "recap_gate_target": projection["recap_gate_target"],
        "pending_proposal_ids": projection["pending_proposal_ids"],
        "next_after_seq": projection["next_after_seq"],
        "week_anchor_utc": compute_recap_week_anchor_utc().astimezone(UTC).isoformat(),
    }


async def list_coach_threads_v2(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    threads = await list_coach_threads(
        db,
        user_id=user_id,
        limit=safe_limit + 1,
        offset=safe_offset,
    )
    has_more = len(threads) > safe_limit
    paged_threads = threads[:safe_limit]

    thread_ids = [thread.id for thread in paged_threads]
    events_by_thread: dict[str, list[dict]] = {str(tid): [] for tid in thread_ids}
    pending_proposals_by_thread: dict[str, bool] = {str(tid): False for tid in thread_ids}

    if thread_ids:
        all_events_result = await db.execute(
            select(CoachEvent)
            .where(CoachEvent.thread_id.in_(thread_ids))
            .order_by(CoachEvent.thread_id, CoachEvent.seq)
        )
        all_proposal_rows = await db.execute(
            select(CoachProposal.id, CoachProposal.thread_id, CoachProposal.status).where(
                CoachProposal.user_id == user_id,
                CoachProposal.thread_id.in_(thread_ids),
            )
        )
        proposal_status_by_thread: dict[str, dict[str, str]] = {str(tid): {} for tid in thread_ids}
        for proposal_id, thread_id, status in all_proposal_rows.all():
            proposal_status_by_thread[str(thread_id)][str(proposal_id)] = status
            if status == "pending":
                pending_proposals_by_thread[str(thread_id)] = True

        for event in all_events_result.scalars().all():
            tid = str(event.thread_id)
            serialized = serialize_thread_event(event, proposal_status_by_id=proposal_status_by_thread.get(tid, {}))
            if serialized is not None:
                events_by_thread[tid].append(serialized)
        events_by_thread = await hydrate_recap_messages_by_thread(
            db,
            user_id=user_id,
            messages_by_thread=events_by_thread,
        )

    return {
        "items": [
            {
                "id": str(thread.id),
                "status": thread.status,
                "title": thread.title,
                "latest_seq": thread.latest_seq,
                "created_at": thread.created_at.astimezone(UTC).isoformat(),
                "updated_at": thread.updated_at.astimezone(UTC).isoformat(),
                "messages": events_by_thread.get(str(thread.id), []),
                "has_pending_proposal": pending_proposals_by_thread.get(str(thread.id), False),
            }
            for thread in paged_threads
        ],
        "limit": safe_limit,
        "offset": safe_offset,
        "has_more": has_more,
        "next_offset": safe_offset + safe_limit if has_more else None,
    }


async def archive_coach_thread_v2(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
) -> dict:
    thread = await get_coach_thread_by_id(
        db,
        user_id=user_id,
        thread_id=thread_id,
        for_update=True,
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.status == THREAD_STATUS_ACTIVE:
        await maybe_update_thread_memory(db, thread=thread, force=True)
    archived = await archive_coach_thread(
        db,
        thread_id=thread_id,
        user_id=user_id,
    )
    # `updated_at` is DB-managed (`onupdate=func.now()`), so refresh explicitly in async
    # context to avoid lazy-loading it later (which raises MissingGreenlet).
    await db.refresh(archived, attribute_names=["updated_at", "status", "title", "latest_seq"])
    return {
        "thread": {
            "id": str(archived.id),
            "status": archived.status,
            "title": archived.title,
            "latest_seq": archived.latest_seq,
            "updated_at": archived.updated_at.astimezone(UTC).isoformat(),
        }
    }
