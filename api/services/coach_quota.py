from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from api.services.local_usage import consume_coach_turn, ensure_coach_turn_available, get_coach_turn_quota


async def get_coach_weekly_quota(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    week_anchor_utc: datetime | None = None,
) -> dict:
    quota = await get_coach_turn_quota(
        db,
        user_id=user_id,
        week_anchor_utc=week_anchor_utc,
    )
    return quota.model_dump(mode="json")


async def ensure_coach_weekly_quota_available(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    week_anchor_utc: datetime | None = None,
) -> dict:
    quota = await ensure_coach_turn_available(
        db,
        user_id=user_id,
        week_anchor_utc=week_anchor_utc,
    )
    return quota.model_dump(mode="json")


async def consume_coach_weekly_quota(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_id: str,
    week_anchor_utc: datetime | None = None,
) -> dict:
    quota = await consume_coach_turn(
        db,
        user_id=user_id,
        source_id=source_id,
        week_anchor_utc=week_anchor_utc,
    )
    return quota.model_dump(mode="json")
