from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

WEEKLY_RECAP_WEEKDAY = 6  # Sunday
WEEKLY_RECAP_HOUR_UTC = 20
WEEKLY_RECAP_MINUTE_UTC = 0


def compute_recap_week_anchor_utc(now_utc: datetime | None = None) -> datetime:
    """Return the latest recap anchor at or before `now_utc`.

    Anchor definition:
    - Fixed UTC schedule
    - Sunday at 20:00 UTC
    """
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    days_since_sunday = (now.weekday() - WEEKLY_RECAP_WEEKDAY) % 7
    sunday_date = (now - timedelta(days=days_since_sunday)).date()
    anchor = datetime.combine(
        sunday_date,
        time(hour=WEEKLY_RECAP_HOUR_UTC, minute=WEEKLY_RECAP_MINUTE_UTC, tzinfo=UTC),
    )
    if now < anchor:
        anchor -= timedelta(days=7)
    return anchor


def get_recap_window_utc(anchor_utc: datetime) -> tuple[datetime, datetime]:
    """Return [start, end] datetimes for the weekly recap window in UTC."""
    end = anchor_utc.astimezone(UTC)
    start = end - timedelta(days=7)
    return start, end

