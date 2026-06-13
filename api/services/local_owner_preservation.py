from __future__ import annotations

import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True)
class UserScopedTable:
    key: str
    label: str
    table_name: str
    category: str
    user_column: str = "user_id"


@dataclass(frozen=True)
class RelatedCount:
    key: str
    label: str
    category: str
    sql: str


@dataclass(frozen=True)
class UniqueConflictSpec:
    table_name: str
    label: str
    key_columns: tuple[str, ...]
    user_column: str = "user_id"


@dataclass(frozen=True)
class UserDataSummary:
    user_id: uuid.UUID
    email: str
    local_owner_key: str
    row_counts: dict[str, int]


@dataclass(frozen=True)
class LocalOwnerResolution:
    kind: str
    user_id: uuid.UUID | None
    message: str


DIRECT_USER_SCOPED_TABLES: tuple[UserScopedTable, ...] = (
    UserScopedTable("active_analyses", "Active analysis", "active_analyses", "plans"),
    UserScopedTable("active_season_plans", "Active season plan", "active_season_plans", "plans"),
    UserScopedTable("active_weekly_plans", "Active weekly plan", "active_weekly_plans", "plans"),
    UserScopedTable("athlete_profiles", "Athlete profile", "athlete_profiles", "profile"),
    UserScopedTable("competitions", "Competitions", "competitions", "profile"),
    UserScopedTable("analysis_jobs", "Analysis jobs", "analysis_jobs", "jobs"),
    UserScopedTable("coach_threads", "Coach threads", "coach_threads", "coach"),
    UserScopedTable("coach_conversations", "Legacy coach conversation", "coach_conversations", "coach"),
    UserScopedTable("coach_proposals", "Coach proposals", "coach_proposals", "coach"),
    UserScopedTable("coach_turn_requests", "Coach turn idempotency requests", "coach_turn_requests", "coach"),
    UserScopedTable("coach_turn_runs", "Coach turn runs", "coach_turn_runs", "coach"),
    UserScopedTable("coach_interaction_quotas", "Coach interaction quotas", "coach_interaction_quotas", "coach"),
    UserScopedTable("daily_update_runs", "Daily update runs", "daily_update_runs", "connected_mode"),
    UserScopedTable("weekly_recap_runs", "Weekly recap runs", "weekly_recap_runs", "connected_mode"),
    UserScopedTable("integration_connections", "Integration connections", "integration_connections", "connectors"),
    UserScopedTable("strava_credentials", "Strava credentials", "strava_credentials", "connectors"),
    UserScopedTable("whoop_credentials", "WHOOP credentials", "whoop_credentials", "connectors"),
    UserScopedTable("oauth_sessions", "OAuth sessions", "oauth_sessions", "connectors"),
    UserScopedTable("ai_run_costs", "AI run costs", "ai_run_costs", "costs"),
    UserScopedTable("local_usage_plan_overrides", "Local usage plan override", "local_usage_plan_overrides", "local_usage"),
    UserScopedTable("local_usage_counters", "Local usage counters", "local_usage_counters", "local_usage"),
    UserScopedTable("local_usage_events", "Local usage events", "local_usage_events", "local_usage"),
)

RELATED_COUNTS: tuple[RelatedCount, ...] = (
    RelatedCount(
        key="coach_events",
        label="Coach events",
        category="coach",
        sql=(
            "SELECT count(*) FROM coach_events e "
            "JOIN coach_threads t ON t.id = e.thread_id "
            "WHERE t.user_id = :user_id"
        ),
    ),
    RelatedCount(
        key="coach_messages",
        label="Legacy coach messages",
        category="coach",
        sql=(
            "SELECT count(*) FROM coach_messages m "
            "JOIN coach_conversations c ON c.id = m.conversation_id "
            "WHERE c.user_id = :user_id"
        ),
    ),
)

TRAINING_OWNER_TABLE_KEYS = frozenset(
    {
        "active_analyses",
        "active_season_plans",
        "active_weekly_plans",
        "athlete_profiles",
        "competitions",
        "integration_connections",
        "strava_credentials",
        "whoop_credentials",
        "coach_threads",
    }
)

UNIQUE_CONFLICT_SPECS: tuple[UniqueConflictSpec, ...] = (
    UniqueConflictSpec("active_analyses", "Active analysis", ()),
    UniqueConflictSpec("active_season_plans", "Active season plan", ()),
    UniqueConflictSpec("active_weekly_plans", "Active weekly plan", ()),
    UniqueConflictSpec("athlete_profiles", "Athlete profile", ()),
    UniqueConflictSpec("coach_conversations", "Legacy coach conversation", ()),
    UniqueConflictSpec("strava_credentials", "Strava credentials", ()),
    UniqueConflictSpec("whoop_credentials", "WHOOP credentials", ()),
    UniqueConflictSpec("local_usage_plan_overrides", "Local usage plan override", ()),
    UniqueConflictSpec("integration_connections", "Integration connections", ("provider",)),
    UniqueConflictSpec("daily_update_runs", "Daily update runs", ("target_date",)),
    UniqueConflictSpec("weekly_recap_runs", "Weekly recap runs", ("week_anchor_utc",)),
    UniqueConflictSpec("coach_turn_requests", "Coach turn requests", ("idempotency_key",)),
    UniqueConflictSpec("coach_interaction_quotas", "Coach interaction quotas", ("week_anchor_utc",)),
    UniqueConflictSpec(
        "local_usage_counters",
        "Local usage counters",
        ("feature_key", "window_start", "window_end"),
    ),
)


def normalize_async_database_url(raw_url: str) -> str:
    database_url = raw_url.strip()
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + database_url.removeprefix("postgresql://")
    if database_url.startswith("postgres://"):
        return "postgresql+asyncpg://" + database_url.removeprefix("postgres://")
    return database_url


def redact_database_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    if not parsed.netloc or "@" not in parsed.netloc:
        return raw_url
    credentials, host = parsed.netloc.rsplit("@", 1)
    username = credentials.split(":", 1)[0]
    return urlunsplit((parsed.scheme, f"{username}:<redacted>@{host}", parsed.path, parsed.query, parsed.fragment))


def mask_identifier(value: str, *, prefix: int = 4, suffix: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= prefix + suffix:
        return "<redacted>"
    return f"{value[:prefix]}...{value[-suffix:]}"


def training_row_count(summary: UserDataSummary) -> int:
    return sum(summary.row_counts.get(key, 0) for key in TRAINING_OWNER_TABLE_KEYS)


def choose_local_owner(
    users: list[UserDataSummary],
    *,
    configured_local_owner_user_id: uuid.UUID | None,
) -> LocalOwnerResolution:
    if configured_local_owner_user_id is not None:
        matching_user = next((user for user in users if user.user_id == configured_local_owner_user_id), None)
        if matching_user is None:
            return LocalOwnerResolution(
                kind="configured_missing",
                user_id=configured_local_owner_user_id,
                message="LOCAL_OWNER_USER_ID is configured but does not match a row in users.",
            )
        return LocalOwnerResolution(
            kind="configured",
            user_id=configured_local_owner_user_id,
            message="LOCAL_OWNER_USER_ID points at an existing user. This is the safest preservation mode.",
        )

    owners_with_training_data = [user for user in users if training_row_count(user) > 0]
    if len(owners_with_training_data) == 1:
        owner = owners_with_training_data[0]
        return LocalOwnerResolution(
            kind="auto_single_training_owner",
            user_id=owner.user_id,
            message="Exactly one user owns training data; local mode should auto-adopt this owner.",
        )
    if len(owners_with_training_data) > 1:
        return LocalOwnerResolution(
            kind="needs_configuration",
            user_id=None,
            message="Multiple users own training data. Set LOCAL_OWNER_USER_ID before using local mode.",
        )
    return LocalOwnerResolution(
        kind="fresh_local_owner",
        user_id=None,
        message="No existing training owner found. Local mode will create a fresh local owner.",
    )
