import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from worker.celery_app import celery_app


def test_beat_schedule_registered():
    schedule = celery_app.conf.beat_schedule
    assert "run-nightly-coach-memory-compaction" in schedule
    assert (
        schedule["run-nightly-coach-memory-compaction"]["task"]
        == "worker.tasks.run_nightly_coach_memory_compaction_task"
    )
    assert "run-coach-idempotency-cleanup" in schedule
    assert schedule["run-coach-idempotency-cleanup"]["task"] == "worker.tasks.run_coach_idempotency_cleanup_task"
