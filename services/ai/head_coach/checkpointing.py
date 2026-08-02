from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CHECKPOINT_SCHEMA_VERSION = 9
CHECKPOINT_TABLES = {
    "checkpoint_migrations",
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
}
_CHECKPOINT_PAYLOAD_TABLES = ("checkpoint_writes", "checkpoint_blobs", "checkpoints")


class CheckpointUnavailableError(RuntimeError):
    """Raised when durable checkpoint storage cannot be opened or queried."""


class RunAlreadyClaimedError(RuntimeError):
    """Raised when another worker already owns the same run identity."""


class CheckpointScope(str, Enum):
    INITIAL_PLANNING = "initial_planning"
    MATERIAL_REPLANNING = "material_replanning"
    COACH_TURN = "coach_turn"
    WEEKLY_RECAP = "weekly_recap"
    DAILY_ADAPTATION = "daily_adaptation"


class CheckpointIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    owner_id: UUID
    scope: CheckpointScope
    resource_id: str = Field(min_length=1, max_length=200)
    thread_id: str = Field(min_length=1, max_length=500)
    checkpoint_ns: str = Field(default="", max_length=500)


def build_checkpoint_identity(
    *,
    owner_id: UUID,
    scope: CheckpointScope,
    resource_id: UUID | str,
    execution_id: UUID | str | None = None,
) -> CheckpointIdentity:
    resource_value = str(resource_id)
    is_analysis = scope in {
        CheckpointScope.INITIAL_PLANNING,
        CheckpointScope.MATERIAL_REPLANNING,
    }
    resource_kind = "analysis" if is_analysis else "coach"
    thread_id = f"owner:{owner_id}:{resource_kind}:{resource_value}"
    if not is_analysis:
        thread_id = f"{thread_id}:scope:{scope.value}:v1"
    if execution_id is not None:
        thread_id = f"{thread_id}:run:{execution_id}"
    return CheckpointIdentity(
        owner_id=owner_id,
        scope=scope,
        resource_id=resource_value,
        thread_id=thread_id,
        checkpoint_ns="",
    )


def build_checkpoint_config(identity: CheckpointIdentity) -> RunnableConfig:
    return {
        "configurable": {
            "thread_id": identity.thread_id,
            "checkpoint_ns": identity.checkpoint_ns,
        }
    }


def normalize_checkpoint_database_url(database_url: str) -> str:
    normalized = database_url.strip()
    if normalized.startswith("postgresql+asyncpg://"):
        return "postgresql://" + normalized.removeprefix("postgresql+asyncpg://")
    if normalized.startswith("postgres://"):
        return "postgresql://" + normalized.removeprefix("postgres://")
    if normalized.startswith("postgresql://"):
        return normalized
    raise ValueError("Head Coach checkpointing requires a PostgreSQL database URL")


class HeadCoachCheckpointerProvider:
    """One loop/process-safe PostgreSQL pool and saver, injectable for tests."""

    def __init__(
        self,
        *,
        database_url: str,
        injected_checkpointer: BaseCheckpointSaver[Any] | None = None,
        pool_min_size: int = 1,
        pool_max_size: int = 4,
        pool_timeout_seconds: float = 10.0,
    ) -> None:
        if pool_max_size < pool_min_size:
            raise ValueError("Head Coach checkpoint pool max size must be at least min size")
        self._database_url = normalize_checkpoint_database_url(database_url)
        self._injected_checkpointer = injected_checkpointer
        self._pool_min_size = pool_min_size
        self._pool_max_size = pool_max_size
        self._pool_timeout_seconds = pool_timeout_seconds
        self._pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] | None = None
        self._checkpointer: BaseCheckpointSaver[Any] | None = injected_checkpointer
        self._injected_claim_manager = InMemoryExecutionClaimManager() if injected_checkpointer is not None else None
        self._start_lock = asyncio.Lock()

    async def get(self) -> BaseCheckpointSaver[Any]:
        checkpointer = self._checkpointer
        if checkpointer is not None:
            return checkpointer
        async with self._start_lock:
            checkpointer = self._checkpointer
            if checkpointer is None:
                await self._start_postgres()
                checkpointer = self._checkpointer
        if checkpointer is None:
            raise CheckpointUnavailableError("Head Coach checkpointer failed to initialize")
        return checkpointer

    async def _start_postgres(self) -> None:
        pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] = AsyncConnectionPool(
            conninfo=self._database_url,
            min_size=self._pool_min_size,
            max_size=self._pool_max_size,
            open=False,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
        )
        try:
            await pool.open(wait=True, timeout=self._pool_timeout_seconds)
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.aget_tuple(
                {
                    "configurable": {
                        "thread_id": "__head_coach_schema_probe__",
                        "checkpoint_ns": "health/v1",
                    }
                }
            )
        except Exception as exc:
            await pool.close()
            raise CheckpointUnavailableError(
                "Durable Head Coach checkpoint storage is unavailable; no in-memory fallback was used"
            ) from exc
        self._pool = pool
        self._checkpointer = checkpointer

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
        self._pool = None
        self._checkpointer = self._injected_checkpointer

    @asynccontextmanager
    async def claim(self, run_identity: str) -> AsyncIterator[None]:
        await self.get()
        if self._injected_claim_manager is not None:
            async with self._injected_claim_manager.claim(run_identity):
                yield
            return
        if self._pool is None:
            raise CheckpointUnavailableError("Head Coach checkpoint claim storage is unavailable")
        async with PostgresExecutionClaimManager(self._pool).claim(run_identity):
            yield


_process_providers: dict[tuple[int, str, int, int, float], HeadCoachCheckpointerProvider] = {}


def get_process_checkpointer_provider(
    *,
    database_url: str,
    pool_min_size: int = 1,
    pool_max_size: int = 4,
    pool_timeout_seconds: float = 10.0,
) -> HeadCoachCheckpointerProvider:
    normalized_url = normalize_checkpoint_database_url(database_url)
    key = (os.getpid(), normalized_url, pool_min_size, pool_max_size, pool_timeout_seconds)
    provider = _process_providers.get(key)
    if provider is None:
        provider = HeadCoachCheckpointerProvider(
            database_url=normalized_url,
            pool_min_size=pool_min_size,
            pool_max_size=pool_max_size,
            pool_timeout_seconds=pool_timeout_seconds,
        )
        _process_providers[key] = provider
    return provider


def derive_advisory_lock_key(run_identity: str) -> int:
    digest = hashlib.blake2b(run_identity.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


class InMemoryExecutionClaimManager:
    def __init__(self) -> None:
        self._claimed: set[str] = set()
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def claim(self, run_identity: str) -> AsyncIterator[None]:
        async with self._lock:
            if run_identity in self._claimed:
                raise RunAlreadyClaimedError(f"Head Coach run is already claimed: {run_identity}")
            self._claimed.add(run_identity)
        try:
            yield
        finally:
            async with self._lock:
                self._claimed.discard(run_identity)


class PostgresExecutionClaimManager:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]]) -> None:
        self._pool = pool

    @asynccontextmanager
    async def claim(self, run_identity: str) -> AsyncIterator[None]:
        lock_key = derive_advisory_lock_key(run_identity)
        async with self._pool.connection() as connection:
            result = await connection.execute("SELECT pg_try_advisory_lock(%s)", (lock_key,))
            row = await result.fetchone()
            lock_acquired = bool(next(iter(row.values()))) if row else False
            if not lock_acquired:
                raise RunAlreadyClaimedError(f"Head Coach run is already claimed: {run_identity}")
            try:
                yield
            finally:
                await connection.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))


async def delete_owner_checkpoints(db: AsyncSession, *, owner_id: UUID) -> int:
    thread_prefix = f"owner:{owner_id}:%"
    deleted = 0
    for table_name in _CHECKPOINT_PAYLOAD_TABLES:
        result = await db.execute(
            text(f"DELETE FROM {table_name} WHERE thread_id LIKE :thread_prefix"),
            {"thread_prefix": thread_prefix},
        )
        deleted += int(getattr(result, "rowcount", 0) or 0)
    return deleted

async def delete_checkpoint_thread(db: AsyncSession, *, thread_id: str) -> int:
    deleted = 0
    for table_name in _CHECKPOINT_PAYLOAD_TABLES:
        result = await db.execute(
            text(f"DELETE FROM {table_name} WHERE thread_id = :thread_id"),
            {"thread_id": thread_id},
        )
        deleted += int(getattr(result, "rowcount", 0) or 0)
    return deleted
