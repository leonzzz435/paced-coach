import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from api.models.ai_run_cost import AiRunCost
from api.models.coach_event import CoachEvent
from api.models.coach_thread import CoachThread
from api.services import coach_memory
from api.services.ai_run_costs import AiRunCostSnapshot
from api.services.coach_event_store import EVENT_TOOL_TRACE
from services.ai.coach.athlete_model_agent import AthleteModelSummary


class _FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)


class _FakeResult:
    def __init__(self, values=None, scalar_one_or_none=None):
        self._values = values
        self._scalar_one_or_none = scalar_one_or_none

    def scalars(self):
        return _FakeScalarResult(self._values)

    def scalar_one_or_none(self):
        return self._scalar_one_or_none


class _FakeDb:
    def __init__(self, *, user, events):
        self._user = user
        self._events = events
        self.flushed = False
        self.added = []

    async def execute(self, statement):
        statement_text = str(statement)
        if "users" in statement_text:
            return _FakeResult(scalar_one_or_none=self._user)
        return _FakeResult(self._events)

    def add(self, _obj):
        self.added.append(_obj)

    async def flush(self):
        self.flushed = True


def test_extract_last_summary_seq_is_thread_scoped_only():
    athlete_model = {
        "_meta": {
            "last_summary_seq": 14,
            "thread_last_summary_seq": {
                "known-thread": 6,
            },
        }
    }

    assert coach_memory._extract_last_summary_seq(athlete_model, thread_id="known-thread") == 6
    assert coach_memory._extract_last_summary_seq(athlete_model, thread_id="missing-thread") == 0


@pytest.mark.asyncio
async def test_maybe_update_thread_memory_maps_confidence_entries_to_dict(monkeypatch):
    thread_id = uuid.uuid4()
    user_id = uuid.uuid4()
    thread = CoachThread(
        id=thread_id,
        user_id=user_id,
        latest_seq=2,
        status="active",
    )
    user_state = SimpleNamespace(id=user_id, memory_summary=None, athlete_model={})

    events = [
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=1,
            event_type="user_message",
            actor="user",
            payload={"text": "I felt tired last Thursday"},
            created_at=datetime.now(UTC),
        ),
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=2,
            event_type="coach_message",
            actor="coach",
            payload={"text": "We can reduce intensity tomorrow"},
            created_at=datetime.now(UTC),
        ),
    ]
    fake_db = _FakeDb(user=user_state, events=events)

    async def _fake_summarize(*, previous_model: dict, recent_events: list[dict], invoke_config=None):
        _ = previous_model
        _ = recent_events
        _ = invoke_config
        return AthleteModelSummary.model_validate(
            {
                "training_preferences": [],
                "schedule_constraints": [],
                "response_patterns": [],
                "injury_risk_notes": ["reported fatigue"],
                "transient_state_notes": [
                    {
                        "topic": "illness",
                        "status": "active",
                        "summary": "Reported cold symptoms and low energy.",
                        "first_observed_at": "2026-02-10T09:00:00+00:00",
                        "last_observed_at": "2026-02-10T09:00:00+00:00",
                    }
                ],
                "motivation_style": None,
                "goal_state": None,
                "confidence_by_field": [{"field_name": "injury_risk_notes", "confidence": 0.72}],
                "memory_summary": "Athlete reported fatigue; keep next hard session flexible.",
            }
        )

    monkeypatch.setattr(coach_memory, "summarize_athlete_model", _fake_summarize)
    monkeypatch.setattr(
        coach_memory,
        "capture_langsmith_run_costs",
        lambda *_args, **_kwargs: AiRunCostSnapshot(cost_status="captured", total_cost_usd=0.01, total_tokens=111),
    )

    updated = await coach_memory.maybe_update_thread_memory(
        cast("Any", fake_db),
        thread=thread,
        salient=True,
    )

    assert updated is True
    assert fake_db.flushed is True
    assert user_state.memory_summary == "Athlete reported fatigue; keep next hard session flexible."
    assert isinstance(user_state.athlete_model, dict)
    assert any(isinstance(item, AiRunCost) and item.feature == "coach_memory" for item in fake_db.added)
    assert user_state.athlete_model["confidence_by_field"] == {"injury_risk_notes": 0.72}
    assert user_state.athlete_model["transient_state_notes"][0]["topic"] == "illness"
    assert user_state.athlete_model["transient_state_notes"][0]["status"] == "active"
    meta = user_state.athlete_model["_meta"]
    assert isinstance(meta, dict)
    assert meta["thread_last_summary_seq"][str(thread_id)] == 2
    assert "last_summary_seq" not in meta


@pytest.mark.asyncio
async def test_maybe_update_thread_memory_excludes_tool_and_context_summary_events(monkeypatch):
    thread_id = uuid.uuid4()
    user_id = uuid.uuid4()
    thread = CoachThread(
        id=thread_id,
        user_id=user_id,
        latest_seq=3,
        status="active",
    )
    user_state = SimpleNamespace(id=user_id, memory_summary=None, athlete_model={})
    events = [
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=1,
            event_type=EVENT_TOOL_TRACE,
            actor="system",
            payload={"tool_name": "get_training_snapshot"},
            created_at=datetime.now(UTC),
        ),
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=2,
            event_type="context_summary",
            actor="system",
            payload={"summary_text": "old summary"},
            created_at=datetime.now(UTC),
        ),
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=3,
            event_type="user_message",
            actor="user",
            payload={"text": "I felt great this week"},
            created_at=datetime.now(UTC),
        ),
    ]
    fake_db = _FakeDb(user=user_state, events=events)

    captured_event_types: list[str] = []

    async def _fake_summarize(*, previous_model: dict, recent_events: list[dict], invoke_config=None):
        _ = previous_model
        _ = invoke_config
        captured_event_types.extend([event["event_type"] for event in recent_events])
        return AthleteModelSummary.model_validate(
            {
                "training_preferences": [],
                "schedule_constraints": [],
                "response_patterns": [],
                "injury_risk_notes": [],
                "transient_state_notes": [],
                "motivation_style": None,
                "goal_state": None,
                "confidence_by_field": [],
                "memory_summary": "summary",
            }
        )

    monkeypatch.setattr(coach_memory, "summarize_athlete_model", _fake_summarize)

    updated = await coach_memory.maybe_update_thread_memory(
        cast("Any", fake_db),
        thread=thread,
        salient=True,
    )

    assert updated is True
    assert captured_event_types == ["user_message"]


@pytest.mark.asyncio
async def test_maybe_update_thread_memory_ignores_legacy_global_progress_and_preserves_other_threads(monkeypatch):
    thread_id = uuid.uuid4()
    other_thread_id = uuid.uuid4()
    user_id = uuid.uuid4()
    thread = CoachThread(
        id=thread_id,
        user_id=user_id,
        latest_seq=2,
        status="active",
    )
    user_state = SimpleNamespace(
        id=user_id,
        memory_summary="older summary",
        athlete_model={
            "goal_state": "Build",
            "_meta": {
                "last_summary_seq": 14,
                "thread_last_summary_seq": {
                    str(other_thread_id): 7,
                },
                "updated_at": "2026-03-01T00:00:00+00:00",
            },
        },
    )

    events = [
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=1,
            event_type="user_message",
            actor="user",
            payload={"text": "Thread-specific detail one"},
            created_at=datetime.now(UTC),
        ),
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=2,
            event_type="coach_message",
            actor="coach",
            payload={"text": "Thread-specific detail two"},
            created_at=datetime.now(UTC),
        ),
    ]
    fake_db = _FakeDb(user=user_state, events=events)
    captured_previous_model: dict | None = None

    async def _fake_summarize(*, previous_model: dict, recent_events: list[dict], invoke_config=None):
        nonlocal captured_previous_model
        _ = recent_events
        _ = invoke_config
        captured_previous_model = previous_model
        return AthleteModelSummary.model_validate(
            {
                "training_preferences": [],
                "schedule_constraints": [],
                "response_patterns": [],
                "injury_risk_notes": [],
                "transient_state_notes": [],
                "motivation_style": None,
                "goal_state": "Build",
                "confidence_by_field": [],
                "memory_summary": "new summary",
            }
        )

    monkeypatch.setattr(coach_memory, "summarize_athlete_model", _fake_summarize)

    updated = await coach_memory.maybe_update_thread_memory(
        cast("Any", fake_db),
        thread=thread,
        force=True,
    )

    assert updated is True
    assert captured_previous_model is not None
    assert captured_previous_model["goal_state"] == "Build"
    captured_meta = captured_previous_model["_meta"]
    assert "last_summary_seq" not in captured_meta
    assert captured_meta["thread_last_summary_seq"] == {
        str(other_thread_id): 7,
    }

    meta = user_state.athlete_model["_meta"]
    assert meta["thread_last_summary_seq"] == {
        str(other_thread_id): 7,
        str(thread_id): 2,
    }
    assert "last_summary_seq" not in meta


@pytest.mark.asyncio
async def test_maybe_update_thread_memory_repairs_legacy_meta_even_without_new_events():
    thread_id = uuid.uuid4()
    user_id = uuid.uuid4()
    thread = CoachThread(
        id=thread_id,
        user_id=user_id,
        latest_seq=2,
        status="active",
    )
    user_state = SimpleNamespace(
        id=user_id,
        memory_summary="older summary",
        athlete_model={
            "goal_state": "Build",
            "_meta": {
                "last_summary_seq": 14,
                "thread_last_summary_seq": {
                    str(thread_id): 2,
                },
                "updated_at": "2026-03-01T00:00:00+00:00",
            },
        },
    )
    fake_db = _FakeDb(user=user_state, events=[])

    updated = await coach_memory.maybe_update_thread_memory(
        cast("Any", fake_db),
        thread=thread,
        force=True,
    )

    assert updated is False
    assert user_state.athlete_model == {
        "goal_state": "Build",
        "_meta": {
            "thread_last_summary_seq": {
                str(thread_id): 2,
            },
            "updated_at": "2026-03-01T00:00:00+00:00",
        },
    }
    assert fake_db.added == [user_state]
