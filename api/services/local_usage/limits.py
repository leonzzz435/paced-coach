from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.job import AnalysisJob, JobStatus
from api.models.local_usage import LocalUsageEvent, LocalUsagePlanOverride
from api.services.full_run_policy import (
    evaluate_full_run_availability,
    get_latest_full_run_created_at,
)
from api.services.local_usage.schemas import (
    CoachMessageStatus,
    LocalUsageFeatures,
    LocalUsageStatusSnapshot,
    PlanGenerationStatus,
    UsageWindow,
)
from api.services.local_usage.usage import (
    FEATURE_ADAPTIVE_UPDATE,
    FEATURE_COACH_TURN,
    FEATURE_DAILY_SYNC,
    FEATURE_FULL_RUN,
    consume_window_usage,
    ensure_window_usage_available,
    get_initial_draft_plan_event,
    get_window_usage_snapshot,
    record_usage_event,
)
from api.services.local_usage_plans import (
    LOCAL_DEFAULT_USAGE_PLAN,
    LOCAL_EXTENDED_USAGE_PLAN,
    LocalUsagePlan,
    get_local_usage_plan_definition,
)
from core.task_timeouts import get_analysis_running_job_max_age_seconds

ACTIVE_LOCAL_PLAN_STATUSES = {"active", "enabled"}


@dataclass(frozen=True, init=False)
class LocalUsageContext:
    plan_override: LocalUsagePlanOverride | None
    selected_plan: LocalUsagePlan | None
    effective_plan: LocalUsagePlan
    tier: Literal["free", "extended"]
    has_access: bool

    def __init__(
        self,
        *,
        selected_plan: LocalUsagePlan | None,
        effective_plan: LocalUsagePlan,
        tier: Literal["free", "extended"],
        has_access: bool,
        plan_override: LocalUsagePlanOverride | None = None,
    ):
        object.__setattr__(self, "plan_override", plan_override)
        object.__setattr__(self, "selected_plan", selected_plan)
        object.__setattr__(self, "effective_plan", effective_plan)
        object.__setattr__(self, "tier", tier)
        object.__setattr__(self, "has_access", has_access)


@dataclass(frozen=True)
class InitialDraftPlanStatus:
    available: bool
    pending: bool
    consumed_at: datetime | None


@dataclass(frozen=True, init=False)
class PlanGenerationAccess:
    mode: Literal["dev_bypass", "extended", "free"]
    usage_context: LocalUsageContext | None = None
    initial_draft_claim_source_id: str | None = None

    def __init__(
        self,
        *,
        mode: Literal["dev_bypass", "extended", "free"],
        usage_context: LocalUsageContext | None = None,
        initial_draft_claim_source_id: str | None = None,
    ):
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "usage_context", usage_context)
        object.__setattr__(self, "initial_draft_claim_source_id", initial_draft_claim_source_id)


@dataclass(frozen=True)
class AdaptiveUpdateWindow:
    cycle_source_id: str
    window_start: datetime
    window_end: datetime


def is_local_usage_bypass_enabled(settings=None) -> bool:
    resolved_settings = settings or get_settings()
    dev_bypass = bool(getattr(resolved_settings, "local_usage_dev_bypass", False))
    if not dev_bypass:
        return False

    web_app_url = (os.getenv("WEB_APP_URL") or "").strip().lower()
    return web_app_url.startswith(("http://localhost", "http://127.0.0.1"))


def is_usage_safety_bypass_enabled(settings=None) -> bool:
    resolved_settings = settings or get_settings()
    if getattr(resolved_settings, "auth_mode", "local") == "local":
        return bool(getattr(resolved_settings, "local_usage_safety_bypass", False))
    return is_local_usage_bypass_enabled(resolved_settings)


def _now_utc(now: datetime | None = None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_status(raw_status: str | None) -> str:
    normalized = (raw_status or "").strip().lower()
    return normalized or "inactive"


def _period_window_for_plan_override(
    plan_override: LocalUsagePlanOverride | None,
    *,
    now: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    if plan_override is None:
        return None, None

    if plan_override.current_period_start is not None or plan_override.current_period_end is not None:
        return plan_override.current_period_start, plan_override.current_period_end

    current_time = _now_utc(now)
    return current_time, current_time


def _coach_message_not_limited_payload(
    *,
    window_start: datetime,
    window_end: datetime,
) -> CoachMessageStatus:
    return CoachMessageStatus(
        used=0,
        limit=None,
        remaining=None,
        window_start=window_start,
        window_end=window_end,
    )


def _coach_message_limited_payload(
    *,
    window_start: datetime,
    window_end: datetime,
    used: int,
    limit_value: int,
) -> CoachMessageStatus:
    safe_limit = max(limit_value, 0)
    safe_used = max(used, 0)
    return CoachMessageStatus(
        used=safe_used,
        limit=safe_limit,
        remaining=max(safe_limit - safe_used, 0),
        window_start=window_start,
        window_end=window_end,
    )


def _utc_day_window(*, now: datetime | None = None) -> tuple[datetime, datetime]:
    current_time = _now_utc(now)
    window_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    return window_start, window_start + timedelta(days=1)


async def get_local_usage_plan_override(db: AsyncSession, *, user_id: uuid.UUID) -> LocalUsagePlanOverride | None:
    row = await db.execute(select(LocalUsagePlanOverride).where(LocalUsagePlanOverride.user_id == user_id))
    return row.scalar_one_or_none()


def build_local_usage_context(plan_override: LocalUsagePlanOverride | None) -> LocalUsageContext:
    selected_plan = get_local_usage_plan_definition(plan_override.plan_key if plan_override is not None else None)
    normalized_status = _normalize_status(plan_override.status if plan_override is not None else None)
    has_access = plan_override is not None and normalized_status in ACTIVE_LOCAL_PLAN_STATUSES and selected_plan is not None
    effective_plan = selected_plan if has_access and selected_plan is not None else LOCAL_DEFAULT_USAGE_PLAN
    return LocalUsageContext(
        plan_override=plan_override,
        selected_plan=selected_plan,
        effective_plan=effective_plan,
        tier="extended" if has_access else "free",
        has_access=has_access,
    )


async def get_local_usage_context(db: AsyncSession, *, user_id: uuid.UUID) -> LocalUsageContext:
    return build_local_usage_context(await get_local_usage_plan_override(db, user_id=user_id))


def has_local_usage_access(context: LocalUsageContext, settings=None) -> bool:
    return is_local_usage_bypass_enabled(settings) or context.has_access


def has_weekly_recap_feature_access(context: LocalUsageContext, settings=None) -> bool:
    if is_local_usage_bypass_enabled(settings):
        return True
    return bool(context.effective_plan is not None and context.effective_plan.weekly_recap_included)


def require_local_usage_access(context: LocalUsageContext, settings=None):
    if has_local_usage_access(context, settings=settings):
        return
    raise HTTPException(status_code=403, detail="Feature unavailable in this local build")


def require_weekly_recap_access(context: LocalUsageContext, settings=None):
    if has_weekly_recap_feature_access(context, settings=settings):
        return
    raise HTTPException(status_code=403, detail="Weekly recap is not available")


def _coach_turn_exhausted_detail(context: LocalUsageContext) -> str:
    return "Daily coach message limit reached. Your coaching allowance resets tomorrow."


def _adaptive_update_exhausted_exception(context: LocalUsageContext) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail="Adaptive update limit reached for this training block. Generate a new training block to reset this limit.",
    )


def _draft_plan_status_from_event(event: LocalUsageEvent | None) -> InitialDraftPlanStatus:
    if event is None:
        return InitialDraftPlanStatus(available=True, pending=False, consumed_at=None)

    metadata = event.payload_metadata if isinstance(event.payload_metadata, dict) else {}
    state = str(metadata.get("state") or "consumed").strip().lower()
    if state == "pending":
        return InitialDraftPlanStatus(available=False, pending=True, consumed_at=None)
    return InitialDraftPlanStatus(available=False, pending=False, consumed_at=event.consumed_at)


async def get_initial_draft_plan_status(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> InitialDraftPlanStatus:
    return _draft_plan_status_from_event(await get_initial_draft_plan_event(db, user_id=user_id))


async def finalize_initial_draft_plan_claim(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_id: str,
    consumed_at: datetime | None = None,
) -> bool:
    event = await get_initial_draft_plan_event(db, user_id=user_id)
    if event is None:
        return False

    metadata = dict(event.payload_metadata or {})
    metadata["state"] = "consumed"
    metadata["analysis_job_id"] = source_id
    metadata["finalized_at"] = _now_utc(consumed_at).isoformat()
    event.payload_metadata = metadata
    event.consumed_at = _now_utc(consumed_at)
    db.add(event)
    return True


async def release_initial_draft_plan_claim(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> bool:
    event = await get_initial_draft_plan_event(db, user_id=user_id)
    if event is None:
        return False

    metadata = event.payload_metadata if isinstance(event.payload_metadata, dict) else {}
    state = str(metadata.get("state") or "").strip().lower()
    if state != "pending":
        return False

    await _delete_initial_draft_event(db, event=event)
    return True


async def _flush_if_supported(db: AsyncSession) -> None:
    flush = getattr(db, "flush", None)
    if flush is not None:
        await flush()


def _is_pending_initial_draft_event(event: LocalUsageEvent) -> bool:
    metadata = event.payload_metadata if isinstance(event.payload_metadata, dict) else {}
    state = str(metadata.get("state") or "").strip().lower()
    return state == "pending"


async def _delete_initial_draft_event(
    db: AsyncSession,
    *,
    event: LocalUsageEvent,
) -> None:
    await db.delete(event)
    await _flush_if_supported(db)


def _is_terminal_job_status(status: str | None) -> bool:
    return status in {JobStatus.COMPLETED.value, JobStatus.CANCELLED.value, JobStatus.FAILED.value}


def _mark_job_failed_for_stale_initial_claim(
    job: AnalysisJob,
    *,
    now: datetime,
) -> None:
    job.status = JobStatus.FAILED.value
    job.completed_at = now
    job.error_message = "Job timed out (exceeded maximum execution time)"


async def _find_latest_free_initial_job(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> AnalysisJob | None:
    rows = await db.execute(
        select(AnalysisJob).where(AnalysisJob.user_id == user_id).order_by(AnalysisJob.created_at.desc())
    )
    for job in rows.scalars().all():
        config = getattr(job, "config", None)
        if not isinstance(config, dict):
            continue
        if str(config.get("_plan_generation_access_mode") or "").strip().lower() == "free_initial":
            return job
    return None


async def _repair_stale_initial_draft_plan_claim(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> bool:
    event = await get_initial_draft_plan_event(db, user_id=user_id)
    if event is None:
        return False

    if not _is_pending_initial_draft_event(event):
        return False

    job = await _find_latest_free_initial_job(db, user_id=user_id)
    if job is None:
        await _delete_initial_draft_event(db, event=event)
        return True

    if _is_terminal_job_status(job.status):
        await _delete_initial_draft_event(db, event=event)
        return True

    if job.status != JobStatus.RUNNING.value:
        return False

    stale_threshold_seconds = get_analysis_running_job_max_age_seconds()
    if stale_threshold_seconds is None:
        return False

    current_time = _now_utc(now)
    age_seconds = (current_time - _now_utc(job.created_at)).total_seconds()
    if age_seconds <= stale_threshold_seconds:
        return False

    _mark_job_failed_for_stale_initial_claim(job, now=current_time)
    db.add(job)
    await _delete_initial_draft_event(db, event=event)
    return True


async def _find_active_plan_generation_job(db: AsyncSession, *, user_id: uuid.UUID) -> AnalysisJob | None:
    rows = await db.execute(
        select(AnalysisJob)
        .where(
            AnalysisJob.user_id == user_id,
            AnalysisJob.status.in_((JobStatus.PENDING.value, JobStatus.RUNNING.value)),
        )
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )
    return rows.scalar_one_or_none()


async def ensure_plan_generation_available(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> PlanGenerationAccess:
    settings = get_settings()
    if is_usage_safety_bypass_enabled(settings):
        return PlanGenerationAccess(mode="dev_bypass", usage_context=None)

    active_job = await _find_active_plan_generation_job(db, user_id=user_id)
    if active_job is not None:
        raise HTTPException(status_code=409, detail="Plan generation is already running.")

    context = await get_local_usage_context(db, user_id=user_id)
    plan = context.effective_plan
    cooldown_days = plan.plan_generation_cooldown_days
    cooldown_interval = timedelta(days=cooldown_days)
    availability = await evaluate_full_run_availability(
        db,
        user_id=user_id,
        now=now,
        min_interval=cooldown_interval,
    )

    if availability.allowed:
        return PlanGenerationAccess(
            mode="extended" if context.has_access else "free",
            usage_context=context,
        )

    next_allowed_at = availability.next_allowed_at.astimezone(UTC).isoformat() if availability.next_allowed_at else None
    if not context.has_access:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Local plan generation is limited to once every {cooldown_days} days. "
                f"Next allowed at {next_allowed_at}."
            ),
        )

    return PlanGenerationAccess(
        mode="extended",
        usage_context=context,
        initial_draft_claim_source_id=None,
    )


async def _get_adaptive_update_window(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> AdaptiveUpdateWindow | None:
    row = await db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id))
    active_weekly = row.scalar_one_or_none()
    if active_weekly is None:
        return None

    cycle_source_id = str(active_weekly.source_job_id)
    generation_row = await db.execute(
        select(LocalUsageEvent).where(
            LocalUsageEvent.user_id == user_id,
            LocalUsageEvent.feature_key == FEATURE_FULL_RUN,
            LocalUsageEvent.source_type == "analysis_job",
            LocalUsageEvent.source_id == cycle_source_id,
        )
    )
    generation_event = generation_row.scalar_one_or_none()
    window_start = _now_utc(generation_event.consumed_at if generation_event is not None else active_weekly.updated_at or now)
    return AdaptiveUpdateWindow(
        cycle_source_id=cycle_source_id,
        window_start=window_start,
        window_end=window_start + timedelta(days=28),
    )


async def get_adaptive_update_usage(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    context: LocalUsageContext | None = None,
    now: datetime | None = None,
) -> UsageWindow:
    settings = get_settings()
    current_time = _now_utc(now)
    if is_usage_safety_bypass_enabled(settings):
        return UsageWindow(
            used=0,
            limit=999,
            remaining=999,
            window_start=current_time,
            window_end=current_time,
        )

    resolved_context = context or await get_local_usage_context(db, user_id=user_id)
    window = await _get_adaptive_update_window(db, user_id=user_id, now=current_time)
    if window is None:
        return UsageWindow(
            used=0,
            limit=resolved_context.effective_plan.adaptive_updates_per_cycle_limit,
            remaining=resolved_context.effective_plan.adaptive_updates_per_cycle_limit,
            window_start=None,
            window_end=None,
        )

    return await get_window_usage_snapshot(
        db,
        user_id=user_id,
        feature_key=FEATURE_ADAPTIVE_UPDATE,
        window_start=window.window_start,
        window_end=window.window_end,
        limit_value=resolved_context.effective_plan.adaptive_updates_per_cycle_limit,
    )


async def consume_adaptive_update(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_id: str,
    context: LocalUsageContext | None = None,
    now: datetime | None = None,
) -> UsageWindow:
    settings = get_settings()
    if is_usage_safety_bypass_enabled(settings):
        return await get_adaptive_update_usage(db, user_id=user_id, context=context, now=now)

    resolved_context = context or await get_local_usage_context(db, user_id=user_id)
    window = await _get_adaptive_update_window(db, user_id=user_id, now=now)
    if window is None:
        raise HTTPException(status_code=409, detail="Adaptive updates require an active training block.")

    usage = await get_window_usage_snapshot(
        db,
        user_id=user_id,
        feature_key=FEATURE_ADAPTIVE_UPDATE,
        window_start=window.window_start,
        window_end=window.window_end,
        limit_value=resolved_context.effective_plan.adaptive_updates_per_cycle_limit,
    )
    if usage.remaining <= 0:
        raise _adaptive_update_exhausted_exception(resolved_context)

    exhausted_detail = str(_adaptive_update_exhausted_exception(resolved_context).detail)
    try:
        return await consume_window_usage(
            db,
            user_id=user_id,
            feature_key=FEATURE_ADAPTIVE_UPDATE,
            source_type="coach_proposal",
            source_id=source_id,
            window_start=window.window_start,
            window_end=window.window_end,
            limit_value=resolved_context.effective_plan.adaptive_updates_per_cycle_limit,
            exhausted_detail=exhausted_detail,
            metadata={"cycle_source_id": window.cycle_source_id},
        )
    except HTTPException as exc:
        if exc.status_code == 402:
            raise _adaptive_update_exhausted_exception(resolved_context) from exc
        raise


def is_proactive_daily_sync_enabled(context: LocalUsageContext) -> bool:
    return bool(
        context.has_access
        and context.effective_plan.proactive_daily_sync_enabled
    )


async def get_daily_sync_usage(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    context: LocalUsageContext | None = None,
    now: datetime | None = None,
) -> UsageWindow:
    settings = get_settings()
    current_time = _now_utc(now)
    if is_usage_safety_bypass_enabled(settings):
        return UsageWindow(
            used=0,
            limit=999,
            remaining=999,
            window_start=current_time,
            window_end=current_time,
        )

    resolved_context = context or await get_local_usage_context(db, user_id=user_id)
    window_start, window_end = _utc_day_window(now=current_time)

    return await get_window_usage_snapshot(
        db,
        user_id=user_id,
        feature_key=FEATURE_DAILY_SYNC,
        window_start=window_start,
        window_end=window_end,
        limit_value=resolved_context.effective_plan.daily_sync_limit,
    )


async def ensure_daily_sync_available(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    context: LocalUsageContext | None = None,
    now: datetime | None = None,
) -> UsageWindow:
    settings = get_settings()
    if is_usage_safety_bypass_enabled(settings):
        return await get_daily_sync_usage(db, user_id=user_id, context=context, now=now)

    resolved_context = context or await get_local_usage_context(db, user_id=user_id)
    window_start, window_end = _utc_day_window(now=now)
    return await ensure_window_usage_available(
        db,
        user_id=user_id,
        feature_key=FEATURE_DAILY_SYNC,
        window_start=window_start,
        window_end=window_end,
        limit_value=resolved_context.effective_plan.daily_sync_limit,
        exhausted_detail="Daily sync already used today. Try again tomorrow.",
    )


async def consume_daily_sync(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_id: str,
    context: LocalUsageContext | None = None,
    now: datetime | None = None,
) -> UsageWindow:
    settings = get_settings()
    if is_usage_safety_bypass_enabled(settings):
        return await get_daily_sync_usage(db, user_id=user_id, context=context, now=now)

    resolved_context = context or await get_local_usage_context(db, user_id=user_id)
    window_start, window_end = _utc_day_window(now=now)
    return await consume_window_usage(
        db,
        user_id=user_id,
        feature_key=FEATURE_DAILY_SYNC,
        source_type="daily_update_run",
        source_id=source_id,
        window_start=window_start,
        window_end=window_end,
        limit_value=resolved_context.effective_plan.daily_sync_limit,
        exhausted_detail="Daily sync already used today. Try again tomorrow.",
    )


async def get_coach_turn_quota(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    context: LocalUsageContext | None = None,
    week_anchor_utc: datetime | None = None,
) -> CoachMessageStatus:
    settings = get_settings()
    anchor, window_end = _utc_day_window(now=week_anchor_utc)
    if is_usage_safety_bypass_enabled(settings):
        return _coach_message_not_limited_payload(window_start=anchor, window_end=window_end)

    resolved_context = context or await get_local_usage_context(db, user_id=user_id)
    usage = await get_window_usage_snapshot(
        db,
        user_id=user_id,
        feature_key=FEATURE_COACH_TURN,
        window_start=anchor,
        window_end=window_end,
        limit_value=resolved_context.effective_plan.coach_turn_daily_limit,
    )
    return _coach_message_limited_payload(
        window_start=anchor,
        window_end=window_end,
        used=usage.used,
        limit_value=usage.limit,
    )


async def ensure_coach_turn_available(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    context: LocalUsageContext | None = None,
    week_anchor_utc: datetime | None = None,
) -> CoachMessageStatus:
    settings = get_settings()
    anchor, window_end = _utc_day_window(now=week_anchor_utc)
    if is_usage_safety_bypass_enabled(settings):
        return _coach_message_not_limited_payload(window_start=anchor, window_end=window_end)

    resolved_context = context or await get_local_usage_context(db, user_id=user_id)
    usage = await get_window_usage_snapshot(
        db,
        user_id=user_id,
        feature_key=FEATURE_COACH_TURN,
        window_start=anchor,
        window_end=window_end,
        limit_value=resolved_context.effective_plan.coach_turn_daily_limit,
    )
    if usage.remaining <= 0:
        raise HTTPException(
            status_code=402,
            detail=_coach_turn_exhausted_detail(resolved_context),
        )
    return _coach_message_limited_payload(
        window_start=anchor,
        window_end=window_end,
        used=usage.used,
        limit_value=usage.limit,
    )


async def consume_coach_turn(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_id: str,
    context: LocalUsageContext | None = None,
    week_anchor_utc: datetime | None = None,
) -> CoachMessageStatus:
    settings = get_settings()
    anchor, window_end = _utc_day_window(now=week_anchor_utc)
    if is_usage_safety_bypass_enabled(settings):
        return _coach_message_not_limited_payload(window_start=anchor, window_end=window_end)

    resolved_context = context or await get_local_usage_context(db, user_id=user_id)
    usage = await consume_window_usage(
        db,
        user_id=user_id,
        feature_key=FEATURE_COACH_TURN,
        source_type="coach_turn",
        source_id=source_id,
        window_start=anchor,
        window_end=window_end,
        limit_value=resolved_context.effective_plan.coach_turn_daily_limit,
        exhausted_detail=_coach_turn_exhausted_detail(resolved_context),
    )
    return _coach_message_limited_payload(
        window_start=anchor,
        window_end=window_end,
        used=usage.used,
        limit_value=usage.limit,
    )


async def record_full_run_consumption(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_id: str,
    consumed_at: datetime | None = None,
) -> bool:
    return await record_usage_event(
        db,
        user_id=user_id,
        feature_key=FEATURE_FULL_RUN,
        source_type="analysis_job",
        source_id=source_id,
        consumed_at=consumed_at,
    )


async def build_local_usage_status_snapshot(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> LocalUsageStatusSnapshot:
    settings = get_settings()
    current_time = _now_utc(now)
    if is_usage_safety_bypass_enabled(settings):
        return LocalUsageStatusSnapshot(
            tier="dev_bypass",
            status="active",
            plan_key="dev_bypass",
            plan_name="Dev bypass",
            current_period_start=current_time,
            current_period_end=current_time,
            plan_generation=PlanGenerationStatus(
                allowed=True,
                last_generated_at=None,
                next_allowed_at=None,
                cooldown_days=LOCAL_EXTENDED_USAGE_PLAN.plan_generation_cooldown_days,
            ),
            adaptive_updates=await get_adaptive_update_usage(db, user_id=user_id, now=current_time),
            daily_sync=await get_daily_sync_usage(db, user_id=user_id, now=current_time),
            coach_messages=await get_coach_turn_quota(db, user_id=user_id),
            features=LocalUsageFeatures(
                weekly_recap_included=True,
                proactive_daily_sync_enabled=False,
                extended_access=True,
            ),
        )

    context = await get_local_usage_context(db, user_id=user_id)
    plan_override = context.plan_override
    plan = context.effective_plan
    cooldown_days = plan.plan_generation_cooldown_days
    cooldown_interval = timedelta(days=cooldown_days)
    last_full_run_at = await get_latest_full_run_created_at(db, user_id=user_id)
    availability = await evaluate_full_run_availability(
        db, user_id=user_id, now=current_time, min_interval=cooldown_interval
    )
    current_period_start, current_period_end = _period_window_for_plan_override(plan_override, now=current_time)

    return LocalUsageStatusSnapshot(
        tier=context.tier,
        status=_normalize_status(plan_override.status if plan_override is not None else "inactive"),
        plan_key=(plan_override.plan_key if plan_override is not None else None) or plan.plan_key,
        plan_name=(
            (
                (plan_override.plan_name or context.selected_plan.plan_name)
                if plan_override is not None and context.selected_plan is not None
                else (plan_override.plan_name if plan_override is not None else None)
            )
            if context.has_access
            else plan.plan_name
        ),
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        plan_generation=PlanGenerationStatus(
            allowed=availability.allowed,
            last_generated_at=last_full_run_at,
            next_allowed_at=availability.next_allowed_at,
            cooldown_days=cooldown_days,
        ),
        adaptive_updates=await get_adaptive_update_usage(db, user_id=user_id, context=context, now=current_time),
        daily_sync=await get_daily_sync_usage(db, user_id=user_id, context=context, now=current_time),
        coach_messages=await get_coach_turn_quota(db, user_id=user_id, context=context),
        features=LocalUsageFeatures(
            weekly_recap_included=bool(context.effective_plan.weekly_recap_included),
            proactive_daily_sync_enabled=is_proactive_daily_sync_enabled(context),
            extended_access=context.has_access,
        ),
    )
