from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PlanGenerationStatus(BaseModel):
    allowed: bool
    last_generated_at: datetime | None = None
    next_allowed_at: datetime | None = None
    cooldown_days: int


class UsageWindow(BaseModel):
    used: int
    limit: int
    remaining: int
    window_start: datetime | None = None
    window_end: datetime | None = None


class CoachMessageStatus(BaseModel):
    used: int
    limit: int | None = None
    remaining: int | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None


class LocalUsageFeatures(BaseModel):
    weekly_recap_included: bool
    proactive_daily_sync_enabled: bool
    extended_access: bool = False


class LocalUsageStatusSnapshot(BaseModel):
    tier: Literal["free", "extended", "dev_bypass"] = "free"
    status: str
    plan_key: str | None = None
    plan_name: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    plan_generation: PlanGenerationStatus
    adaptive_updates: UsageWindow
    daily_sync: UsageWindow
    coach_messages: CoachMessageStatus
    features: LocalUsageFeatures
