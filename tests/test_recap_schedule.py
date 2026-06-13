from datetime import UTC, datetime, timedelta

from core.recap_schedule import compute_recap_week_anchor_utc, get_recap_window_utc


def test_compute_recap_week_anchor_utc_uses_same_sunday_after_cutoff():
    now = datetime(2026, 2, 22, 21, 0, tzinfo=UTC)  # Sunday
    anchor = compute_recap_week_anchor_utc(now)
    assert anchor == datetime(2026, 2, 22, 20, 0, tzinfo=UTC)


def test_compute_recap_week_anchor_utc_uses_previous_week_before_cutoff():
    now = datetime(2026, 2, 22, 19, 0, tzinfo=UTC)  # Sunday
    anchor = compute_recap_week_anchor_utc(now)
    assert anchor == datetime(2026, 2, 15, 20, 0, tzinfo=UTC)


def test_get_recap_window_utc_returns_full_week():
    anchor = datetime(2026, 2, 22, 20, 0, tzinfo=UTC)
    start, end = get_recap_window_utc(anchor)
    assert end == anchor
    assert start == anchor - timedelta(days=7)

