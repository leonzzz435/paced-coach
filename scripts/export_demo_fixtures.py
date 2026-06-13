"""Export sanitized demo fixture candidates from active plan tables.

This script is intentionally manual and review-first:
- It reads the latest active analysis/season/weekly payloads for one user.
- It applies hard redaction rules.
- It writes intermediate JSON artifacts for human review before fixture promotion.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg  # type: ignore[import-untyped]
from dotenv import load_dotenv

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_TRACE_TOKEN_RE = re.compile(
    r"\b(trace[_-]?id|root[_-]?run[_-]?id|source[_-]?job[_-]?id|execution[_-]?id|run[_-]?id)\b",
    re.IGNORECASE,
)

_STRIP_KEYS = {
    "trace_id",
    "run_id",
    "root_run_id",
    "source_job_id",
    "execution_id",
    "job_id",
    "token_usage",
    "token_count",
    "cost_usd",
    "total_cost_usd",
}


def _normalize_database_url(raw_url: str) -> str:
    value = raw_url.strip()
    if value.startswith("postgresql+asyncpg://"):
        return value.replace("postgresql+asyncpg://", "postgresql://", 1)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql://", 1)
    return value


def _redact_text(value: str) -> str:
    redacted = _EMAIL_RE.sub("[redacted-email]", value)
    redacted = _UUID_RE.sub("[redacted-id]", redacted)
    redacted = _TRACE_TOKEN_RE.sub("[redacted-run-key]", redacted)
    return redacted


def _sanitize_payload(value: Any, *, display_alias: str, key_name: str | None = None) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, nested in value.items():
            normalized_key = str(key).lower()
            if normalized_key in _STRIP_KEYS:
                continue
            if normalized_key == "athlete_name":
                sanitized[str(key)] = display_alias
                continue
            cleaned = _sanitize_payload(nested, display_alias=display_alias, key_name=normalized_key)
            if normalized_key.endswith("_id") and isinstance(cleaned, str) and _UUID_RE.fullmatch(cleaned):
                sanitized[str(key)] = "demo-id"
            else:
                sanitized[str(key)] = cleaned
        return sanitized

    if isinstance(value, list):
        return [_sanitize_payload(item, display_alias=display_alias, key_name=key_name) for item in value]

    if isinstance(value, str):
        return _redact_text(value)

    return value


def _coerce_json(record_value: Any) -> dict[str, Any]:
    if isinstance(record_value, dict):
        return record_value
    if isinstance(record_value, str):
        parsed = json.loads(record_value)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Expected JSON object payload from database")


async def _fetch_latest_payloads(conn: asyncpg.Connection, user_id: str) -> dict[str, Any]:
    queries = {
        "analysis": (
            "SELECT analysis_data AS payload, updated_at FROM active_analyses WHERE user_id = $1",
        ),
        "season": (
            "SELECT plan_data AS payload, updated_at FROM active_season_plans WHERE user_id = $1",
        ),
        "weekly": (
            "SELECT plan_data AS payload, updated_at FROM active_weekly_plans WHERE user_id = $1",
        ),
    }

    output: dict[str, Any] = {}
    for label, (query,) in queries.items():
        row = await conn.fetchrow(query, user_id)
        if row is None:
            raise RuntimeError(f"Missing {label} payload for user_id={user_id}")
        payload = _coerce_json(row["payload"])
        output[label] = {
            "payload": payload,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    return output


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


async def _run(args: argparse.Namespace) -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    normalized_db_url = _normalize_database_url(database_url)
    conn = await asyncpg.connect(normalized_db_url)
    try:
        raw_payloads = await _fetch_latest_payloads(conn, args.user_id)
    finally:
        await conn.close()

    out_dir = Path(args.out_dir).expanduser().resolve() / args.persona_slug

    analysis_payload = _sanitize_payload(raw_payloads["analysis"]["payload"], display_alias=args.display_alias)
    season_payload = _sanitize_payload(raw_payloads["season"]["payload"], display_alias=args.display_alias)
    weekly_payload = _sanitize_payload(raw_payloads["weekly"]["payload"], display_alias=args.display_alias)

    _write_json(out_dir / "analysis.json", analysis_payload)
    _write_json(out_dir / "season.json", season_payload)
    _write_json(out_dir / "weekly.json", weekly_payload)

    meta_payload = {
        "persona_slug": args.persona_slug,
        "display_alias": args.display_alias,
        "exported_at": datetime.now(UTC).isoformat(),
        "source": {
            "analysis_updated_at": raw_payloads["analysis"]["updated_at"],
            "season_updated_at": raw_payloads["season"]["updated_at"],
            "weekly_updated_at": raw_payloads["weekly"]["updated_at"],
        },
        "notes": "Intermediate export only. Review and promote manually into web fixtures.",
    }
    _write_json(out_dir / "meta.json", meta_payload)

    print(f"Export complete: {out_dir}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export sanitized demo fixture candidates from local DB")
    parser.add_argument("--persona-slug", required=True, help="Persona identifier (e.g. hybrid-operator)")
    parser.add_argument("--user-id", required=True, help="Internal user UUID from users.id")
    parser.add_argument("--display-alias", required=True, help="Athlete alias used in sanitized outputs")
    parser.add_argument(
        "--out-dir",
        default="./data/demo_exports",
        help="Output directory for intermediate sanitized JSON artifacts",
    )
    return parser


def main() -> None:
    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
