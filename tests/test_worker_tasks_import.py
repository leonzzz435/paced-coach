import os

import pytest


def test_import_worker_tasks_without_database_url_does_not_raise() -> None:
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.pop("DATABASE_URL", None)
    import worker.tasks as worker_tasks

    assert worker_tasks is not None


def test_get_sync_session_requires_database_url() -> None:
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.pop("DATABASE_URL", None)
    from worker.tasks import get_sync_session

    with pytest.raises(RuntimeError, match=r"DATABASE_URL is not set"):
        get_sync_session()
