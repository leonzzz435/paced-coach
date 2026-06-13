from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.local_usage import LocalUsageEvent
from api.models.weekly_recap_run import WeeklyRecapRun
from api.services.athlete_time import (
    DEFAULT_ATHLETE_TIMEZONE,
    as_utc,
    current_recap_anchor_utc,
    get_athlete_timezone,
    next_recap_anchor_utc,
    recap_first_anchor_utc,
    recap_window_utc,
)
from api.services.local_usage.usage import FEATURE_FULL_RUN

FULL_RUN_MIN_INTERVAL = timedelta(weeks=4)
WEEKLY_RECAP_INTERVAL = timedelta(days=7)
_RECAP_ACTIVE_STATUSES = ("pending", "completed")


@dataclass(frozen=True)
class FullRunAvailability:
    allowed: bool
    last_run_at: datetime | None
    next_allowed_at: datetime | None


@dataclass(frozen=True)
class WeeklyRecapAvailability:
    allowed: bool
    reason: str
    last_full_run_at: datetime | None
    current_anchor_utc: datetime | None
    timezone: str
    window_start: datetime | None
    window_end: datetime | None
    next_allowed_at: datetime | None
    existing_run_id: uuid.UUID | None


async def get_latest_full_run_created_at(db: AsyncSession, *, user_id: uuid.UUID) -> datetime | None:
    row = await db.execute(
        select(LocalUsageEvent.consumed_at)
        .where(
            LocalUsageEvent.user_id == user_id,
            LocalUsageEvent.feature_key == FEATURE_FULL_RUN,
            LocalUsageEvent.source_type == "analysis_job",
        )
        .order_by(LocalUsageEvent.consumed_at.desc())
        .limit(1)
    )
    latest_raw: object | None = row.scalar_one_or_none()
    if latest_raw is None:
        return None
    if isinstance(latest_raw, datetime):
        return as_utc(latest_raw)
    created_at = getattr(latest_raw, "created_at", None)
    if isinstance(created_at, datetime):
        return as_utc(created_at)
    consumed_at = getattr(latest_raw, "consumed_at", None)
    if isinstance(consumed_at, datetime):
        return as_utc(consumed_at)
    return None


async def evaluate_full_run_availability(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
    min_interval: timedelta | None = None,
) -> FullRunAvailability:
    now_utc = as_utc(now or datetime.now(UTC))
    interval = min_interval or FULL_RUN_MIN_INTERVAL
    last_run_at = await get_latest_full_run_created_at(db, user_id=user_id)
    if last_run_at is None:
        return FullRunAvailability(allowed=True, last_run_at=None, next_allowed_at=None)
    next_allowed_at = last_run_at + interval
    return FullRunAvailability(
        allowed=now_utc >= next_allowed_at,
        last_run_at=last_run_at,
        next_allowed_at=next_allowed_at,
    )


async def evaluate_weekly_recap_availability(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> WeeklyRecapAvailability:
    now_utc = as_utc(now or datetime.now(UTC))
    last_full_run_at = await get_latest_full_run_created_at(db, user_id=user_id)
    if last_full_run_at is None:
        return WeeklyRecapAvailability(
            allowed=False,
            reason="no_full_run",
            last_full_run_at=None,
            current_anchor_utc=None,
            timezone=DEFAULT_ATHLETE_TIMEZONE,
            window_start=None,
            window_end=None,
            next_allowed_at=None,
            existing_run_id=None,
        )
    timezone_name, _timezone_source = await get_athlete_timezone(db, user_id=user_id)

    current_anchor = current_recap_anchor_utc(
        last_full_run_at=last_full_run_at,
        timezone_name=timezone_name,
        now=now_utc,
    )
    if current_anchor is None:
        first_anchor = recap_first_anchor_utc(last_full_run_at=last_full_run_at, timezone_name=timezone_name)
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=last_full_run_at,
            current_anchor_utc=None,
            timezone=timezone_name,
            window_start=None,
            window_end=None,
            next_allowed_at=first_anchor,
            existing_run_id=None,
        )

    window_start, window_end = recap_window_utc(anchor_utc=current_anchor, timezone_name=timezone_name)

    existing_row = await db.execute(
        select(WeeklyRecapRun.id)
        .where(
            WeeklyRecapRun.user_id == user_id,
            WeeklyRecapRun.status.in_(_RECAP_ACTIVE_STATUSES),
            WeeklyRecapRun.week_anchor_utc == current_anchor,
        )
        .order_by(WeeklyRecapRun.updated_at.desc())
        .limit(1)
    )
    existing_run_id = existing_row.scalar_one_or_none()
    if existing_run_id is not None:
        return WeeklyRecapAvailability(
            allowed=False,
            reason="already_ran_in_window",
            last_full_run_at=last_full_run_at,
            current_anchor_utc=current_anchor,
            timezone=timezone_name,
            window_start=window_start,
            window_end=window_end,
            next_allowed_at=next_recap_anchor_utc(anchor_utc=current_anchor, timezone_name=timezone_name),
            existing_run_id=existing_run_id,
        )

    return WeeklyRecapAvailability(
        allowed=True,
        reason="eligible",
        last_full_run_at=last_full_run_at,
        current_anchor_utc=current_anchor,
        timezone=timezone_name,
        window_start=window_start,
        window_end=window_end,
        next_allowed_at=None,
        existing_run_id=None,
    )
