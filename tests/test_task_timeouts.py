from core.task_timeouts import (
    get_analysis_running_job_max_age_seconds,
    get_analysis_task_soft_time_limit_seconds,
    get_analysis_task_stale_grace_seconds,
    get_analysis_task_time_limit_seconds,
)


def test_task_timeout_defaults(monkeypatch):
    monkeypatch.delenv("ANALYSIS_TASK_TIME_LIMIT_SECONDS", raising=False)
    monkeypatch.delenv("ANALYSIS_TASK_SOFT_TIME_LIMIT_SECONDS", raising=False)
    monkeypatch.delenv("ANALYSIS_TASK_STALE_GRACE_SECONDS", raising=False)

    assert get_analysis_task_time_limit_seconds() is None
    assert get_analysis_task_soft_time_limit_seconds() is None
    assert get_analysis_task_stale_grace_seconds() == 60
    assert get_analysis_running_job_max_age_seconds() is None


def test_soft_timeout_is_clamped_below_hard_timeout(monkeypatch):
    monkeypatch.setenv("ANALYSIS_TASK_TIME_LIMIT_SECONDS", "10")
    monkeypatch.setenv("ANALYSIS_TASK_SOFT_TIME_LIMIT_SECONDS", "100")

    assert get_analysis_task_time_limit_seconds() == 10
    assert get_analysis_task_soft_time_limit_seconds() == 9
    assert get_analysis_running_job_max_age_seconds() == 70


def test_invalid_timeout_values_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("ANALYSIS_TASK_TIME_LIMIT_SECONDS", "invalid")
    monkeypatch.setenv("ANALYSIS_TASK_SOFT_TIME_LIMIT_SECONDS", "-1")
    monkeypatch.setenv("ANALYSIS_TASK_STALE_GRACE_SECONDS", "0")

    assert get_analysis_task_time_limit_seconds() is None
    assert get_analysis_task_soft_time_limit_seconds() is None
    assert get_analysis_task_stale_grace_seconds() == 60
    assert get_analysis_running_job_max_age_seconds() is None
