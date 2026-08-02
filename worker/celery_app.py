import os

from celery import Celery  # type: ignore[import-untyped]
from celery.schedules import crontab  # type: ignore[import-untyped]

from core.task_timeouts import (
    get_analysis_task_soft_time_limit_seconds,
    get_analysis_task_time_limit_seconds,
)

redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise RuntimeError("REDIS_URL must be set for the local Redis service.")

celery_app = Celery(
    "paced_coach_worker",
    broker=redis_url,
    backend=redis_url,
    include=["worker.tasks"],
)

celery_config: dict[str, object] = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "task_track_started": True,
    "worker_prefetch_multiplier": 1,
    "beat_schedule": {
        "run-nightly-coach-memory-compaction": {
            "task": "worker.tasks.run_nightly_coach_memory_compaction_task",
            "schedule": crontab(minute=15, hour=2),
        },
        "run-coach-idempotency-cleanup": {
            "task": "worker.tasks.run_coach_idempotency_cleanup_task",
            "schedule": crontab(minute=45, hour=3),
        },
        "run-head-coach-checkpoint-cleanup": {
            "task": "worker.tasks.run_head_coach_checkpoint_cleanup_task",
            "schedule": crontab(minute=15, hour=4),
        },
        "recover-pending-analysis-dispatches": {
            "task": "worker.tasks.recover_pending_analysis_dispatches_task",
            "schedule": crontab(minute="*"),
        },
    },
}

task_time_limit_seconds = get_analysis_task_time_limit_seconds()
if task_time_limit_seconds is not None:
    celery_config["task_time_limit"] = task_time_limit_seconds

task_soft_time_limit_seconds = get_analysis_task_soft_time_limit_seconds()
if task_soft_time_limit_seconds is not None:
    celery_config["task_soft_time_limit"] = task_soft_time_limit_seconds

celery_app.conf.update(**celery_config)
