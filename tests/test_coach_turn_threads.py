import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from api.models.coach_event import CoachEvent
from api.services import coach_turn
from api.services.coach_event_store import EVENT_RECAP_NARRATIVE, EVENT_RECAP_RESPONSE, EVENT_USER_MESSAGE


@pytest.mark.asyncio
async def test_archive_coach_thread_forces_memory_flush(monkeypatch):
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    active_thread = SimpleNamespace(
        id=thread_id,
        user_id=user_id,
        status="active",
        title="Marathon taper week question",
        latest_seq=9,
        updated_at=datetime.now(UTC),
    )
    archived_thread = SimpleNamespace(
        id=thread_id,
        user_id=user_id,
        status="archived",
        title="Marathon taper week question",
        latest_seq=9,
        updated_at=datetime.now(UTC),
    )

    get_coach_thread_by_id = AsyncMock(return_value=active_thread)
    maybe_update_thread_memory = AsyncMock(return_value=True)
    archive_coach_thread = AsyncMock(return_value=archived_thread)

    monkeypatch.setattr(coach_turn, "get_coach_thread_by_id", get_coach_thread_by_id)
    monkeypatch.setattr(coach_turn, "maybe_update_thread_memory", maybe_update_thread_memory)
    monkeypatch.setattr(coach_turn, "archive_coach_thread", archive_coach_thread)
    db = SimpleNamespace(refresh=AsyncMock())

    result = await coach_turn.archive_coach_thread_v2(
        cast("Any", db),
        user_id=user_id,
        thread_id=thread_id,
    )

    db.refresh.assert_awaited_once_with(
        archived_thread,
        attribute_names=["updated_at", "status", "title", "latest_seq"],
    )
    maybe_update_thread_memory.assert_awaited_once()
    assert maybe_update_thread_memory.await_args is not None
    assert maybe_update_thread_memory.await_args.kwargs["force"] is True
    archive_coach_thread.assert_awaited_once()
    assert result["thread"]["id"] == str(thread_id)
    assert result["thread"]["status"] == "archived"
    assert result["thread"]["title"] == "Marathon taper week question"


class _CountResult:
    def __init__(self, value: int):
        self._value = value

    def scalar_one(self):
        return self._value


class _CountDb:
    def __init__(self, value: int):
        self._value = value

    async def execute(self, _statement):
        return _CountResult(self._value)


class _FlushDb:
    def __init__(self):
        self.added: list[object] = []
        self.flushed = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


class _ScalarRowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _ExecuteResult:
    def __init__(self, *, rows=None, scalars=None):
        self._rows = rows or []
        self._scalars = scalars or []

    def all(self):
        return list(self._rows)

    def scalars(self):
        return _ScalarRowsResult(self._scalars)


class _SequentialDb:
    def __init__(self, responses):
        self._responses = iter(responses)

    async def execute(self, _statement):
        return next(self._responses)


@pytest.mark.asyncio
async def test_ensure_thread_iteration_limit_blocks_when_limit_reached(monkeypatch):
    thread_id = uuid.uuid4()
    monkeypatch.setattr(coach_turn, "_thread_iteration_limit", lambda: 15)

    with pytest.raises(HTTPException) as exc:
        await coach_turn._ensure_thread_iteration_limit(
            cast("Any", _CountDb(15)),
            thread=cast("Any", SimpleNamespace(id=thread_id)),
        )

    assert exc.value.status_code == 409
    assert "limit=15" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_ensure_thread_iteration_limit_allows_when_under_limit(monkeypatch):
    thread_id = uuid.uuid4()
    monkeypatch.setattr(coach_turn, "_thread_iteration_limit", lambda: 15)

    await coach_turn._ensure_thread_iteration_limit(
        cast("Any", _CountDb(14)),
        thread=cast("Any", SimpleNamespace(id=thread_id)),
    )


@pytest.mark.asyncio
async def test_maybe_set_thread_title_from_first_exchange_sets_title(monkeypatch):
    db = _FlushDb()
    thread = SimpleNamespace(title=None)
    monkeypatch.setattr(
        coach_turn,
        "generate_thread_title_from_exchange",
        AsyncMock(return_value="Marathon taper week question"),
    )

    await coach_turn._maybe_set_thread_title_from_first_exchange(
        cast("Any", db),
        thread=cast("Any", thread),
        user_message="Should I keep the tempo run this week?",
        turn_payload={"assistant_message": "Let's reduce intensity for your taper."},
    )

    assert thread.title == "Marathon taper week question"
    assert db.flushed is True


@pytest.mark.asyncio
async def test_maybe_set_thread_title_from_first_exchange_keeps_existing_title(monkeypatch):
    db = _FlushDb()
    thread = SimpleNamespace(title="Existing title")
    generator = AsyncMock(return_value="Ignored")
    monkeypatch.setattr(coach_turn, "generate_thread_title_from_exchange", generator)

    await coach_turn._maybe_set_thread_title_from_first_exchange(
        cast("Any", db),
        thread=cast("Any", thread),
        user_message="Any message",
        turn_payload={"assistant_message": "Any reply"},
    )

    assert thread.title == "Existing title"
    assert db.flushed is False
    generator.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_coach_threads_hydrates_answered_recap_follow_up(monkeypatch):
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    recap_run_id = uuid.uuid4()
    created_at = datetime.now(UTC)
    response_text = "The climbs felt smooth and controlled."

    monkeypatch.setattr(
        coach_turn,
        "list_coach_threads",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=thread_id,
                    status="active",
                    title="Weekly Recap",
                    latest_seq=3,
                    created_at=created_at,
                    updated_at=created_at,
                )
            ]
        ),
    )

    fake_db = _SequentialDb(
        [
            _ExecuteResult(
                scalars=[
                    CoachEvent(
                        id=uuid.uuid4(),
                        thread_id=thread_id,
                        seq=1,
                        event_type=EVENT_RECAP_NARRATIVE,
                        actor="coach",
                        payload={
                            "recap": {
                                "run_id": str(recap_run_id),
                                "follow_up_question": "Did the climbs feel smooth?",
                                "athlete_response": None,
                                "narrative": {"this_week_blocks": [], "looking_ahead_blocks": []},
                            }
                        },
                        created_at=created_at,
                    ),
                    CoachEvent(
                        id=uuid.uuid4(),
                        thread_id=thread_id,
                        seq=2,
                        event_type=EVENT_USER_MESSAGE,
                        actor="user",
                        payload={"text": response_text},
                        created_at=created_at,
                    ),
                    CoachEvent(
                        id=uuid.uuid4(),
                        thread_id=thread_id,
                        seq=3,
                        event_type=EVENT_RECAP_RESPONSE,
                        actor="user",
                        payload={"recap_run_id": str(recap_run_id), "response": response_text},
                        created_at=created_at,
                    ),
                ]
            ),
            _ExecuteResult(rows=[]),
            _ExecuteResult(rows=[(recap_run_id, "Did the climbs feel smooth?", response_text)]),
        ]
    )

    result = await coach_turn.list_coach_threads_v2(
        cast("Any", fake_db),
        user_id=user_id,
        limit=20,
        offset=0,
    )

    assert len(result["items"]) == 1
    assert len(result["items"][0]["messages"]) == 2
    assert result["items"][0]["messages"][0]["kind"] == "recap"
    assert result["items"][0]["messages"][0]["recap"]["athlete_response"] == response_text
    assert result["items"][0]["messages"][1]["kind"] == "text"
    assert result["items"][0]["messages"][1]["text"] == response_text
