from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_REVISION = "001_initial_local_first"
HEAD_REVISION = "002_head_coach_checkpoints"


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _database_url(admin_url: str, database_name: str) -> str:
    parsed = urlsplit(_psycopg_url(admin_url))
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{database_name}", parsed.query, ""))


def _upgrade(database_url: str, revision: str):
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", revision],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.integration
def test_disposable_001_to_002_upgrade_preserves_existing_owner_and_active_plans():
    """Exercise the additive upgrade only against an explicitly authorized disposable database."""
    admin_url = os.getenv("HEAD_COACH_MIGRATION_TEST_ADMIN_URL")
    if not admin_url:
        pytest.skip("HEAD_COACH_MIGRATION_TEST_ADMIN_URL is not configured")

    database_name = f"paced_coach_migration_test_{uuid4().hex}"
    database_url = _database_url(admin_url, database_name)
    owner_id = uuid4()
    job_id = uuid4()
    season_plan_id = uuid4()
    weekly_plan_id = uuid4()
    season_payload = {"schema_version": 1, "title": "Synthetic historical season"}
    weekly_payload = {"schema_version": 1, "title": "Synthetic historical week"}

    with psycopg.connect(_psycopg_url(admin_url), autocommit=True) as admin_connection:
        admin_connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))

    try:
        _upgrade(database_url, BASELINE_REVISION)
        with psycopg.connect(database_url) as connection:
            connection.execute(
                """
                INSERT INTO users (id, local_owner_key, email, credits)
                VALUES (%s, %s, %s, %s)
                """,
                (owner_id, f"migration-test-{owner_id}", f"{owner_id}@example.test", 0),
            )
            connection.execute(
                """
                INSERT INTO analysis_jobs (id, user_id, status, config)
                VALUES (%s, %s, %s, %s)
                """,
                (job_id, owner_id, "completed", Jsonb({"synthetic": True})),
            )
            connection.execute(
                """
                INSERT INTO active_season_plans (id, user_id, version, plan_data, source_job_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (season_plan_id, owner_id, 1, Jsonb(season_payload), job_id),
            )
            connection.execute(
                """
                INSERT INTO active_weekly_plans (id, user_id, version, plan_data, source_job_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (weekly_plan_id, owner_id, 1, Jsonb(weekly_payload), job_id),
            )
            connection.commit()

        _upgrade(database_url, "head")

        with psycopg.connect(database_url) as connection:
            owner_row = connection.execute(
                "SELECT id, local_owner_key FROM users WHERE id = %s",
                (owner_id,),
            ).fetchone()
            season_row = connection.execute(
                "SELECT id, user_id, version, plan_data, source_job_id FROM active_season_plans WHERE id = %s",
                (season_plan_id,),
            ).fetchone()
            weekly_row = connection.execute(
                "SELECT id, user_id, version, plan_data, source_job_id FROM active_weekly_plans WHERE id = %s",
                (weekly_plan_id,),
            ).fetchone()
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
            checkpoint_tables = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name LIKE 'checkpoint%'
                    """
                ).fetchall()
            }

        assert owner_row == (owner_id, f"migration-test-{owner_id}")
        assert season_row == (season_plan_id, owner_id, 1, season_payload, job_id)
        assert weekly_row == (weekly_plan_id, owner_id, 1, weekly_payload, job_id)
        assert revision == (HEAD_REVISION,)
        assert checkpoint_tables == {
            "checkpoint_migrations",
            "checkpoints",
            "checkpoint_blobs",
            "checkpoint_writes",
        }
    finally:
        with psycopg.connect(_psycopg_url(admin_url), autocommit=True) as admin_connection:
            admin_connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (database_name,),
            )
            admin_connection.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name)))
