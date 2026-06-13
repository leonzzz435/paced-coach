import logging
import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Settings, get_settings
from api.deps import get_current_user, get_db
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.ai_run_cost import AiRunCost
from api.models.coach_proposal import CoachProposal
from api.models.daily_update_run import DailyUpdateRun
from api.services.ai_run_costs import (
    build_ai_run_cost_record,
    capture_langsmith_run_costs,
    finish_ai_root_trace,
    start_ai_root_trace,
)
from api.services.athlete_time import get_athlete_time_context
from api.services.coach_event_store import EVENT_PROPOSAL_CREATED, append_coach_events, get_or_create_coach_thread
from api.services.coach_patch_ops import apply_ops, sanitize_ops
from api.services.connected_coaching import assert_connected_coaching_available
from api.services.daily_sync_sources import extract_daily_sync_sources
from api.services.daily_update_runs import fail_stale_pending_daily_update_run
from api.services.dashboard_state import compose_day_override
from api.services.html_sanitizer import sanitize_html
from api.services.integration_status import load_integrations_status
from api.services.local_usage import (
    LocalUsageContext,
    consume_daily_sync,
    ensure_daily_sync_available,
    get_local_usage_context,
    is_usage_safety_bypass_enabled,
)
from api.services.ongoing_tools import build_ongoing_tool_registry
from services.ai.daily.daily_update_agent import generate_daily_update_narrative
from services.ai.daily.schemas import DailyUpdateNarrative
from services.ai.langgraph.schemas.ui_blocks import UiHtmlBlock, UiKpi, UiWeeklyPlan

logger = logging.getLogger(__name__)

router = APIRouter()


class DailyUpdateRunRequest(BaseModel):
    athlete_check_in: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional subjective athlete check-in for today's daily coaching sync.",
    )


def _normalize_athlete_check_in(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _sanitize_daily_blocks(blocks: list[UiHtmlBlock]) -> list[UiHtmlBlock]:
    sanitized: list[UiHtmlBlock] = []
    seen_keys: set[str] = set()
    for block in blocks:
        key = block.key
        if key in seen_keys:
            suffix = 1
            while f"{key}-{suffix}" in seen_keys:
                suffix += 1
            key = f"{key}-{suffix}"
        seen_keys.add(key)
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


def _sanitize_daily_kpis(kpis: list[UiKpi]) -> list[UiKpi]:
    sanitized: list[UiKpi] = []
    seen_ids: set[str] = set()
    for kpi in kpis:
        kpi_id = kpi.kpi_id.strip() or "dashboard-kpi"
        if kpi_id in seen_ids:
            suffix = 1
            while f"{kpi_id}-{suffix}" in seen_ids:
                suffix += 1
            kpi_id = f"{kpi_id}-{suffix}"
        seen_ids.add(kpi_id)
        sanitized.append(kpi.model_copy(update={"kpi_id": kpi_id}))
    return sanitized[:6]


def _sanitize_daily_payload(payload: DailyUpdateNarrative) -> DailyUpdateNarrative:
    return payload.model_copy(
        update={
            "dashboard_kpis": _sanitize_daily_kpis(payload.dashboard_kpis),
            "today_focus_blocks": _sanitize_daily_blocks(payload.today_focus_blocks),
            "optional_proposal_ops": sanitize_ops(payload.optional_proposal_ops),
        }
    )


async def _run_daily_update_agent(
    *,
    db: AsyncSession,
    user_id: uuid.UUID,
    daily_run: DailyUpdateRun,
    target_date_iso: str,
    current_plan: UiWeeklyPlan,
    athlete_check_in: str | None,
) -> tuple[DailyUpdateNarrative, dict, list[str], dict, AiRunCost]:
    ai_trace = start_ai_root_trace(
        run_name="daily_update",
        feature="daily_update",
        user_id=str(user_id),
        thread_id=None,
        inputs={
            "target_date": target_date_iso,
            "trigger_source": "dashboard_widget",
            "source_run_id": str(daily_run.id),
            "has_athlete_check_in": athlete_check_in is not None,
        },
        tags=["agent:daily_update"],
        metadata={
            "source_type": "daily_update_run",
            "source_id": str(daily_run.id),
            "target_date": target_date_iso,
        },
    )
    try:
        async with build_ongoing_tool_registry(db, user_id=user_id) as tool_registry:
            prefetched_recovery_readiness = await tool_registry.get_recovery_readiness_signals(days=7)
            sources_used = extract_daily_sync_sources(prefetched_recovery_readiness)
            with ai_trace.context_manager():
                narrative = _sanitize_daily_payload(
                    await generate_daily_update_narrative(
                        tool_registry=tool_registry,
                        target_date_iso=target_date_iso,
                        trigger_source="dashboard_widget",
                        athlete_check_in=athlete_check_in,
                        prefetched_recovery_readiness=prefetched_recovery_readiness,
                        prefetched_weekly_plan=current_plan.model_dump(mode="json"),
                        invoke_config={
                            "run_name": "daily_update",
                            "tags": [
                                "agent:daily_update",
                                "feature:daily_update",
                                f"user:{user_id}",
                            ],
                            "metadata": {
                                "user_id": str(user_id),
                                "target_date": target_date_iso,
                                "trigger_source": "dashboard_widget",
                            },
                        },
                    )
                )
            finish_ai_root_trace(
                ai_trace,
                outputs={
                    "proposal_ops_count": len(narrative.optional_proposal_ops),
                    "dashboard_kpi_count": len(narrative.dashboard_kpis),
                    "focus_block_count": len(narrative.today_focus_blocks),
                },
            )
            return (
                narrative,
                tool_registry.get_observability_snapshot(),
                sources_used,
                prefetched_recovery_readiness,
                build_ai_run_cost_record(
                    user_id=user_id,
                    thread_id=None,
                    feature="daily_update",
                    source_type="daily_update_run",
                    source_id=daily_run.id,
                    run_name="daily_update",
                    trace_metadata=ai_trace.trace_metadata(),
                    cost_snapshot=capture_langsmith_run_costs(ai_trace.trace_metadata()),
                    source_metadata={
                        "target_date": target_date_iso,
                        "trigger_source": "dashboard_widget",
                        "has_athlete_check_in": athlete_check_in is not None,
                    },
                ),
            )
    except Exception as exc:
        finish_ai_root_trace(ai_trace, error=exc)
        raise


async def _prepare_daily_run(
    *,
    db: AsyncSession,
    user_id: uuid.UUID,
    target_date: date,
    settings: Settings,
) -> tuple[ActiveWeeklyPlan, LocalUsageContext | None, DailyUpdateRun]:
    existing_row = await db.execute(
        select(DailyUpdateRun).where(
            DailyUpdateRun.user_id == user_id,
            DailyUpdateRun.target_date == target_date,
        )
    )
    existing_run = existing_row.scalar_one_or_none()
    existing_status = str(existing_run.status or "").strip().lower() if existing_run is not None else ""
    if existing_status == "pending" and await fail_stale_pending_daily_update_run(db, run=existing_run):
        existing_status = str(existing_run.status or "").strip().lower() if existing_run is not None else ""
    if existing_status in {"done", "completed"}:
        raise HTTPException(
            status_code=429,
            detail="Daily update already run for today. Check the dashboard for the latest insights.",
        )
    if existing_status == "pending":
        raise HTTPException(status_code=409, detail="Daily update is already running for today.")

    weekly_row = await db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id))
    active_weekly = weekly_row.scalar_one_or_none()
    if active_weekly is None:
        raise HTTPException(status_code=409, detail="Daily sync requires an active weekly plan.")

    usage_context = None
    if not is_usage_safety_bypass_enabled(settings):
        usage_context = await get_local_usage_context(db, user_id=user_id)
        await ensure_daily_sync_available(db, user_id=user_id, context=usage_context)

    integrations_status = await load_integrations_status(db, user_id=user_id, settings=settings)
    assert_connected_coaching_available(
        feature_enabled=True,
        integrations_status=integrations_status,
        locked_message="Daily coaching requires a connected training or recovery source.",
    )

    daily_run = existing_run or DailyUpdateRun(
        user_id=user_id,
        target_date=target_date,
        trigger_source="manual",
    )
    daily_run.status = "pending"
    daily_run.error_message = None
    daily_run.trigger_source = "manual"
    daily_run.context_snapshot = None
    daily_run.update_payload = None
    daily_run.proposal_id = None
    db.add(daily_run)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Daily update is already running for today.") from exc
    await db.refresh(daily_run)

    return active_weekly, usage_context, daily_run


async def _create_daily_proposal_if_needed(
    *,
    db: AsyncSession,
    user_id: uuid.UUID,
    active_weekly,
    current_plan: UiWeeklyPlan,
    narrative: DailyUpdateNarrative,
    daily_run: DailyUpdateRun,
) -> tuple[uuid.UUID | None, dict | None, uuid.UUID | None]:
    if not narrative.optional_proposal_ops:
        return None, None, None

    preview_plan, _changed = apply_ops(current_plan, narrative.optional_proposal_ops)
    preview_plan_dump = preview_plan.model_dump(mode="json")

    thread = await get_or_create_coach_thread(db, user_id=user_id)
    proposal_row = CoachProposal(
        user_id=user_id,
        thread_id=thread.id,
        weekly_plan_version=active_weekly.version,
        assistant_message="I've reviewed your latest recovery metrics and recommend the following daily adjustments.",
        ops={"ops": [op.model_dump(mode="json") for op in narrative.optional_proposal_ops]},
        origin="daily_update",
        status="pending",
    )
    db.add(proposal_row)
    await db.flush()
    daily_run.proposal_id = proposal_row.id

    await append_coach_events(
        db,
        thread=thread,
        items=[
            (
                EVENT_PROPOSAL_CREATED,
                "coach",
                {
                    "proposal_id": str(proposal_row.id),
                    "assistant_message": proposal_row.assistant_message,
                    "ops": [op.model_dump(mode="json") for op in narrative.optional_proposal_ops],
                    "base_weekly_plan": current_plan.model_dump(mode="json"),
                    "preview_weekly_plan": preview_plan_dump,
                    "origin": proposal_row.origin,
                    "status": proposal_row.status,
                },
            )
        ],
    )
    return proposal_row.id, preview_plan_dump, thread.id


@router.post("/run")
async def run_daily_update(
    request: DailyUpdateRunRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    settings = get_settings()
    athlete_time = await get_athlete_time_context(db, user_id=user_id)
    target_date = athlete_time.today_local_date
    target_date_iso = target_date.isoformat()
    athlete_check_in = _normalize_athlete_check_in(request.athlete_check_in if request else None)
    active_weekly, usage_context, daily_run = await _prepare_daily_run(
        db=db,
        user_id=user_id,
        target_date=target_date,
        settings=settings,
    )

    current_plan = UiWeeklyPlan.model_validate(active_weekly.plan_data)
    thread_id: uuid.UUID | None = None
    ai_cost_record = None

    try:
        (
            narrative,
            observability,
            sources_used,
            prefetched_recovery_readiness,
            ai_cost_record,
        ) = await _run_daily_update_agent(
            db=db,
            user_id=user_id,
            daily_run=daily_run,
            target_date_iso=target_date_iso,
            current_plan=current_plan,
            athlete_check_in=athlete_check_in,
        )
        db.add(ai_cost_record)

        proposal_id, preview_plan_dump, thread_id = await _create_daily_proposal_if_needed(
            db=db,
            user_id=user_id,
            active_weekly=active_weekly,
            current_plan=current_plan,
            narrative=narrative,
            daily_run=daily_run,
        )

        day_override = compose_day_override(
            weekly_plan=current_plan,
            target_date_iso=target_date_iso,
            today_focus_blocks=narrative.today_focus_blocks,
        )

        daily_run.status = "completed"
        if not is_usage_safety_bypass_enabled(settings):
            await consume_daily_sync(
                db,
                user_id=user_id,
                source_id=str(daily_run.id),
                context=usage_context,
            )
        daily_run.context_snapshot = {
            "athlete_time": {
                "timezone": athlete_time.timezone,
                "timezone_source": athlete_time.timezone_source,
                "today_local_date": target_date_iso,
                "now_local_iso": athlete_time.now_local_iso,
            },
            "prefetched_recovery_readiness": prefetched_recovery_readiness,
            "athlete_check_in": athlete_check_in,
            "tool_observability": observability,
        }
        daily_run.update_payload = narrative.model_dump(mode="json")
        db.add(daily_run)
        await db.commit()
        await db.refresh(daily_run)

        return {
            "status": "success",
            "run_id": str(daily_run.id),
            "sources_used": sources_used,
            "proposal_id": str(proposal_id) if proposal_id else None,
            "thread_id": str(thread_id) if thread_id else None,
            "preview_weekly_plan": preview_plan_dump,
            "narrative": daily_run.update_payload,
            "today_override": day_override.model_dump(mode="json") if day_override is not None else None,
        }
    except HTTPException as exc:
        await db.rollback()
        daily_run.status = "failed"
        daily_run.error_message = str(exc.detail)
        db.add(daily_run)
        if ai_cost_record is not None:
            db.add(ai_cost_record)
        await db.commit()
        raise
    except Exception as exc:
        await db.rollback()
        daily_run.status = "failed"
        daily_run.error_message = str(exc)
        db.add(daily_run)
        if ai_cost_record is not None:
            db.add(ai_cost_record)
        await db.commit()
        logger.exception("Daily update failed for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to generate daily update.") from exc
