import asyncio
import os
import uuid
from unittest.mock import patch

import pytest

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")

from worker import tasks as worker_tasks


def _reset_worker_loops():
    for loop in worker_tasks._worker_event_loops.values():
        if not loop.is_closed():
            loop.close()
    worker_tasks._worker_event_loops.clear()


def test_worker_async_runner_reuses_process_loop():
    _reset_worker_loops()
    try:
        loop_ids: list[int] = []

        async def capture_loop_id() -> int:
            loop_id = id(asyncio.get_running_loop())
            loop_ids.append(loop_id)
            return loop_id

        first = worker_tasks._run_async_in_worker_loop(capture_loop_id())
        second = worker_tasks._run_async_in_worker_loop(capture_loop_id())

        assert first == second
        assert loop_ids == [first, second]
        assert list(worker_tasks._worker_event_loops) == [os.getpid()]
    finally:
        _reset_worker_loops()


@pytest.mark.parametrize(
    ("task_name", "async_name"),
    [
        ("run_nightly_coach_memory_compaction_task", "_run_nightly_coach_memory_compaction_async"),
        ("run_coach_idempotency_cleanup_task", "_run_coach_idempotency_cleanup_async"),
        ("run_head_coach_checkpoint_cleanup_task", "_run_head_coach_checkpoint_cleanup_async"),
    ],
)
def test_scheduled_tasks_use_worker_loop_runner(task_name: str, async_name: str):
    task = getattr(worker_tasks, task_name)
    async_func = getattr(worker_tasks, async_name)

    def fake_runner(coro):
        assert asyncio.iscoroutine(coro)
        coro.close()
        return 1

    with patch.object(worker_tasks, "_run_async_in_worker_loop", side_effect=fake_runner) as mock_runner:
        task()

    mock_runner.assert_called_once()
    called_coro = mock_runner.call_args.args[0]
    assert called_coro.cr_code is async_func.__code__


def test_checkpoint_cleanup_is_scheduled_daily():
    schedule = worker_tasks.celery_app.conf.beat_schedule["run-head-coach-checkpoint-cleanup"]

    assert schedule["task"] == "worker.tasks.run_head_coach_checkpoint_cleanup_task"


def test_pending_analysis_dispatch_recovery_reenqueues_durable_intents():
    first_job_id = uuid.uuid4()
    second_job_id = uuid.uuid4()
    with (
        patch.object(worker_tasks, "get_sync_session") as get_sync_session,
        patch.object(worker_tasks.run_analysis_task, "delay") as delay,
    ):
        session = get_sync_session.return_value.__enter__.return_value
        session.execute.return_value.scalars.return_value = [first_job_id, second_job_id]
        recovered = worker_tasks.recover_pending_analysis_dispatches_task()

    assert recovered == 2
    assert [call.args[0] for call in delay.call_args_list] == [str(first_job_id), str(second_job_id)]
    session.commit.assert_called_once_with()
