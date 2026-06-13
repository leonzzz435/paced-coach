from typing import Any, cast

import pytest
from fastapi import HTTPException

from api.routers import health


@pytest.mark.asyncio
async def test_readiness_check_returns_ready_when_all_dependencies_pass(monkeypatch):
    async def _fake_database_ready():
        return None

    async def _fake_redis_ready():
        return None

    monkeypatch.setattr(health, "_check_database_ready", _fake_database_ready)
    monkeypatch.setattr(health, "_check_redis_ready", _fake_redis_ready)

    assert await health.readiness_check() == {
        "status": "ready",
        "checks": {
            "database": "ok",
            "redis": "ok",
        },
    }


@pytest.mark.asyncio
async def test_readiness_check_returns_503_when_dependency_fails(monkeypatch):
    async def _fake_database_ready():
        return None

    async def _fake_redis_ready():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(health, "_check_database_ready", _fake_database_ready)
    monkeypatch.setattr(health, "_check_redis_ready", _fake_redis_ready)

    with pytest.raises(HTTPException) as exc:
        await health.readiness_check()

    assert exc.value.status_code == 503
    detail = cast("dict[str, Any]", exc.value.detail)
    assert detail == {
        "status": "not_ready",
        "checks": {
            "database": "ok",
            "redis": "error",
        },
        "failures": {
            "redis": "RuntimeError",
        },
    }
