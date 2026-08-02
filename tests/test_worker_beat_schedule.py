import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from worker.celery_app import celery_app


def test_beat_schedule_contains_only_current_maintenance_tasks():
    schedule = celery_app.conf.beat_schedule

    assert set(schedule) == {
        "run-nightly-coach-memory-compaction",
        "run-coach-idempotency-cleanup",
        "run-head-coach-checkpoint-cleanup",
        "recover-pending-analysis-dispatches",
    }
    assert (
        schedule["run-nightly-coach-memory-compaction"]["task"]
        == "worker.tasks.run_nightly_coach_memory_compaction_task"
    )
    assert schedule["run-coach-idempotency-cleanup"]["task"] == "worker.tasks.run_coach_idempotency_cleanup_task"
    assert (
        schedule["run-head-coach-checkpoint-cleanup"]["task"]
        == "worker.tasks.run_head_coach_checkpoint_cleanup_task"
    )
    assert (
        schedule["recover-pending-analysis-dispatches"]["task"]
        == "worker.tasks.recover_pending_analysis_dispatches_task"
    )
