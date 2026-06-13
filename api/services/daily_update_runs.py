from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from api.models.daily_update_run import DailyUpdateRun
from core.task_timeouts import get_daily_update_pending_max_age_seconds

_STALE_DAILY_UPDATE_ERROR = "Daily sync did not finish. Please retry."


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def fail_stale_pending_daily_update_run(
    db: AsyncSession,
    *,
    run: DailyUpdateRun | None,
    now: datetime | None = None,
) -> bool:
    if run is None:
        return False
    if str(run.status or "").strip().lower() != "pending":
        return False

    max_age_seconds = get_daily_update_pending_max_age_seconds()
    if max_age_seconds is None:
        return False

    last_progress_at = getattr(run, "updated_at", None) or getattr(run, "created_at", None)
    if not isinstance(last_progress_at, datetime):
        return False

    current_time = _to_utc(now or datetime.now(UTC))
    if current_time - _to_utc(last_progress_at) <= timedelta(seconds=max_age_seconds):
        return False

    run.status = "failed"
    run.error_message = _STALE_DAILY_UPDATE_ERROR
    await db.commit()
    return True
