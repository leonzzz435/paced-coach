#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.config import get_settings
from api.services.local_owner_preservation import (
    DIRECT_USER_SCOPED_TABLES,
    UNIQUE_CONFLICT_SPECS,
    UniqueConflictSpec,
    normalize_async_database_url,
)


def _resolve_database_url(cli_database_url: str) -> str:
    raw_url = (
        cli_database_url
        or os.getenv("DATABASE_URL_ASYNC", "")
        or os.getenv("DATABASE_URL", "")
        or get_settings().database_url_async
    )
    return normalize_async_database_url(raw_url)


def _parse_required_uuid(raw_value: str, *, name: str) -> uuid.UUID:
    value = raw_value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return uuid.UUID(value)


async def _table_exists(conn: AsyncConnection, table_name: str) -> bool:
    result = await conn.execute(text("SELECT to_regclass(:table_name) IS NOT NULL"), {"table_name": table_name})
    return bool(result.scalar_one())


async def _user_exists(conn: AsyncConnection, user_id: uuid.UUID) -> bool:
    result = await conn.execute(text("SELECT EXISTS (SELECT 1 FROM users WHERE id = :user_id)"), {"user_id": user_id})
    return bool(result.scalar_one())


async def _count_for_user(conn: AsyncConnection, table_name: str, user_column: str, user_id: uuid.UUID) -> int:
    if not await _table_exists(conn, table_name):
        return 0
    result = await conn.execute(
        text(f"SELECT count(*) FROM {table_name} WHERE {user_column} = :user_id"),
        {"user_id": user_id},
    )
    return int(result.scalar_one())


async def _find_unique_conflicts(
    conn: AsyncConnection,
    spec: UniqueConflictSpec,
    *,
    source_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> list[str]:
    if not await _table_exists(conn, spec.table_name):
        return []

    if not spec.key_columns:
        source_count = await _count_for_user(conn, spec.table_name, spec.user_column, source_user_id)
        target_count = await _count_for_user(conn, spec.table_name, spec.user_column, target_user_id)
        if source_count and target_count:
            return [f"{source_count} source row(s), {target_count} target row(s)"]
        return []

    join_predicate = " AND ".join(f"s.{column} = t.{column}" for column in spec.key_columns)
    projection = " || ', ' || ".join(f"s.{column}::text" for column in spec.key_columns)
    sql = (
        f"SELECT {projection} AS conflict_key FROM {spec.table_name} s "
        f"JOIN {spec.table_name} t ON {join_predicate} "
        f"WHERE s.{spec.user_column} = :source_user_id AND t.{spec.user_column} = :target_user_id "
        "ORDER BY conflict_key LIMIT 20"
    )
    result = await conn.execute(
        text(sql),
        {"source_user_id": source_user_id, "target_user_id": target_user_id},
    )
    return [str(row.conflict_key) for row in result.fetchall()]


async def _build_plan(
    conn: AsyncConnection,
    *,
    source_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> dict[str, Any]:
    if source_user_id == target_user_id:
        raise ValueError("source and target users must be different.")
    if not await _user_exists(conn, source_user_id):
        raise ValueError(f"source user does not exist: {source_user_id}")
    if not await _user_exists(conn, target_user_id):
        raise ValueError(f"target user does not exist: {target_user_id}")

    updates: list[dict[str, Any]] = []
    for table in DIRECT_USER_SCOPED_TABLES:
        source_count = await _count_for_user(conn, table.table_name, table.user_column, source_user_id)
        target_count = await _count_for_user(conn, table.table_name, table.user_column, target_user_id)
        updates.append(
            {
                "table": table.table_name,
                "label": table.label,
                "user_column": table.user_column,
                "source_rows": source_count,
                "target_rows_before": target_count,
            }
        )

    conflicts: list[dict[str, Any]] = []
    for spec in UNIQUE_CONFLICT_SPECS:
        conflict_keys = await _find_unique_conflicts(
            conn,
            spec,
            source_user_id=source_user_id,
            target_user_id=target_user_id,
        )
        if conflict_keys:
            conflicts.append(
                {
                    "table": spec.table_name,
                    "label": spec.label,
                    "key_columns": list(spec.key_columns),
                    "conflicts": conflict_keys,
                }
            )

    return {
        "source_user_id": str(source_user_id),
        "target_user_id": str(target_user_id),
        "updates": updates,
        "conflicts": conflicts,
        "safe_to_execute": not conflicts,
    }


async def _execute_plan(
    conn: AsyncConnection,
    plan: dict[str, Any],
    *,
    source_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> dict[str, int]:
    updated_rows: dict[str, int] = {}
    for item in plan["updates"]:
        table_name = item["table"]
        user_column = item["user_column"]
        if item["source_rows"] == 0:
            updated_rows[table_name] = 0
            continue
        result = await conn.execute(
            text(f"UPDATE {table_name} SET {user_column} = :target_user_id WHERE {user_column} = :source_user_id"),
            {"source_user_id": source_user_id, "target_user_id": target_user_id},
        )
        updated_rows[table_name] = int(result.rowcount or 0)
    return updated_rows


def _print_plan(plan: dict[str, Any], *, executed: bool):
    mode = "EXECUTED" if executed else "DRY RUN"
    print(f"Local owner migration plan ({mode})")
    print(f"Source user: {plan['source_user_id']}")
    print(f"Target user: {plan['target_user_id']}")
    print(f"Safe to execute: {plan['safe_to_execute']}")
    print("")
    if plan["conflicts"]:
        print("Conflicts:")
        for conflict in plan["conflicts"]:
            joined_keys = "; ".join(conflict["conflicts"])
            print(f"  {conflict['table']}: {joined_keys}")
        print("")
    print("Planned row updates:")
    for item in plan["updates"]:
        if item["source_rows"] or item["target_rows_before"]:
            print(
                f"  {item['table']}: source={item['source_rows']} "
                f"target_before={item['target_rows_before']}"
            )
    if executed:
        print("")
        print("Updated rows:")
        for table_name, row_count in sorted(plan["updated_rows"].items()):
            if row_count:
                print(f"  {table_name}: {row_count}")
    else:
        print("")
        print("No rows were changed. Re-run with --execute only after taking a backup and reviewing conflicts.")


async def _main_async(args: argparse.Namespace) -> int:
    source_user_id = _parse_required_uuid(args.source_user_id, name="--source-user-id")
    target_user_id = _parse_required_uuid(args.target_user_id, name="--target-user-id")
    database_url = _resolve_database_url(args.database_url)
    engine = create_async_engine(database_url)
    executed = False
    try:
        if args.execute:
            async with engine.begin() as conn:
                plan = await _build_plan(conn, source_user_id=source_user_id, target_user_id=target_user_id)
                if plan["conflicts"]:
                    raise RuntimeError("Migration has unique-key conflicts; no rows were changed.")
                plan["updated_rows"] = await _execute_plan(
                    conn,
                    plan,
                    source_user_id=source_user_id,
                    target_user_id=target_user_id,
                )
                executed = True
        else:
            async with engine.connect() as conn:
                plan = await _build_plan(conn, source_user_id=source_user_id, target_user_id=target_user_id)
    finally:
        await engine.dispose()

    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        _print_plan(plan, executed=executed)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Move user-scoped local data from one existing user to another. Defaults to dry-run."
    )
    parser.add_argument("--database-url", default="", help="Override DATABASE_URL/DATABASE_URL_ASYNC.")
    parser.add_argument("--source-user-id", required=True, help="Existing user id that currently owns rows.")
    parser.add_argument("--target-user-id", required=True, help="Existing local owner user id that should own rows.")
    parser.add_argument("--execute", action="store_true", help="Actually update rows. Without this, dry-run only.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    return asyncio.run(_main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
