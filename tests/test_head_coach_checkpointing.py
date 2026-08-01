from importlib.metadata import version
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.base import MIGRATIONS

from services.ai.head_coach.checkpointing import (
    CHECKPOINT_SCHEMA_VERSION,
    CHECKPOINT_TABLES,
    CheckpointScope,
    CheckpointUnavailableError,
    HeadCoachCheckpointerProvider,
    build_checkpoint_config,
    build_checkpoint_identity,
    delete_owner_checkpoints,
    normalize_checkpoint_database_url,
)

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
RUN_ID = UUID("00000000-0000-0000-0000-000000000002")


def test_postgres_checkpointer_dependency_and_schema_version_are_pinned_together():
    assert version("langgraph-checkpoint-postgres") == "3.1.0"
    assert CHECKPOINT_SCHEMA_VERSION == len(MIGRATIONS) - 1 == 9
    assert CHECKPOINT_TABLES == {
        "checkpoint_migrations",
        "checkpoints",
        "checkpoint_blobs",
        "checkpoint_writes",
    }


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        (
            "postgresql+asyncpg://postgres:secret@localhost:5432/paced_coach",
            "postgresql://postgres:secret@localhost:5432/paced_coach",
        ),
        (
            "postgres://postgres:secret@localhost:5432/paced_coach",
            "postgresql://postgres:secret@localhost:5432/paced_coach",
        ),
        (
            "postgresql://postgres:secret@localhost:5432/paced_coach?sslmode=disable",
            "postgresql://postgres:secret@localhost:5432/paced_coach?sslmode=disable",
        ),
    ],
)
def test_checkpoint_database_url_uses_psycopg_scheme(database_url: str, expected: str):
    assert normalize_checkpoint_database_url(database_url) == expected


def test_checkpoint_identity_is_stable_owner_scoped_and_namespaced():
    identity = build_checkpoint_identity(
        owner_id=OWNER_ID,
        scope=CheckpointScope.INITIAL_PLANNING,
        resource_id=RUN_ID,
    )

    assert identity.thread_id == f"owner:{OWNER_ID}:analysis:{RUN_ID}"
    assert identity.checkpoint_ns == ""
    assert build_checkpoint_config(identity) == {
        "configurable": {
            "thread_id": identity.thread_id,
            "checkpoint_ns": identity.checkpoint_ns,
        }
    }

    coach_identity = build_checkpoint_identity(
        owner_id=OWNER_ID,
        scope=CheckpointScope.COACH_TURN,
        resource_id="thread-1",
        execution_id=RUN_ID,
    )
    assert coach_identity.thread_id == f"owner:{OWNER_ID}:coach:thread-1:scope:coach_turn:v1:run:{RUN_ID}"


@pytest.mark.asyncio
async def test_injected_test_checkpointer_never_opens_postgres():
    checkpointer = InMemorySaver()
    provider = HeadCoachCheckpointerProvider(
        database_url="postgresql://unused",
        injected_checkpointer=checkpointer,
    )

    assert await provider.get() is checkpointer
    await provider.close()


@pytest.mark.asyncio
async def test_production_checkpointer_unavailability_fails_without_memory_fallback():
    provider = HeadCoachCheckpointerProvider(
        database_url="postgresql://postgres:postgres@127.0.0.1:1/unavailable",
        pool_timeout_seconds=0.05,
    )

    with pytest.raises(CheckpointUnavailableError, match="no in-memory fallback"):
        await provider.get()

    await provider.close()


@pytest.mark.asyncio
async def test_owner_checkpoint_deletion_covers_every_payload_table():
    db = SimpleNamespace(
        execute=AsyncMock(return_value=cast("Any", type("Result", (), {"rowcount": 2})()))
    )

    deleted = await delete_owner_checkpoints(cast("Any", db), owner_id=OWNER_ID)

    statements = [str(call.args[0]) for call in db.execute.await_args_list]
    assert any("checkpoint_writes" in statement for statement in statements)
    assert any("checkpoint_blobs" in statement for statement in statements)
    assert any("checkpoints" in statement for statement in statements)
    assert all(call.args[1]["thread_prefix"] == f"owner:{OWNER_ID}:%" for call in db.execute.await_args_list)
    assert deleted == 6
