import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from api.config import get_settings
from api.deps import engine
from core.version_manifest import get_release_version, get_version_manifest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> dict:
    git_sha = os.getenv("GIT_SHA") or "unknown"
    environment = os.getenv("APP_ENV") or "local"
    manifest = get_version_manifest()
    return {
        "status": "healthy",
        "env": environment,
        "git_sha": git_sha,
        "release_version": get_release_version(),
        "ui_schema_version": manifest.components.ui_schema.current_schema_version,
        "db_schema_version": manifest.components.db_schema.version,
    }

async def _check_database_ready() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


def _ping_redis_sync(redis_url: str) -> None:
    from redis import Redis

    client = Redis.from_url(
        redis_url,
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
        health_check_interval=0,
    )
    try:
        if client.ping() is not True:
            raise RuntimeError("Redis ping failed")
    finally:
        client.close()


async def _check_redis_ready() -> None:
    redis_url = get_settings().redis_url.strip()
    if not redis_url:
        raise RuntimeError("REDIS_URL is not configured")
    await asyncio.to_thread(_ping_redis_sync, redis_url)


@router.get("/ready")
async def readiness_check() -> dict[str, object]:
    checks: dict[str, str] = {}
    failures: dict[str, str] = {}

    for name, check in (
        ("database", _check_database_ready),
        ("redis", _check_redis_ready),
    ):
        try:
            await check()
            checks[name] = "ok"
        except Exception as exc:
            logger.warning("Readiness check failed for %s: %s", name, type(exc).__name__)
            checks[name] = "error"
            failures[name] = type(exc).__name__

    if failures:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": checks,
                "failures": failures,
            },
        )

    return {"status": "ready", "checks": checks}
