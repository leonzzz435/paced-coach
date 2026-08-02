from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def owner_plan_generation_lock_key(user_id: uuid.UUID) -> int:
    digest = hashlib.blake2b(f"owner:{user_id}:plan-generation".encode(), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


async def lock_owner_plan_generation(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Serialize availability checks and job creation for one local owner."""
    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": owner_plan_generation_lock_key(user_id)},
    )
