#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.config import get_settings
from api.services.local_owner_preservation import (
    DIRECT_USER_SCOPED_TABLES,
    RELATED_COUNTS,
    UserDataSummary,
    choose_local_owner,
    mask_identifier,
    normalize_async_database_url,
    redact_database_url,
)


def _resolve_database_url(cli_database_url: str) -> str:
    raw_url = (
        cli_database_url
        or os.getenv("DATABASE_URL_ASYNC", "")
        or os.getenv("DATABASE_URL", "")
        or get_settings().database_url_async
    )
    return normalize_async_database_url(raw_url)


def _parse_uuid(raw_value: str) -> uuid.UUID | None:
    value = raw_value.strip()
    if not value:
        return None
    return uuid.UUID(value)


async def _table_exists(conn: AsyncConnection, table_name: str) -> bool:
    result = await conn.execute(text("SELECT to_regclass(:table_name) IS NOT NULL"), {"table_name": table_name})
    return bool(result.scalar_one())


async def _count_for_user(conn: AsyncConnection, table_name: str, user_column: str, user_id: uuid.UUID) -> int:
    if not await _table_exists(conn, table_name):
        return 0
    result = await conn.execute(
        text(f"SELECT count(*) FROM {table_name} WHERE {user_column} = :user_id"),
        {"user_id": user_id},
    )
    return int(result.scalar_one())


async def _related_count_for_user(conn: AsyncConnection, sql: str, user_id: uuid.UUID) -> int:
    result = await conn.execute(text(sql), {"user_id": user_id})
    return int(result.scalar_one())


async def _global_count(conn: AsyncConnection, table_name: str) -> int:
    if not await _table_exists(conn, table_name):
        return 0
    result = await conn.execute(text(f"SELECT count(*) FROM {table_name}"))
    return int(result.scalar_one())


async def _user_owner_key_column(conn: AsyncConnection) -> str:
    result = await conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'local_owner_key'"
        )
    )
    column_names = {str(row.column_name) for row in result.fetchall()}
    if "local_owner_key" in column_names:
        return "local_owner_key"
    raise RuntimeError("users table has no local owner key column")


async def _fetch_users(conn: AsyncConnection) -> list[tuple[uuid.UUID, str, str, str]]:
    owner_key_column = await _user_owner_key_column(conn)
    result = await conn.execute(
        text(
            f"SELECT id, email, {owner_key_column} AS local_owner_key, created_at::text AS created_at "
            "FROM users ORDER BY created_at NULLS LAST, email"
        )
    )
    return [
        (row.id, str(row.email or ""), str(row.local_owner_key or ""), str(row.created_at or ""))
        for row in result.fetchall()
    ]


async def build_report(
    conn: AsyncConnection,
    *,
    configured_local_owner_user_id: uuid.UUID | None,
    show_identifiers: bool,
) -> dict[str, Any]:
    user_rows = await _fetch_users(conn)
    users: list[UserDataSummary] = []
    public_users: list[dict[str, Any]] = []

    for user_id, email, local_owner_key, created_at in user_rows:
        row_counts: dict[str, int] = {}
        for table in DIRECT_USER_SCOPED_TABLES:
            row_counts[table.key] = await _count_for_user(conn, table.table_name, table.user_column, user_id)
        for related in RELATED_COUNTS:
            row_counts[related.key] = await _related_count_for_user(conn, related.sql, user_id)

        users.append(
            UserDataSummary(
                user_id=user_id,
                email=email,
                local_owner_key=local_owner_key,
                row_counts=row_counts,
            )
        )
        public_users.append(
            {
                "id": str(user_id),
                "email": email if show_identifiers else mask_identifier(email),
                "local_owner_key": local_owner_key if show_identifiers else mask_identifier(local_owner_key),
                "created_at": created_at,
                "row_counts": row_counts,
            }
        )

    owner_resolution = choose_local_owner(users, configured_local_owner_user_id=configured_local_owner_user_id)
    return {
        "users": public_users,
        "owner_resolution": {
            **asdict(owner_resolution),
            "user_id": str(owner_resolution.user_id) if owner_resolution.user_id is not None else None,
        },
        "global_counts": {"users": len(public_users)},
    }


def _print_report(report: dict[str, Any]):
    print("Local owner data preservation report")
    print(f"Users: {report['global_counts']['users']}")
    print("")
    owner = report["owner_resolution"]
    print(f"Owner resolution: {owner['kind']}")
    print(f"Owner user id: {owner['user_id'] or '<none>'}")
    print(f"Owner note: {owner['message']}")
    print("")

    for user in report["users"]:
        print(f"User {user['id']} email={user['email']} local_owner_key={user['local_owner_key']}")
        non_zero_counts = {key: value for key, value in user["row_counts"].items() if value}
        if not non_zero_counts:
            print("  no scoped data rows")
            continue
        for key, value in sorted(non_zero_counts.items()):
            print(f"  {key}: {value}")


async def _main_async(args: argparse.Namespace) -> int:
    database_url = _resolve_database_url(args.database_url)
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            configured_owner = _parse_uuid(args.local_owner_user_id or os.getenv("LOCAL_OWNER_USER_ID", ""))
            report = await build_report(
                conn,
                configured_local_owner_user_id=configured_owner,
                show_identifiers=args.show_identifiers,
            )
    finally:
        await engine.dispose()

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        if args.show_database_url:
            print(f"Database: {redact_database_url(database_url)}")
            print("")
        _print_report(report)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Report local owner data without modifying the database.")
    parser.add_argument("--database-url", default="", help="Override DATABASE_URL/DATABASE_URL_ASYNC.")
    parser.add_argument("--local-owner-user-id", default="", help="Override LOCAL_OWNER_USER_ID for report resolution.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--show-identifiers", action="store_true", help="Show email and local owner keys instead of masking them.")
    parser.add_argument("--show-database-url", action="store_true", help="Print the redacted database URL.")
    return asyncio.run(_main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
