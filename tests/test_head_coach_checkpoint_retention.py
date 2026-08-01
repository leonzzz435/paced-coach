import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from services.ai.head_coach.checkpointing import (
    InMemoryExecutionClaimManager,
    RunAlreadyClaimedError,
    delete_checkpoint_thread,
    derive_advisory_lock_key,
)
from services.ai.head_coach.middleware import LifecyclePhase, build_lifecycle_event

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_advisory_lock_key_is_stable_signed_bigint():
    first = derive_advisory_lock_key("owner:one:analysis:run")
    second = derive_advisory_lock_key("owner:one:analysis:run")

    assert first == second
    assert -(2**63) <= first < 2**63


@pytest.mark.asyncio
async def test_overlapping_execution_claims_fail_closed_and_release_after_owner_exits():
    manager = InMemoryExecutionClaimManager()
    first_claim_entered = asyncio.Event()
    release_first_claim = asyncio.Event()

    async def hold_first_claim() -> None:
        async with manager.claim("run-1"):
            first_claim_entered.set()
            await release_first_claim.wait()

    first_task = asyncio.create_task(hold_first_claim())
    await first_claim_entered.wait()

    with pytest.raises(RunAlreadyClaimedError):
        async with manager.claim("run-1"):
            pass

    release_first_claim.set()
    await first_task

    async with manager.claim("run-1"):
        pass


def test_lifecycle_event_excludes_raw_context_and_reasoning():
    event = build_lifecycle_event(
        phase=LifecyclePhase.REVIEWING_CONSTRAINTS,
        run_id="run-1",
        profile_name="initial_planning",
        occurred_at=datetime.now(UTC) - timedelta(seconds=1),
        artifact_ids=["artifact-1"],
    )
    payload = event.model_dump(mode="json")

    assert payload["phase"] == "reviewing_constraints"
    assert "messages" not in payload
    assert "context" not in payload
    assert "reasoning" not in payload
    assert "credentials" not in payload


@pytest.mark.asyncio
async def test_checkpoint_cleanup_targets_one_execution_thread():
    db = AsyncMock()
    db.execute.return_value.rowcount = 2

    thread_deleted = await delete_checkpoint_thread(db, thread_id="owner:one:analysis:job")
    assert thread_deleted == 6
    assert db.execute.await_count == 3
