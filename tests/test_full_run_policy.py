import uuid
from datetime import UTC, datetime, timedelta

import pytest

from api.services import full_run_policy


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDb:
    def __init__(self, responses):
        self._responses = iter(responses)

    async def execute(self, _statement):
        return next(self._responses)


@pytest.mark.asyncio
async def test_evaluate_full_run_availability_allows_when_no_prior_runs():
    availability = await full_run_policy.evaluate_full_run_availability(
        _FakeDb([_FakeResult(None)]),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        now=datetime(2026, 2, 28, 12, 0, tzinfo=UTC),
    )

    assert availability.allowed is True
    assert availability.last_run_at is None
    assert availability.next_allowed_at is None


@pytest.mark.asyncio
async def test_evaluate_full_run_availability_blocks_within_4_weeks():
    last_run_at = datetime(2026, 2, 15, 9, 30, tzinfo=UTC)
    now = datetime(2026, 2, 28, 12, 0, tzinfo=UTC)
    availability = await full_run_policy.evaluate_full_run_availability(
        _FakeDb([_FakeResult(last_run_at)]),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        now=now,
    )

    assert availability.allowed is False
    assert availability.last_run_at == last_run_at
    assert availability.next_allowed_at == last_run_at + timedelta(weeks=4)


@pytest.mark.asyncio
async def test_evaluate_weekly_recap_availability_requires_full_run():
    availability = await full_run_policy.evaluate_weekly_recap_availability(
        _FakeDb([_FakeResult(None)]),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        now=datetime(2026, 2, 28, 12, 0, tzinfo=UTC),
    )

    assert availability.allowed is False
    assert availability.reason == "no_full_run"
    assert availability.next_allowed_at is None


@pytest.mark.asyncio
async def test_evaluate_weekly_recap_availability_requires_first_7_day_window():
    last_run_at = datetime(2026, 2, 26, 8, 0, tzinfo=UTC)
    now = datetime(2026, 2, 28, 12, 0, tzinfo=UTC)
    availability = await full_run_policy.evaluate_weekly_recap_availability(
        _FakeDb([_FakeResult(last_run_at), _FakeResult(None)]),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        now=now,
    )

    assert availability.allowed is False
    assert availability.reason == "window_not_open"
    assert availability.timezone == "UTC"
    assert availability.next_allowed_at == datetime(2026, 3, 5, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_evaluate_weekly_recap_availability_blocks_if_window_already_used():
    last_run_at = datetime(2026, 2, 10, 7, 0, tzinfo=UTC)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=UTC)
    existing_run_id = uuid.uuid4()
    availability = await full_run_policy.evaluate_weekly_recap_availability(
        _FakeDb([_FakeResult(last_run_at), _FakeResult(None), _FakeResult(existing_run_id)]),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        now=now,
    )

    assert availability.allowed is False
    assert availability.reason == "already_ran_in_window"
    assert availability.existing_run_id == existing_run_id
    assert availability.current_anchor_utc == datetime(2026, 2, 17, 0, 0, tzinfo=UTC)
    assert availability.window_start == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    assert availability.window_end == datetime(2026, 2, 17, 0, 0, tzinfo=UTC)
    assert availability.next_allowed_at == datetime(2026, 2, 24, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_evaluate_weekly_recap_availability_allows_one_run_per_window():
    last_run_at = datetime(2026, 2, 10, 7, 0, tzinfo=UTC)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=UTC)
    availability = await full_run_policy.evaluate_weekly_recap_availability(
        _FakeDb([_FakeResult(last_run_at), _FakeResult(None), _FakeResult(None)]),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        now=now,
    )

    assert availability.allowed is True
    assert availability.reason == "eligible"
    assert availability.current_anchor_utc == datetime(2026, 2, 17, 0, 0, tzinfo=UTC)
    assert availability.window_start == datetime(2026, 2, 10, 0, 0, tzinfo=UTC)
    assert availability.window_end == datetime(2026, 2, 17, 0, 0, tzinfo=UTC)
    assert availability.window_end == availability.window_start + timedelta(days=7)
