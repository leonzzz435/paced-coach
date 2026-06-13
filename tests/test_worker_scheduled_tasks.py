import asyncio
import os
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


def test_daily_proactive_task_is_disabled(caplog):
    caplog.set_level("INFO")
    worker_tasks.run_daily_coach_proactive_eval_task()

    assert "Daily coach proactive eval is disabled" in caplog.text
