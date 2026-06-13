import uuid

from api.services.local_owner_preservation import (
    DIRECT_USER_SCOPED_TABLES,
    TRAINING_OWNER_TABLE_KEYS,
    UNIQUE_CONFLICT_SPECS,
    UserDataSummary,
    choose_local_owner,
    mask_identifier,
    normalize_async_database_url,
    redact_database_url,
)


def _summary(user_id: uuid.UUID, *, training_rows: int = 0) -> UserDataSummary:
    return UserDataSummary(
        user_id=user_id,
        email=f"{user_id}@example.test",
        local_owner_key=f"owner_{user_id}",
        row_counts=dict.fromkeys(TRAINING_OWNER_TABLE_KEYS, training_rows),
    )


def test_choose_local_owner_prefers_configured_existing_user():
    configured_id = uuid.uuid4()
    other_id = uuid.uuid4()

    resolution = choose_local_owner(
        [_summary(configured_id), _summary(other_id, training_rows=1)],
        configured_local_owner_user_id=configured_id,
    )

    assert resolution.kind == "configured"
    assert resolution.user_id == configured_id


def test_choose_local_owner_reports_missing_configured_user():
    configured_id = uuid.uuid4()

    resolution = choose_local_owner(
        [_summary(uuid.uuid4(), training_rows=1)],
        configured_local_owner_user_id=configured_id,
    )

    assert resolution.kind == "configured_missing"
    assert resolution.user_id == configured_id


def test_choose_local_owner_auto_adopts_single_training_owner():
    owner_id = uuid.uuid4()

    resolution = choose_local_owner(
        [_summary(uuid.uuid4()), _summary(owner_id, training_rows=1)],
        configured_local_owner_user_id=None,
    )

    assert resolution.kind == "auto_single_training_owner"
    assert resolution.user_id == owner_id


def test_choose_local_owner_requires_configuration_for_multiple_training_owners():
    resolution = choose_local_owner(
        [_summary(uuid.uuid4(), training_rows=1), _summary(uuid.uuid4(), training_rows=1)],
        configured_local_owner_user_id=None,
    )

    assert resolution.kind == "needs_configuration"
    assert resolution.user_id is None


def test_preservation_table_specs_cover_expected_local_data_classes():
    table_keys = {table.key for table in DIRECT_USER_SCOPED_TABLES}

    assert {
        "active_season_plans",
        "active_weekly_plans",
        "athlete_profiles",
        "competitions",
        "coach_threads",
        "daily_update_runs",
        "weekly_recap_runs",
        "strava_credentials",
        "whoop_credentials",
        "ai_run_costs",
        "local_usage_events",
    }.issubset(table_keys)


def test_unique_conflict_specs_include_active_plan_and_connector_tables():
    conflict_keys = {(spec.table_name, spec.key_columns) for spec in UNIQUE_CONFLICT_SPECS}

    assert ("active_season_plans", ()) in conflict_keys
    assert ("active_weekly_plans", ()) in conflict_keys
    assert ("integration_connections", ("provider",)) in conflict_keys
    assert ("daily_update_runs", ("target_date",)) in conflict_keys


def test_url_and_identifier_redaction_helpers_do_not_leak_secret_values():
    assert normalize_async_database_url("postgresql://user:pass@localhost:5432/db").startswith("postgresql+asyncpg://")
    assert redact_database_url("postgresql+asyncpg://user:pass@localhost:5432/db") == (
        "postgresql+asyncpg://user:<redacted>@localhost:5432/db"
    )
    assert mask_identifier("local-owner@example.test") == "loca...test"
