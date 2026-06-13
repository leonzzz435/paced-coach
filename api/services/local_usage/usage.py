from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.local_usage import LocalUsageCounter, LocalUsageEvent
from api.services.local_usage.schemas import UsageWindow

FEATURE_PLAN_GENERATION = "plan_generation"
FEATURE_FULL_RUN = FEATURE_PLAN_GENERATION
FEATURE_ADAPTIVE_UPDATE = "adaptive_update"
FEATURE_DAILY_SYNC = "daily_sync"
FEATURE_COACH_TURN = "coach_turn"
FEATURE_INITIAL_DRAFT_PLAN = "initial_draft_plan"
INITIAL_DRAFT_PLAN_SOURCE_TYPE = "analysis_draft_block"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _window_usage_from_values(
    *,
    used: int,
    limit_value: int,
    window_start: datetime | None,
    window_end: datetime | None,
) -> UsageWindow:
    safe_used = max(used, 0)
    safe_limit = max(limit_value, 0)
    return UsageWindow(
        used=safe_used,
        limit=safe_limit,
        remaining=max(safe_limit - safe_used, 0),
        window_start=_as_utc(window_start) if window_start is not None else None,
        window_end=_as_utc(window_end) if window_end is not None else None,
    )


async def get_window_usage_snapshot(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    feature_key: str,
    window_start: datetime,
    window_end: datetime,
    limit_value: int,
) -> UsageWindow:
    row = await db.execute(
        select(LocalUsageCounter).where(
            LocalUsageCounter.user_id == user_id,
            LocalUsageCounter.feature_key == feature_key,
            LocalUsageCounter.window_start == window_start,
            LocalUsageCounter.window_end == window_end,
        )
    )
    counter = row.scalar_one_or_none()
    if counter is None:
        return _window_usage_from_values(
            used=0,
            limit_value=limit_value,
            window_start=window_start,
            window_end=window_end,
        )
    return _window_usage_from_values(
        used=counter.used,
        limit_value=counter.limit_value,
        window_start=counter.window_start,
        window_end=counter.window_end,
    )


async def ensure_window_usage_available(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    feature_key: str,
    window_start: datetime,
    window_end: datetime,
    limit_value: int,
    exhausted_detail: str,
) -> UsageWindow:
    snapshot = await get_window_usage_snapshot(
        db,
        user_id=user_id,
        feature_key=feature_key,
        window_start=window_start,
        window_end=window_end,
        limit_value=limit_value,
    )
    if snapshot.remaining <= 0:
        raise HTTPException(status_code=402, detail=exhausted_detail)
    return snapshot


async def record_usage_event(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    feature_key: str,
    source_type: str,
    source_id: str,
    consumed_at: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    quantity: int = 1,
    metadata: dict[str, Any] | None = None,
) -> bool:
    if quantity < 1:
        raise ValueError("quantity must be >= 1")

    result = await db.execute(
        text(
            """
            INSERT INTO local_usage_events (
                id,
                user_id,
                feature_key,
                source_type,
                source_id,
                quantity,
                window_start,
                window_end,
                metadata,
                consumed_at
            )
            VALUES (
                :id,
                :user_id,
                :feature_key,
                :source_type,
                :source_id,
                :quantity,
                :window_start,
                :window_end,
                :metadata,
                :consumed_at
            )
            ON CONFLICT (feature_key, source_type, source_id) DO NOTHING
            RETURNING id
            """
        ),
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "feature_key": feature_key,
            "source_type": source_type,
            "source_id": source_id,
            "quantity": quantity,
            "window_start": window_start,
            "window_end": window_end,
            "metadata": metadata,
            "consumed_at": consumed_at or datetime.now(UTC),
        },
    )
    return result.scalar_one_or_none() is not None


async def consume_window_usage(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    feature_key: str,
    source_type: str,
    source_id: str,
    window_start: datetime,
    window_end: datetime,
    limit_value: int,
    exhausted_detail: str,
    quantity: int = 1,
    metadata: dict[str, Any] | None = None,
) -> UsageWindow:
    if quantity < 1:
        raise ValueError("quantity must be >= 1")

    inserted_event = await record_usage_event(
        db,
        user_id=user_id,
        feature_key=feature_key,
        source_type=source_type,
        source_id=source_id,
        window_start=window_start,
        window_end=window_end,
        quantity=quantity,
        metadata=metadata,
    )
    if not inserted_event:
        return await get_window_usage_snapshot(
            db,
            user_id=user_id,
            feature_key=feature_key,
            window_start=window_start,
            window_end=window_end,
            limit_value=limit_value,
        )

    updated_counter = await db.execute(
        text(
            """
            INSERT INTO local_usage_counters (
                id,
                user_id,
                feature_key,
                window_start,
                window_end,
                used,
                limit_value
            )
            VALUES (
                :id,
                :user_id,
                :feature_key,
                :window_start,
                :window_end,
                :quantity,
                :limit_value
            )
            ON CONFLICT (user_id, feature_key, window_start, window_end)
            DO UPDATE SET
                used = local_usage_counters.used + EXCLUDED.used,
                limit_value = EXCLUDED.limit_value,
                updated_at = now()
            WHERE local_usage_counters.used + EXCLUDED.used <= EXCLUDED.limit_value
            RETURNING used, limit_value, window_start, window_end
            """
        ),
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "feature_key": feature_key,
            "window_start": window_start,
            "window_end": window_end,
            "quantity": quantity,
            "limit_value": limit_value,
        },
    )
    row = updated_counter.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=402, detail=exhausted_detail)

    return _window_usage_from_values(
        used=int(row["used"]),
        limit_value=int(row["limit_value"]),
        window_start=row["window_start"],
        window_end=row["window_end"],
    )


def initial_draft_plan_source_id(*, user_id: uuid.UUID) -> str:
    return f"draft_block:first:{user_id}"


async def get_initial_draft_plan_event(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> LocalUsageEvent | None:
    row = await db.execute(
        select(LocalUsageEvent).where(
            LocalUsageEvent.user_id == user_id,
            LocalUsageEvent.feature_key == FEATURE_INITIAL_DRAFT_PLAN,
            LocalUsageEvent.source_type == INITIAL_DRAFT_PLAN_SOURCE_TYPE,
            LocalUsageEvent.source_id == initial_draft_plan_source_id(user_id=user_id),
        )
    )
    return row.scalar_one_or_none()


async def claim_initial_draft_plan(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    metadata: dict[str, Any] | None = None,
) -> bool:
    payload_metadata = {"state": "pending", **(metadata or {})}
    return await record_usage_event(
        db,
        user_id=user_id,
        feature_key=FEATURE_INITIAL_DRAFT_PLAN,
        source_type=INITIAL_DRAFT_PLAN_SOURCE_TYPE,
        source_id=initial_draft_plan_source_id(user_id=user_id),
        metadata=payload_metadata,
    )
