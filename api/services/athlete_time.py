from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.athlete_profile import AthleteProfile

DEFAULT_ATHLETE_TIMEZONE = "UTC"
TimezoneSource = Literal["profile", "fallback_utc"]


@dataclass(frozen=True)
class AthleteTimeContext:
    timezone: str
    timezone_source: TimezoneSource
    now_local: datetime
    now_local_iso: str
    today_local_date: date


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_timezone_name(timezone_name: str | None) -> tuple[str, TimezoneSource]:
    if timezone_name:
        trimmed_name = timezone_name.strip()
        if trimmed_name:
            try:
                ZoneInfo(trimmed_name)
            except ZoneInfoNotFoundError:
                pass
            else:
                return trimmed_name, "profile"
    return DEFAULT_ATHLETE_TIMEZONE, "fallback_utc"


def local_date_for_datetime(value: datetime, *, timezone_name: str) -> date:
    timezone = ZoneInfo(timezone_name)
    return as_utc(value).astimezone(timezone).date()


def local_midnight_utc(*, local_date: date, timezone_name: str) -> datetime:
    timezone = ZoneInfo(timezone_name)
    return datetime.combine(local_date, time.min, tzinfo=timezone).astimezone(UTC)


def recap_first_anchor_utc(*, last_full_run_at: datetime, timezone_name: str) -> datetime:
    first_anchor_local_date = local_date_for_datetime(last_full_run_at, timezone_name=timezone_name) + timedelta(days=7)
    return local_midnight_utc(local_date=first_anchor_local_date, timezone_name=timezone_name)


def current_recap_anchor_utc(
    *,
    last_full_run_at: datetime,
    timezone_name: str,
    now: datetime | None = None,
) -> datetime | None:
    now_utc = as_utc(now or datetime.now(UTC))
    first_anchor_local_date = local_date_for_datetime(last_full_run_at, timezone_name=timezone_name) + timedelta(days=7)
    current_local_date = local_date_for_datetime(now_utc, timezone_name=timezone_name)
    if current_local_date < first_anchor_local_date:
        return None

    elapsed_days = (current_local_date - first_anchor_local_date).days
    current_anchor_local_date = first_anchor_local_date + timedelta(days=(elapsed_days // 7) * 7)
    return local_midnight_utc(local_date=current_anchor_local_date, timezone_name=timezone_name)


def recap_window_utc(*, anchor_utc: datetime, timezone_name: str) -> tuple[datetime, datetime]:
    anchor_local_date = local_date_for_datetime(anchor_utc, timezone_name=timezone_name)
    window_start_local_date = anchor_local_date - timedelta(days=7)
    window_start_utc = local_midnight_utc(local_date=window_start_local_date, timezone_name=timezone_name)
    window_end_utc = local_midnight_utc(local_date=anchor_local_date, timezone_name=timezone_name)
    return window_start_utc, window_end_utc


def next_recap_anchor_utc(*, anchor_utc: datetime, timezone_name: str) -> datetime:
    anchor_local_date = local_date_for_datetime(anchor_utc, timezone_name=timezone_name)
    next_anchor_local_date = anchor_local_date + timedelta(days=7)
    return local_midnight_utc(local_date=next_anchor_local_date, timezone_name=timezone_name)


async def get_athlete_timezone(db: AsyncSession, *, user_id) -> tuple[str, TimezoneSource]:
    row = await db.execute(select(AthleteProfile.profile).where(AthleteProfile.user_id == user_id))
    profile = row.scalar_one_or_none()
    preferences = profile.get("preferences", {}) if isinstance(profile, dict) else {}
    timezone_name = preferences.get("timezone") if isinstance(preferences, dict) else None
    return normalize_timezone_name(timezone_name if isinstance(timezone_name, str) else None)


async def get_athlete_time_context(
    db: AsyncSession,
    *,
    user_id,
    now: datetime | None = None,
) -> AthleteTimeContext:
    timezone_name, timezone_source = await get_athlete_timezone(db, user_id=user_id)
    timezone = ZoneInfo(timezone_name)
    now_utc = as_utc(now or datetime.now(UTC))
    now_local = now_utc.astimezone(timezone)
    return AthleteTimeContext(
        timezone=timezone_name,
        timezone_source=timezone_source,
        now_local=now_local,
        now_local_iso=now_local.isoformat(),
        today_local_date=now_local.date(),
    )
