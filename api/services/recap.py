from __future__ import annotations

import html
import logging
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.coach_event import CoachEvent
from api.models.coach_proposal import CoachProposal
from api.models.coach_thread import CoachThread
from api.models.weekly_recap_run import WeeklyRecapRun
from api.services.ai_run_costs import (
    AiRunCostSnapshot,
    AiTraceMetadata,
    build_ai_run_cost_record,
    capture_langsmith_run_costs,
    finish_ai_root_trace,
    start_ai_root_trace,
)
from api.services.coach_event_store import (
    EVENT_COACH_MESSAGE,
    EVENT_RECAP_NARRATIVE,
    append_coach_events,
)
from api.services.coach_patch_ops import apply_ops, sanitize_ops
from api.services.coach_quota import get_coach_weekly_quota
from api.services.coach_thread_titles import derive_weekly_recap_thread_title
from api.services.connected_coaching import assert_connected_coaching_available
from api.services.full_run_policy import WeeklyRecapAvailability, evaluate_weekly_recap_availability
from api.services.html_sanitizer import sanitize_html
from api.services.integration_status import load_integrations_status
from api.services.local_usage import get_local_usage_context
from api.services.ongoing_tools import build_ongoing_tool_registry
from services.ai.langgraph.schemas.ui_blocks import UiHtmlBlock, UiWeeklyPlan
from services.ai.recap import WeeklyRecapNarrative, generate_weekly_recap_narrative

logger = logging.getLogger(__name__)
StatusEmitter = Callable[[dict[str, object]], object]
_HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
_SENTENCE_BREAK_PATTERN = re.compile(r"[.!?](?=\s|$)")
_CLAUSE_BREAK_PATTERN = re.compile(r"[,;:](?=\s|$)")


def _sanitize_recap_blocks(blocks: list[UiHtmlBlock]) -> list[UiHtmlBlock]:
    sanitized: list[UiHtmlBlock] = []
    seen: set[str] = set()
    for block in blocks:
        key = block.key
        if key in seen:
            suffix = 1
            while f"{key}-{suffix}" in seen:
                suffix += 1
            key = f"{key}-{suffix}"
        seen.add(key)
        sanitized.append(
            block.model_copy(
                update={
                    "key": key,
                    "content_html": sanitize_html(block.content_html),
                    "tone": block.tone if block.variant == "callout" else None,
                }
            )
        )
    return sanitized


def _sanitize_recap_payload(payload: WeeklyRecapNarrative) -> WeeklyRecapNarrative:
    return payload.model_copy(
        update={
            "this_week_blocks": _sanitize_recap_blocks(payload.this_week_blocks),
            "looking_ahead_blocks": _sanitize_recap_blocks(payload.looking_ahead_blocks),
            "optional_proposal_ops": sanitize_ops(payload.optional_proposal_ops),
        }
    )


def _truncate_preview_text(preview: str, *, max_chars: int) -> str:
    if len(preview) <= max_chars:
        return preview

    sentence_min_chars = max(48, int(max_chars * 0.35))
    sentence_breaks = [
        match.end()
        for match in _SENTENCE_BREAK_PATTERN.finditer(preview[: max_chars + 1])
        if match.end() >= sentence_min_chars
    ]
    if sentence_breaks:
        return preview[: sentence_breaks[-1]].rstrip()

    clause_min_chars = max(72, int(max_chars * 0.45))
    clause_breaks = [
        match.start()
        for match in _CLAUSE_BREAK_PATTERN.finditer(preview[: max_chars + 1])
        if match.start() >= clause_min_chars
    ]
    if clause_breaks:
        return f"{preview[: clause_breaks[-1]].rstrip()}..."

    candidate = preview[: max_chars + 1]
    word_break = candidate.rfind(" ")
    if word_break >= max(32, int(max_chars * 0.6)):
        candidate = candidate[:word_break]
    else:
        candidate = preview[:max_chars]
    return f"{candidate.rstrip(' ,;:')}..."


def _extract_html_text(content_html: str) -> str:
    normalized = html.unescape(_HTML_TAG_PATTERN.sub(" ", content_html)).replace("\n", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def _build_html_preview(content_html: str, *, max_chars: int = 180) -> str:
    preview = _extract_html_text(content_html)
    return _truncate_preview_text(preview, max_chars=max_chars)


def extract_recap_summary_preview(recap_payload: object) -> str | None:
    if not isinstance(recap_payload, dict):
        return None
    narrative = recap_payload.get("narrative")
    if not isinstance(narrative, dict):
        return None

    for section_name in ("this_week_blocks", "looking_ahead_blocks"):
        section_blocks = narrative.get(section_name)
        if not isinstance(section_blocks, list):
            continue
        for raw_block in section_blocks:
            if not isinstance(raw_block, dict):
                continue
            title = str(raw_block.get("title") or "").strip()
            if title:
                return title
            content_html = raw_block.get("content_html")
            if isinstance(content_html, str) and content_html.strip():
                return _build_html_preview(content_html, max_chars=220)
    return None


def extract_recap_action_preview(
    recap_payload: object,
    *,
    exclude: str | None = None,
) -> str | None:
    if not isinstance(recap_payload, dict):
        return None
    narrative = recap_payload.get("narrative")
    if not isinstance(narrative, dict):
        return None

    normalized_exclude = str(exclude or "").strip()

    for section_name in ("looking_ahead_blocks", "this_week_blocks"):
        section_blocks = narrative.get(section_name)
        if not isinstance(section_blocks, list):
            continue
        for raw_block in section_blocks:
            if not isinstance(raw_block, dict):
                continue
            title = str(raw_block.get("title") or "").strip()
            if title and title != normalized_exclude:
                return title
            content_html = raw_block.get("content_html")
            if isinstance(content_html, str) and content_html.strip():
                preview = _build_html_preview(content_html, max_chars=220)
                if preview and preview != normalized_exclude:
                    return preview
    return None


def serialize_recap_run(run: WeeklyRecapRun) -> dict:
    payload = run.recap_payload if isinstance(run.recap_payload, dict) else {}
    return {
        "run_id": str(run.id),
        "user_id": str(run.user_id),
        "week_anchor_utc": run.week_anchor_utc.astimezone(UTC).isoformat(),
        "status": run.status,
        "trigger_source": run.trigger_source,
        "proposal_id": str(run.proposal_id) if run.proposal_id else None,
        "created_at": run.created_at.astimezone(UTC).isoformat(),
        "updated_at": run.updated_at.astimezone(UTC).isoformat(),
        "narrative": payload.get("narrative", {}),
        "base_weekly_plan": payload.get("base_weekly_plan"),
        "preview_weekly_plan": payload.get("preview_weekly_plan"),
        "ops": payload.get("ops", []),
        "follow_up_question": run.follow_up_question,
        "athlete_response": run.athlete_response,
    }


async def _refresh_recap_run_for_serialization(
    db: AsyncSession,
    *,
    run: WeeklyRecapRun,
) -> WeeklyRecapRun:
    await db.refresh(run)
    return run


async def get_recap_thread_id(
    db: AsyncSession,
    *,
    run: WeeklyRecapRun,
) -> str | None:
    if run.recap_event_id is not None:
        event_row = await db.execute(
            select(CoachEvent.thread_id).where(CoachEvent.id == run.recap_event_id)
        )
        thread_id = event_row.scalar_one_or_none()
        if thread_id is not None:
            return str(thread_id)

    if run.proposal_id is not None:
        proposal_row = await db.execute(
            select(CoachProposal.thread_id).where(CoachProposal.id == run.proposal_id)
        )
        thread_id = proposal_row.scalar_one_or_none()
        if thread_id is not None:
            return str(thread_id)
    return None


async def _is_pending_recap_proposal(
    db: AsyncSession,
    *,
    proposal_id: uuid.UUID,
) -> bool:
    proposal_row = await db.execute(
        select(CoachProposal.status).where(CoachProposal.id == proposal_id)
    )
    status = proposal_row.scalar_one_or_none()
    return str(status or "").strip().lower() == "pending"


def resolve_recap_pending_action(
    *,
    has_unanswered_follow_up: bool,
    has_pending_proposal: bool,
) -> str:
    if has_unanswered_follow_up and has_pending_proposal:
        return "follow_up_and_proposal"
    if has_unanswered_follow_up:
        return "follow_up"
    if has_pending_proposal:
        return "proposal"
    return "none"


async def get_recap_pending_action(
    db: AsyncSession,
    *,
    run: WeeklyRecapRun,
) -> str:
    has_unanswered_follow_up = bool(run.follow_up_question and not run.athlete_response)
    has_pending_proposal = bool(run.proposal_id and await _is_pending_recap_proposal(db, proposal_id=run.proposal_id))
    return resolve_recap_pending_action(
        has_unanswered_follow_up=has_unanswered_follow_up,
        has_pending_proposal=has_pending_proposal,
    )


async def _get_recap_run_for_anchor(
    db: AsyncSession, *, user_id: uuid.UUID, week_anchor_utc: datetime
) -> WeeklyRecapRun | None:
    row = await db.execute(
        select(WeeklyRecapRun).where(
            WeeklyRecapRun.user_id == user_id,
            WeeklyRecapRun.week_anchor_utc == week_anchor_utc,
        )
    )
    return row.scalar_one_or_none()


async def _prepare_pending_recap_run(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    week_anchor_utc: datetime,
    existing: WeeklyRecapRun | None,
) -> tuple[WeeklyRecapRun, bool]:
    run = existing or WeeklyRecapRun(
        user_id=user_id,
        week_anchor_utc=week_anchor_utc,
        trigger_source="manual",
    )
    run.status = "pending"
    run.error_message = None
    run.trigger_source = "manual"
    db.add(run)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info(
            "Concurrent recap run detected for user=%s anchor=%s, returning existing",
            user_id,
            week_anchor_utc,
        )
        existing_run = await _get_recap_run_for_anchor(db, user_id=user_id, week_anchor_utc=week_anchor_utc)
        if existing_run is None:
            raise HTTPException(status_code=409, detail="Concurrent recap run conflict") from None
        return existing_run, True
    return run, False


async def _get_active_weekly_plan_for_recap(
    db: AsyncSession, *, user_id: uuid.UUID, run: WeeklyRecapRun
) -> tuple[ActiveWeeklyPlan, UiWeeklyPlan]:
    weekly_row = await db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id))
    active_weekly = weekly_row.scalar_one_or_none()
    if not active_weekly:
        run.status = "failed"
        run.error_message = "No active weekly plan found"
        db.add(run)
        await db.flush()
        raise HTTPException(status_code=404, detail="No active weekly plan found")
    return active_weekly, UiWeeklyPlan.model_validate(active_weekly.plan_data)


async def _generate_recap_narrative(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
    run: WeeklyRecapRun,
    previous_follow_up: dict[str, str] | None = None,
    status_emitter: StatusEmitter | None = None,
) -> tuple[WeeklyRecapNarrative, dict, AiTraceMetadata | None, AiRunCostSnapshot]:
    ai_trace = start_ai_root_trace(
        run_name="weekly_recap",
        feature="weekly_recap",
        user_id=str(user_id),
        thread_id=None,
        inputs={
            "week_start_utc": window_start.isoformat(),
            "week_end_utc": window_end.isoformat(),
            "source_run_id": str(run.id),
        },
        tags=["agent:weekly_recap"],
        metadata={
            "source_type": "weekly_recap_run",
            "source_id": str(run.id),
            "trigger_source": "manual",
        },
    )
    try:
        if status_emitter is not None:
            import inspect as _inspect

            status_result = status_emitter({"step": "fetching_data", "message": "Fetching your training data..."})
            if _inspect.isawaitable(status_result):
                await status_result

        async with build_ongoing_tool_registry(db, user_id=user_id) as tool_registry:
            if status_emitter is not None:
                status_result = status_emitter(
                    {"step": "generating_recap", "message": "Generating your weekly recap..."}
                )
                if _inspect.isawaitable(status_result):
                    await status_result

            with ai_trace.context_manager():
                narrative = await generate_weekly_recap_narrative(
                    tool_registry=tool_registry,
                    week_start_iso=window_start.isoformat(),
                    week_end_iso=window_end.isoformat(),
                    trigger_source="manual",
                    previous_follow_up=previous_follow_up,
                    invoke_config={
                        "run_name": "weekly_recap",
                        "tags": [
                            "agent:weekly_recap",
                            "feature:weekly_recap",
                            f"user:{user_id}",
                        ],
                        "metadata": {
                            "user_id": str(user_id),
                            "week_start_utc": window_start.isoformat(),
                            "week_end_utc": window_end.isoformat(),
                            "trigger_source": "manual",
                        },
                    },
                )
            finish_ai_root_trace(
                ai_trace,
                outputs={
                    "proposal_ops_count": len(narrative.optional_proposal_ops),
                    "this_week_block_count": len(narrative.this_week_blocks),
                    "looking_ahead_block_count": len(narrative.looking_ahead_blocks),
                    "follow_up_question": bool(narrative.follow_up_question),
                },
            )
            observability = tool_registry.get_observability_snapshot()
    except Exception as exc:
        finish_ai_root_trace(ai_trace, error=exc)
        run.status = "failed"
        run.error_message = str(exc)
        db.add(run)
        await db.flush()
        raise
    return (
        _sanitize_recap_payload(narrative),
        observability,
        ai_trace.trace_metadata(),
        capture_langsmith_run_costs(ai_trace.trace_metadata()),
    )


async def _create_optional_recap_proposal(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
    active_weekly: ActiveWeeklyPlan,
    current_plan: UiWeeklyPlan,
    narrative: WeeklyRecapNarrative,
) -> tuple[uuid.UUID | None, dict | None, bool]:
    if not narrative.optional_proposal_ops:
        return None, None, False

    preview_plan, changed = apply_ops(current_plan, narrative.optional_proposal_ops)
    proposal_row = CoachProposal(
        user_id=user_id,
        thread_id=thread_id,
        weekly_plan_version=active_weekly.version,
        assistant_message="Weekly recap proposes plan adaptations based on this week's execution.",
        ops={"ops": [op.model_dump(mode="json") for op in narrative.optional_proposal_ops]},
        origin="weekly_recap",
        status="pending",
    )
    db.add(proposal_row)
    await db.flush()
    return proposal_row.id, preview_plan.model_dump(mode="json"), changed


async def _append_recap_narrative_event(
    db: AsyncSession, *, run: WeeklyRecapRun, thread: CoachThread
) -> list[CoachEvent]:
    if run.recap_event_id is not None:
        return []
    recap_events = await append_coach_events(
        db,
        thread=thread,
        items=[(EVENT_RECAP_NARRATIVE, "coach", {"recap": serialize_recap_run(run)})],
    )
    run.recap_event_id = recap_events[0].id
    db.add(run)
    await db.flush()
    return recap_events


async def get_latest_answered_recap_follow_up(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, str] | None:
    row = await db.execute(
        select(WeeklyRecapRun)
        .where(
            WeeklyRecapRun.user_id == user_id,
            WeeklyRecapRun.status == "completed",
            WeeklyRecapRun.follow_up_question.is_not(None),
            WeeklyRecapRun.athlete_response.is_not(None),
        )
        .order_by(WeeklyRecapRun.updated_at.desc())
        .limit(1)
    )
    run = row.scalar_one_or_none()
    if run is None or not run.follow_up_question or not run.athlete_response:
        return None
    return {
        "question": run.follow_up_question,
        "response": run.athlete_response,
    }


def _recap_unavailable_detail(availability: WeeklyRecapAvailability) -> str:
    if availability.reason == "no_full_run":
        return "Weekly recap is unavailable until a full analysis run exists."
    if availability.reason == "window_not_open":
        next_allowed_at = (
            availability.next_allowed_at.astimezone(UTC).isoformat() if availability.next_allowed_at is not None else None
        )
        return f"Weekly recap is available every 7 days after full run creation. Next allowed at {next_allowed_at}."
    if availability.reason == "already_ran_in_window":
        next_allowed_at = (
            availability.next_allowed_at.astimezone(UTC).isoformat() if availability.next_allowed_at is not None else None
        )
        return f"Weekly recap already ran in this 7-day window. Next allowed at {next_allowed_at}."
    return "Weekly recap is currently unavailable."


async def get_latest_weekly_recap_report(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, object]:
    row = await db.execute(
        select(WeeklyRecapRun)
        .where(
            WeeklyRecapRun.user_id == user_id,
            WeeklyRecapRun.status == "completed",
        )
        .order_by(WeeklyRecapRun.updated_at.desc())
        .limit(1)
    )
    run = row.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Weekly recap not found")

    run = await _refresh_recap_run_for_serialization(db, run=run)
    return {
        "recap": serialize_recap_run(run),
        "thread_id": await get_recap_thread_id(db, run=run),
        "summary_preview": extract_recap_summary_preview(run.recap_payload),
        "pending_action": await get_recap_pending_action(db, run=run),
    }


async def execute_recap_turn(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread: CoachThread,
    status_emitter: StatusEmitter | None = None,
) -> tuple[dict, list[CoachEvent]]:
    recap_usage_context = await get_local_usage_context(db, user_id=user_id)
    availability = await evaluate_weekly_recap_availability(db, user_id=user_id)
    integrations_status = await load_integrations_status(db, user_id=user_id)

    if availability.existing_run_id is not None:
        existing_row = await db.execute(
            select(WeeklyRecapRun).where(
                WeeklyRecapRun.id == availability.existing_run_id,
                WeeklyRecapRun.user_id == user_id,
            )
        )
        existing_run = existing_row.scalar_one_or_none()
        if existing_run is not None:
            existing_run = await _refresh_recap_run_for_serialization(db, run=existing_run)
            return {"kind": "recap", "recap": serialize_recap_run(existing_run)}, []

    if not availability.allowed:
        raise HTTPException(status_code=409, detail=_recap_unavailable_detail(availability))

    assert_connected_coaching_available(
        feature_enabled=bool(recap_usage_context.effective_plan.weekly_recap_included),
        integrations_status=integrations_status,
        locked_message="Weekly recap is not available on this plan.",
    )

    anchor = availability.current_anchor_utc
    if anchor is None or availability.window_start is None or availability.window_end is None:
        raise HTTPException(status_code=409, detail="Weekly recap window is not ready")

    existing = await _get_recap_run_for_anchor(db, user_id=user_id, week_anchor_utc=anchor)
    if existing and existing.status in {"completed", "pending"}:
        existing = await _refresh_recap_run_for_serialization(db, run=existing)
        return {"kind": "recap", "recap": serialize_recap_run(existing)}, []

    run, was_concurrent = await _prepare_pending_recap_run(
        db,
        user_id=user_id,
        week_anchor_utc=anchor,
        existing=existing,
    )
    if was_concurrent and run.status in {"completed", "pending"}:
        run = await _refresh_recap_run_for_serialization(db, run=run)
        return {"kind": "recap", "recap": serialize_recap_run(run)}, []

    active_weekly, current_plan = await _get_active_weekly_plan_for_recap(db, user_id=user_id, run=run)

    previous_follow_up = await get_latest_answered_recap_follow_up(db, user_id=user_id)
    narrative, observability, ai_trace_metadata, ai_cost_snapshot = await _generate_recap_narrative(
        db,
        user_id=user_id,
        window_start=availability.window_start,
        window_end=availability.window_end,
        run=run,
        previous_follow_up=previous_follow_up,
        status_emitter=status_emitter,
    )
    quota = await get_coach_weekly_quota(db, user_id=user_id, week_anchor_utc=anchor)

    db.add(
        build_ai_run_cost_record(
            user_id=user_id,
            thread_id=thread.id,
            feature="weekly_recap",
            source_type="weekly_recap_run",
            source_id=run.id,
            run_name="weekly_recap",
            trace_metadata=ai_trace_metadata,
            cost_snapshot=ai_cost_snapshot,
            source_metadata={
                "week_anchor_utc": anchor.isoformat(),
                "week_start_utc": availability.window_start.isoformat(),
                "week_end_utc": availability.window_end.isoformat(),
                "trigger_source": "manual",
            },
        )
    )

    if not thread.title:
        thread.title = derive_weekly_recap_thread_title(anchor, timezone=availability.timezone)
        db.add(thread)
        await db.flush()

    proposal_id, preview_weekly_payload, changed = await _create_optional_recap_proposal(
        db,
        user_id=user_id,
        thread_id=thread.id,
        active_weekly=active_weekly,
        current_plan=current_plan,
        narrative=narrative,
    )

    run.status = "completed"
    run.error_message = None
    run.follow_up_question = narrative.follow_up_question or None
    run.context_snapshot = {
        "week_window": {
            "start_utc": availability.window_start.isoformat(),
            "end_utc": availability.window_end.isoformat(),
        },
        "athlete_timezone": availability.timezone,
        "tool_observability": observability,
    }
    run.proposal_id = proposal_id
    run.recap_payload = {
        "narrative": {
            "this_week_blocks": [block.model_dump(mode="json") for block in narrative.this_week_blocks],
            "looking_ahead_blocks": [block.model_dump(mode="json") for block in narrative.looking_ahead_blocks],
        },
        "base_weekly_plan": current_plan.model_dump(mode="json"),
        "ops": [op.model_dump(mode="json") for op in narrative.optional_proposal_ops],
        "preview_weekly_plan": preview_weekly_payload,
        "changed": changed,
    }
    db.add(run)
    await db.flush()
    run = await _refresh_recap_run_for_serialization(db, run=run)

    created_events: list[CoachEvent] = []

    recap_events = await _append_recap_narrative_event(db, run=run, thread=thread)
    created_events.extend(recap_events)

    if narrative.follow_up_question:
        follow_up_events = await append_coach_events(
            db,
            thread=thread,
            items=[(EVENT_COACH_MESSAGE, "coach", {"text": narrative.follow_up_question})],
        )
        created_events.extend(follow_up_events)

    run = await _refresh_recap_run_for_serialization(db, run=run)
    turn_payload = {
        "kind": "recap",
        "recap": serialize_recap_run(run),
        "quota": quota,
    }
    return turn_payload, created_events
