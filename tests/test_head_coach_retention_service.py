from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_retention_deletes_terminal_analysis_and_coach_execution_threads(monkeypatch):
    from api.services import head_coach_checkpoint_retention as retention

    owner_id = uuid4()
    analysis_id = uuid4()
    coach_thread_id = uuid4()
    coach_run_id = uuid4()
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(all=lambda: [(owner_id, analysis_id)]),
        SimpleNamespace(all=lambda: [(owner_id, coach_thread_id, coach_run_id)]),
    ]
    delete_thread = AsyncMock(side_effect=[4, 3])
    monkeypatch.setattr(retention, "delete_checkpoint_thread", delete_thread)

    summary = await retention.cleanup_expired_head_coach_checkpoints(
        db,
        cutoff=datetime(2026, 7, 12, tzinfo=UTC),
    )

    assert summary.analysis_threads_deleted == 1
    assert summary.coach_executions_deleted == 1
    assert summary.checkpoint_rows_deleted == 7
    assert delete_thread.await_args_list[0].kwargs == {"thread_id": f"owner:{owner_id}:analysis:{analysis_id}"}
    assert delete_thread.await_args_list[1].kwargs == {
        "thread_id": f"owner:{owner_id}:coach:{coach_thread_id}:scope:coach_turn:v1:run:{coach_run_id}"
    }
