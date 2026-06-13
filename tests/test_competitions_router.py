import uuid
from datetime import date
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.competitions import CompetitionIn, update_competition


class _FakeSelectResult:
    def __init__(self, competition):
        self.competition = competition

    def scalar_one_or_none(self):
        return self.competition


class _FakeDb:
    def __init__(self, competition):
        self.competition = competition
        self.committed = False
        self.refreshed = None

    async def execute(self, _statement):
        return _FakeSelectResult(self.competition)

    async def commit(self):
        self.committed = True

    async def refresh(self, competition):
        self.refreshed = competition


@pytest.mark.asyncio
async def test_update_competition_edits_existing_row():
    user_id = uuid.uuid4()
    competition_id = uuid.uuid4()
    competition = SimpleNamespace(
        id=competition_id,
        user_id=user_id,
        name="Old Race",
        date=None,
        date_text=None,
        race_type=None,
        priority=None,
        target_time=None,
        notes=None,
    )
    db = _FakeDb(competition)

    result = await update_competition(
        competition_id,
        CompetitionIn(
            name="  New Race  ",
            date=date(2026, 10, 11),
            race_type=" Half Marathon ",
            priority=" A ",
            target_time=" 01:40:00 ",
            notes=" Rolling course ",
        ),
        cast("AsyncSession", db),
        user_id,
    )

    assert result.id == str(competition_id)
    assert result.name == "New Race"
    assert result.date == date(2026, 10, 11)
    assert result.race_type == "Half Marathon"
    assert result.priority == "A"
    assert result.target_time == "01:40:00"
    assert result.notes == "Rolling course"
    assert competition.name == "New Race"
    assert db.committed is True
    assert db.refreshed is competition


@pytest.mark.asyncio
async def test_update_competition_returns_404_for_missing_row():
    db = _FakeDb(None)

    with pytest.raises(HTTPException) as exc_info:
        await update_competition(
            uuid.uuid4(),
            CompetitionIn(name="Race"),
            cast("AsyncSession", db),
            uuid.uuid4(),
        )

    assert exc_info.value.status_code == 404
    assert db.committed is False
