import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import suppress
from time import monotonic
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import DB_SKIP_AUTO_COMMIT_FLAG, get_current_user, get_db
from api.services.coach_turn import archive_coach_thread_v2, get_coach_thread_v2, list_coach_threads_v2, post_coach_turn

router = APIRouter()
_COACH_TURN_STREAM_HEARTBEAT_SECONDS = 5.0
_COACH_TURN_STREAM_TIMEOUT_SECONDS = 600.0


class CoachTurnUiContext(BaseModel):
    source: Literal["today_mission"]
    day_id: str = Field(..., min_length=1, max_length=64)
    week_id: str | None = Field(default=None, min_length=1, max_length=64)
    date: str | None = Field(default=None, min_length=1, max_length=32)
    day_label: str | None = Field(default=None, min_length=1, max_length=120)
    workout_title: str | None = Field(default=None, min_length=1, max_length=120)


class CoachTurnRequest(BaseModel):
    thread_id: uuid.UUID | None = None
    action: str = Field(..., pattern="^(text|proposal_accept|proposal_reject)$")
    message: str | None = Field(default=None, min_length=1, max_length=2000)
    proposal_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    idempotency_key: str = Field(..., min_length=1, max_length=120)
    ui_context: CoachTurnUiContext | None = None


def _sse_event(event_name: str, payload: dict[str, object] | None = None) -> str:
    lines = [f"event: {event_name}"]
    if payload is not None:
        serialized = json.dumps(payload, ensure_ascii=False)
        lines.extend([f"data: {line}" for line in serialized.splitlines() or ["{}"]])
    lines.append("")
    return "\n".join(lines) + "\n"


def _wants_sse_response(request: Request) -> bool:
    accept_header = request.headers.get("accept", "")
    return "text/event-stream" in accept_header.lower()


def _turn_ui_context_payload(payload: CoachTurnRequest) -> dict[str, object] | None:
    return payload.ui_context.model_dump(mode="json") if payload.ui_context else None


async def _post_coach_turn_payload(
    *,
    payload: CoachTurnRequest,
    db: AsyncSession,
    user_id: uuid.UUID,
    status_emitter=None,
):
    return await post_coach_turn(
        db,
        user_id=user_id,
        action=payload.action,
        thread_id=payload.thread_id,
        message=payload.message,
        proposal_id=payload.proposal_id,
        reason=payload.reason,
        idempotency_key=payload.idempotency_key,
        ui_context=_turn_ui_context_payload(payload),
        status_emitter=status_emitter,
    )


def _disable_auto_commit(db: AsyncSession) -> None:
    db.info[DB_SKIP_AUTO_COMMIT_FLAG] = True


async def _cancel_turn_task(turn_task: asyncio.Task) -> None:
    if turn_task.done():
        return
    turn_task.cancel()
    with suppress(asyncio.CancelledError):
        await turn_task


def _stream_timeout_reached(*, now: float, stream_started_at: float) -> bool:
    return (
        _COACH_TURN_STREAM_TIMEOUT_SECONDS is not None
        and now - stream_started_at > _COACH_TURN_STREAM_TIMEOUT_SECONDS
    )


async def _stream_timeout_error(db: AsyncSession, turn_task: asyncio.Task) -> str:
    await _cancel_turn_task(turn_task)
    await db.rollback()
    _disable_auto_commit(db)
    return _sse_event(
        "error",
        {
            "detail": "Coach turn timed out while generating a response",
            "status_code": 504,
        },
    )


async def _stream_failure_error(db: AsyncSession, turn_task: asyncio.Task, exc: Exception) -> str:
    await _cancel_turn_task(turn_task)
    await db.rollback()
    _disable_auto_commit(db)
    if isinstance(exc, HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Coach turn failed"
        return _sse_event("error", {"detail": detail, "status_code": exc.status_code})
    return _sse_event("error", {"detail": "Coach turn failed", "status_code": 500})


async def _next_status_or_heartbeat_event(
    status_queue: asyncio.Queue[dict[str, object]],
    *,
    now: float,
    last_status_emit_at: float,
) -> tuple[str | None, float]:
    try:
        status_payload = await asyncio.wait_for(status_queue.get(), timeout=0.2)
    except TimeoutError:
        if now - last_status_emit_at < _COACH_TURN_STREAM_HEARTBEAT_SECONDS:
            return None, last_status_emit_at
        return (
            _sse_event(
                "status",
                {
                    "step": "thinking",
                    "message": "Still working on your coaching response...",
                },
            ),
            now,
        )
    return _sse_event("status", status_payload), monotonic()


async def _stream_turn_events(
    *,
    payload: CoachTurnRequest,
    db: AsyncSession,
    user_id: uuid.UUID,
) -> AsyncIterator[str]:
    status_queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
    stream_started_at = monotonic()
    last_status_emit_at = stream_started_at

    async def emit_status(status_payload: dict[str, object]):
        await status_queue.put(status_payload)

    turn_task = asyncio.create_task(
        _post_coach_turn_payload(
            payload=payload,
            db=db,
            user_id=user_id,
            status_emitter=emit_status,
        )
    )

    try:
        while not turn_task.done() or not status_queue.empty():
            now = monotonic()
            if _stream_timeout_reached(now=now, stream_started_at=stream_started_at):
                yield await _stream_timeout_error(db, turn_task)
                yield _sse_event("done")
                return

            event, last_status_emit_at = await _next_status_or_heartbeat_event(
                status_queue,
                now=now,
                last_status_emit_at=last_status_emit_at,
            )
            if event is None:
                continue
            yield event

        turn_payload = await turn_task
        await db.commit()
        _disable_auto_commit(db)
        yield _sse_event("result", turn_payload)
    except HTTPException as exc:
        yield await _stream_failure_error(db, turn_task, exc)
    except Exception as exc:
        yield await _stream_failure_error(db, turn_task, exc)
    finally:
        await _cancel_turn_task(turn_task)
        if turn_task.cancelled() and not db.info.get(DB_SKIP_AUTO_COMMIT_FLAG):
            await db.rollback()
            _disable_auto_commit(db)
    yield _sse_event("done")


@router.post("/turn")
async def post_turn(
    payload: CoachTurnRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    if payload.action != "text" or not _wants_sse_response(request):
        return await _post_coach_turn_payload(payload=payload, db=db, user_id=user_id)

    return StreamingResponse(
        _stream_turn_events(payload=payload, db=db, user_id=user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/thread")
async def get_thread(
    thread_id: uuid.UUID | None = None,
    after_seq: int | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await get_coach_thread_v2(db, user_id=user_id, thread_id=thread_id, after_seq=after_seq, limit=limit)


@router.get("/threads")
async def list_threads(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await list_coach_threads_v2(db, user_id=user_id, limit=limit, offset=offset)


@router.post("/thread/{thread_id}/archive")
async def archive_thread(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await archive_coach_thread_v2(db, user_id=user_id, thread_id=thread_id)
