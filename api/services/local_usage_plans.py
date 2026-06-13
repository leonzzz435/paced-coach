from __future__ import annotations

from dataclasses import dataclass

LOCAL_DEFAULT_USAGE_PLAN_KEY = "local_default"
LOCAL_EXTENDED_USAGE_PLAN_KEY = "local_extended"
LEGACY_FREE_PLAN_KEY = "free"


@dataclass(frozen=True)
class LocalUsagePlan:
    plan_key: str
    plan_name: str
    plan_generation_cooldown_days: int
    daily_sync_limit: int
    coach_turn_daily_limit: int
    weekly_recap_included: bool
    proactive_daily_sync_enabled: bool
    adaptive_updates_per_cycle_limit: int
    weekly_recap_limit: int = 1


LOCAL_DEFAULT_USAGE_PLAN = LocalUsagePlan(
    plan_key=LOCAL_DEFAULT_USAGE_PLAN_KEY,
    plan_name="Local default",
    plan_generation_cooldown_days=28,
    daily_sync_limit=1,
    coach_turn_daily_limit=3,
    weekly_recap_included=True,
    weekly_recap_limit=1,
    proactive_daily_sync_enabled=False,
    adaptive_updates_per_cycle_limit=2,
)

LOCAL_EXTENDED_USAGE_PLAN = LocalUsagePlan(
    plan_key=LOCAL_EXTENDED_USAGE_PLAN_KEY,
    plan_name="Local extended",
    plan_generation_cooldown_days=7,
    daily_sync_limit=1,
    coach_turn_daily_limit=20,
    weekly_recap_included=True,
    weekly_recap_limit=1,
    proactive_daily_sync_enabled=False,
    adaptive_updates_per_cycle_limit=8,
)

_PLAN_BY_KEY = {
    LOCAL_DEFAULT_USAGE_PLAN.plan_key: LOCAL_DEFAULT_USAGE_PLAN,
    LOCAL_EXTENDED_USAGE_PLAN.plan_key: LOCAL_EXTENDED_USAGE_PLAN,
    LEGACY_FREE_PLAN_KEY: LOCAL_DEFAULT_USAGE_PLAN,
}


def get_local_usage_plan_definition(plan_key: str | None) -> LocalUsagePlan | None:
    if not isinstance(plan_key, str) or not plan_key.strip():
        return None
    return _PLAN_BY_KEY.get(plan_key.strip().lower())
