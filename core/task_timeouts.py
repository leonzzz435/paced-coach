import os

DEFAULT_ANALYSIS_TASK_STALE_GRACE_SECONDS = 60
DEFAULT_DAILY_UPDATE_PENDING_MAX_AGE_SECONDS = 30 * 60


def _get_optional_positive_int_env(var_name: str) -> int | None:
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return None
    try:
        parsed_value = int(raw_value)
    except ValueError:
        return None
    if parsed_value <= 0:
        return None
    return parsed_value


def _get_positive_int_env(var_name: str, default: int) -> int:
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    try:
        parsed_value = int(raw_value)
    except ValueError:
        return default
    if parsed_value <= 0:
        return default
    return parsed_value


def get_analysis_task_time_limit_seconds() -> int | None:
    return _get_optional_positive_int_env("ANALYSIS_TASK_TIME_LIMIT_SECONDS")


def get_analysis_task_soft_time_limit_seconds() -> int | None:
    hard_limit_seconds = get_analysis_task_time_limit_seconds()
    if hard_limit_seconds is None:
        return None
    default_soft_limit_seconds = (
        hard_limit_seconds - 30
        if hard_limit_seconds > 30
        else 1
    )
    configured_soft_limit = _get_optional_positive_int_env("ANALYSIS_TASK_SOFT_TIME_LIMIT_SECONDS")
    if configured_soft_limit is None:
        configured_soft_limit = default_soft_limit_seconds
    if hard_limit_seconds == 1:
        return 1
    return min(configured_soft_limit, hard_limit_seconds - 1)


def get_analysis_task_stale_grace_seconds() -> int:
    return _get_positive_int_env("ANALYSIS_TASK_STALE_GRACE_SECONDS", DEFAULT_ANALYSIS_TASK_STALE_GRACE_SECONDS)


def get_analysis_running_job_max_age_seconds() -> int | None:
    task_time_limit_seconds = get_analysis_task_time_limit_seconds()
    if task_time_limit_seconds is None:
        return None
    return task_time_limit_seconds + get_analysis_task_stale_grace_seconds()


def get_daily_update_pending_max_age_seconds() -> int | None:
    raw_value = os.getenv("DAILY_UPDATE_PENDING_MAX_AGE_SECONDS")
    if raw_value is None:
        return DEFAULT_DAILY_UPDATE_PENDING_MAX_AGE_SECONDS
    try:
        parsed_value = int(raw_value)
    except ValueError:
        return DEFAULT_DAILY_UPDATE_PENDING_MAX_AGE_SECONDS
    if parsed_value <= 0:
        return None
    return parsed_value
