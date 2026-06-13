from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.local_usage import LocalUsagePlanOverride
from api.services.local_usage import (
    AdaptiveUpdateWindow,
    LocalUsageContext,
    consume_adaptive_update,
    get_adaptive_update_usage,
    limits,
)
from api.services.local_usage.limits import _get_adaptive_update_window
from api.services.local_usage.schemas import UsageWindow
from api.services.local_usage_plans import LOCAL_DEFAULT_USAGE_PLAN, LOCAL_EXTENDED_USAGE_PLAN


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _AdaptiveWindowDb:
    def __init__(self, *, active_weekly, generation_event):
        self.active_weekly = active_weekly
        self.generation_event = generation_event

    async def execute(self, statement, *_args, **_kwargs):
        sql = str(statement)
        if "FROM active_weekly_plans" in sql:
            return _FakeScalarResult(self.active_weekly)
        if "FROM local_usage_events" in sql:
            return _FakeScalarResult(self.generation_event)
        raise AssertionError(f"Unexpected statement: {sql}")


def _context_for_free() -> LocalUsageContext:
    return LocalUsageContext(
        plan_override=None,
        selected_plan=None,
        effective_plan=LOCAL_DEFAULT_USAGE_PLAN,
        tier="free",
        has_access=False,
    )


def _context_for_extended_local_plan() -> LocalUsageContext:
    return LocalUsageContext(
        plan_override=cast(
            "LocalUsagePlanOverride",
            SimpleNamespace(plan_key=LOCAL_EXTENDED_USAGE_PLAN.plan_key, status="active"),
        ),
        selected_plan=LOCAL_EXTENDED_USAGE_PLAN,
        effective_plan=LOCAL_EXTENDED_USAGE_PLAN,
        tier="extended",
        has_access=True,
    )


@pytest.mark.asyncio
async def test_adaptive_update_window_prefers_generation_consumed_at():
    user_id = uuid.uuid4()
    source_job_id = uuid.uuid4()
    generation_consumed_at = datetime(2026, 4, 1, 8, 0, tzinfo=UTC)
    db = _AdaptiveWindowDb(
        active_weekly=SimpleNamespace(
            source_job_id=source_job_id,
            updated_at=datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
        ),
        generation_event=SimpleNamespace(consumed_at=generation_consumed_at),
    )

    window = await _get_adaptive_update_window(cast("AsyncSession", db), user_id=user_id)

    assert window == AdaptiveUpdateWindow(
        cycle_source_id=str(source_job_id),
        window_start=generation_consumed_at,
        window_end=generation_consumed_at + timedelta(days=28),
    )


@pytest.mark.asyncio
async def test_adaptive_update_window_falls_back_to_active_weekly_timestamp():
    user_id = uuid.uuid4()
    source_job_id = uuid.uuid4()
    updated_at = datetime(2026, 4, 3, 12, 0, tzinfo=UTC)
    db = _AdaptiveWindowDb(
        active_weekly=SimpleNamespace(
            source_job_id=source_job_id,
            updated_at=updated_at,
        ),
        generation_event=None,
    )

    window = await _get_adaptive_update_window(cast("AsyncSession", db), user_id=user_id)

    assert window == AdaptiveUpdateWindow(
        cycle_source_id=str(source_job_id),
        window_start=updated_at,
        window_end=updated_at + timedelta(days=28),
    )


@pytest.mark.asyncio
async def test_get_adaptive_update_usage_returns_full_remaining_without_active_block(monkeypatch):
    monkeypatch.setattr(
        limits,
        "get_settings",
        lambda: SimpleNamespace(local_usage_dev_bypass=False),
    )
    monkeypatch.setattr(limits, "_get_adaptive_update_window", AsyncMock(return_value=None))

    usage = await get_adaptive_update_usage(
        object(),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        context=_context_for_free(),
    )

    assert usage.used == 0
    assert usage.limit == LOCAL_DEFAULT_USAGE_PLAN.adaptive_updates_per_cycle_limit
    assert usage.remaining == LOCAL_DEFAULT_USAGE_PLAN.adaptive_updates_per_cycle_limit
    assert usage.window_start is None
    assert usage.window_end is None


@pytest.mark.asyncio
async def test_get_adaptive_update_usage_uses_plan_limit_for_window_snapshot(monkeypatch):
    window = AdaptiveUpdateWindow(
        cycle_source_id="analysis-job-1",
        window_start=datetime(2026, 4, 1, 8, 0, tzinfo=UTC),
        window_end=datetime(2026, 4, 29, 8, 0, tzinfo=UTC),
    )
    snapshot = UsageWindow(
        used=3,
        limit=LOCAL_EXTENDED_USAGE_PLAN.adaptive_updates_per_cycle_limit,
        remaining=5,
        window_start=window.window_start,
        window_end=window.window_end,
    )
    get_snapshot = AsyncMock(return_value=snapshot)

    monkeypatch.setattr(
        limits,
        "get_settings",
        lambda: SimpleNamespace(local_usage_dev_bypass=False),
    )
    monkeypatch.setattr(limits, "_get_adaptive_update_window", AsyncMock(return_value=window))
    monkeypatch.setattr(limits, "get_window_usage_snapshot", get_snapshot)

    usage = await get_adaptive_update_usage(
        object(),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        context=_context_for_extended_local_plan(),
    )

    assert usage == snapshot
    assert get_snapshot.await_args is not None
    assert get_snapshot.await_args.kwargs["limit_value"] == LOCAL_EXTENDED_USAGE_PLAN.adaptive_updates_per_cycle_limit


@pytest.mark.asyncio
async def test_consume_adaptive_update_requires_active_training_block(monkeypatch):
    monkeypatch.setattr(
        limits,
        "get_settings",
        lambda: SimpleNamespace(local_usage_dev_bypass=False),
    )
    monkeypatch.setattr(limits, "_get_adaptive_update_window", AsyncMock(return_value=None))

    with pytest.raises(HTTPException) as exc:
        await consume_adaptive_update(
            object(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
            source_id="proposal-1",
            context=_context_for_free(),
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Adaptive updates require an active training block."


@pytest.mark.asyncio
async def test_consume_adaptive_update_default_local_plan_raises_cycle_reset_message(monkeypatch):
    window = AdaptiveUpdateWindow(
        cycle_source_id="analysis-job-1",
        window_start=datetime(2026, 4, 1, 8, 0, tzinfo=UTC),
        window_end=datetime(2026, 4, 29, 8, 0, tzinfo=UTC),
    )
    exhausted = UsageWindow(
        used=LOCAL_DEFAULT_USAGE_PLAN.adaptive_updates_per_cycle_limit,
        limit=LOCAL_DEFAULT_USAGE_PLAN.adaptive_updates_per_cycle_limit,
        remaining=0,
        window_start=window.window_start,
        window_end=window.window_end,
    )

    monkeypatch.setattr(
        limits,
        "get_settings",
        lambda: SimpleNamespace(local_usage_dev_bypass=False),
    )
    monkeypatch.setattr(limits, "_get_adaptive_update_window", AsyncMock(return_value=window))
    monkeypatch.setattr(limits, "get_window_usage_snapshot", AsyncMock(return_value=exhausted))

    with pytest.raises(HTTPException) as exc:
        await consume_adaptive_update(
            object(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
            source_id="proposal-1",
            context=_context_for_free(),
        )

    assert exc.value.status_code == 429
    assert exc.value.detail == "Adaptive update limit reached for this training block. Generate a new training block to reset this limit."


@pytest.mark.asyncio
async def test_consume_adaptive_update_extended_local_plan_raises_cycle_reset_message(monkeypatch):
    window = AdaptiveUpdateWindow(
        cycle_source_id="analysis-job-1",
        window_start=datetime(2026, 4, 1, 8, 0, tzinfo=UTC),
        window_end=datetime(2026, 4, 29, 8, 0, tzinfo=UTC),
    )
    exhausted = UsageWindow(
        used=LOCAL_EXTENDED_USAGE_PLAN.adaptive_updates_per_cycle_limit,
        limit=LOCAL_EXTENDED_USAGE_PLAN.adaptive_updates_per_cycle_limit,
        remaining=0,
        window_start=window.window_start,
        window_end=window.window_end,
    )

    monkeypatch.setattr(
        limits,
        "get_settings",
        lambda: SimpleNamespace(local_usage_dev_bypass=False),
    )
    monkeypatch.setattr(limits, "_get_adaptive_update_window", AsyncMock(return_value=window))
    monkeypatch.setattr(limits, "get_window_usage_snapshot", AsyncMock(return_value=exhausted))

    with pytest.raises(HTTPException) as exc:
        await consume_adaptive_update(
            object(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
            source_id="proposal-1",
            context=_context_for_extended_local_plan(),
        )

    assert exc.value.status_code == 429
    assert exc.value.detail == "Adaptive update limit reached for this training block. Generate a new training block to reset this limit."
