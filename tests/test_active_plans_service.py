import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.active_plans import get_active_analysis, get_active_season_plan, get_active_weekly_plan


@pytest.mark.asyncio
async def test_get_active_weekly_plan_normalizes_payload_version_to_row_version():
    user_id = uuid.uuid4()
    active = SimpleNamespace(
        version=5,
        plan_data={"type": "weekly_plan", "schema_version": 2, "version": 1, "plan_id": "w1"},
        source_job_id=uuid.uuid4(),
        updated_at=SimpleNamespace(isoformat=lambda: "2026-02-21T00:00:00+00:00"),
    )
    row = MagicMock()
    row.scalar_one_or_none.return_value = active
    db = AsyncMock()
    db.execute.return_value = row

    payload = await get_active_weekly_plan(db, user_id=user_id)

    assert payload is not None
    assert payload["version"] == 5
    assert payload["weekly_plan"]["version"] == 5


@pytest.mark.asyncio
async def test_get_active_season_plan_normalizes_payload_version_to_row_version():
    user_id = uuid.uuid4()
    active = SimpleNamespace(
        version=7,
        plan_data={"type": "season_plan", "schema_version": 2, "version": 1, "plan_id": "s1"},
        source_job_id=uuid.uuid4(),
        updated_at=SimpleNamespace(isoformat=lambda: "2026-02-21T00:00:00+00:00"),
    )
    row = MagicMock()
    row.scalar_one_or_none.return_value = active
    db = AsyncMock()
    db.execute.return_value = row

    payload = await get_active_season_plan(db, user_id=user_id)

    assert payload is not None
    assert payload["version"] == 7
    assert payload["season_plan"]["version"] == 7


@pytest.mark.asyncio
async def test_get_active_analysis_normalizes_payload_version_to_row_version():
    user_id = uuid.uuid4()
    active = SimpleNamespace(
        version=9,
        analysis_data={"type": "analysis", "schema_version": 2, "version": 1, "analysis_id": "a1"},
        expert_context={},
        source_job_id=uuid.uuid4(),
        updated_at=SimpleNamespace(isoformat=lambda: "2026-02-21T00:00:00+00:00"),
    )
    row = MagicMock()
    row.scalar_one_or_none.return_value = active
    db = AsyncMock()
    db.execute.return_value = row

    payload = await get_active_analysis(db, user_id=user_id)

    assert payload is not None
    assert payload["version"] == 9
    assert payload["analysis"]["version"] == 9
