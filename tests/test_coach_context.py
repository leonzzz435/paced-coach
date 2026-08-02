import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from api.models.coach_event import CoachEvent
from api.models.coach_thread import CoachThread
from api.services.coach_context import _summarize_current_weekly_plan_identity, build_turn_context
from api.services.coach_event_store import EVENT_TOOL_TRACE


class _FakeAnalysisResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDb:
    def __init__(self, *, user=None):
        self._user = user

    async def execute(self, _statement):
        statement_text = str(_statement)
        if "users" in statement_text:
            return _FakeAnalysisResult(self._user)
        return _FakeAnalysisResult(None)


class _FakeRegistry:
    def __init__(self):
        self.current_weekly_plan_called = False

    async def get_upcoming_competitions(self):
        return [{"name": "A race", "date": "2026-03-11"}]

    async def get_current_weekly_plan(self):
        self.current_weekly_plan_called = True
        return {
            "plan_id": "plan-1",
            "version": 7,
            "updated_at": "2026-02-27T06:00:00+00:00",
            "weeks": [
                {
                    "week_id": "wk-2026-02-23",
                    "week_label": "Build",
                    "start_date": "2026-02-23",
                    "end_date": "2026-03-01",
                    "days": [
                        {
                            "day_id": "2026-02-27",
                            "date": "2026-02-27",
                            "day_label": "Fri — Strength-Endurance",
                            "workout_title": "Strength-Endurance",
                            "focus_type": "strength-endurance",
                            "estimated_duration_min": 75,
                            "estimated_intensity": "high",
                            "is_completed": False,
                        }
                    ],
                }
            ],
        }

    async def get_current_season_plan(self):
        return {"schema_version": 3, "strategy_id": "strategy-1"}

    def get_observability_snapshot(self):
        return {
            "tool_usage": {},
            "cache_keys": [],
            "source_of_truth": "local_athlete_owned",
        }


@pytest.mark.asyncio
async def test_build_turn_context_coach_chat_mode_skips_prefetch_and_includes_tiers():
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    thread = CoachThread(id=thread_id, user_id=user_id, latest_seq=3, status="active")
    registry = _FakeRegistry()
    recent_events = [
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=1,
            event_type="user_message",
            actor="user",
            payload={"text": "How am I doing?"},
            created_at=datetime.now(UTC),
        ),
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=2,
            event_type=EVENT_TOOL_TRACE,
            actor="system",
            payload={
                "turn_seq_anchor": 1,
                "tool_name": "get_training_snapshot",
                "args": {},
                "result_preview": '{"sessions_7d":5}',
                "char_len": 20,
                "truncated": False,
                "result_hash": "abc",
            },
            created_at=datetime.now(UTC),
        ),
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=3,
            event_type="coach_message",
            actor="coach",
            payload={"text": "Solid week overall. Keep Thursday easy."},
            created_at=datetime.now(UTC),
        ),
    ]

    context = await build_turn_context(
        _FakeDb(
            user=SimpleNamespace(
                memory_summary="Athlete responds best to concise guidance.",
                athlete_model={"goal_state": "build"},
            )
        ),  # type: ignore[arg-type]
        user_id=user_id,
        thread=thread,
        recent_events=recent_events,
        mode="coach_chat",
        tool_registry=registry,  # type: ignore[arg-type]
        user_message="How am I doing?",
        ui_context={"source": "today_mission", "day": {"day_id": "2026-02-27"}},
    )

    assert registry.current_weekly_plan_called is True
    assert context["mode"] == "coach_chat"
    assert isinstance(context["now_utc"], str)
    assert context["ui_context"] == {"source": "today_mission", "day": {"day_id": "2026-02-27"}}
    assert context["current_season_plan"]["strategy_id"] == "strategy-1"
    assert context["current_weekly_plan_identity"]["plan_id"] == "plan-1"
    assert context["current_weekly_plan_identity"]["schema_version"] == 1
    assert context["current_weekly_plan_identity"]["weeks"][0]["week_id"] == "wk-2026-02-23"
    assert context["current_weekly_plan_identity"]["weeks"][0]["days"][0]["day_id"] == "2026-02-27"
    assert context["current_weekly_plan_identity"]["weeks"][0]["days"][0]["workout_title"] == "Strength-Endurance"
    assert context["tool_budget"]["tools_called_current_turn_pre_call"] == 0
    assert context["tool_budget"]["tools_called_last_turn"] == 1
    assert context["tool_budget"]["tools_called_prior_turns"] == 1
    assert context["memory_summary"] == "Athlete responds best to concise guidance."
    assert context["athlete_model"] == {"goal_state": "build"}
    assert context["long_term_memory"]["transient_state_notes"] == []
    assert context["long_term_memory"]["memory_updated_at"] is None
    assert context["long_term_memory"]["memory_age_days"] is None
    assert context["tool_observability"]["source_of_truth"] == "local_athlete_owned"
    assert len(context["recent_tool_results"]) == 1
    assert len(context["recent_events"]) == 3


@pytest.mark.asyncio
async def test_build_turn_context_proactive_mode_uses_same_local_sources():
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    thread = CoachThread(id=thread_id, user_id=user_id, latest_seq=1, status="active")
    registry = _FakeRegistry()
    recent_events = [
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=1,
            event_type="user_message",
            actor="user",
            payload={"text": "Hi"},
            created_at=datetime.now(UTC),
        )
    ]

    context = await build_turn_context(
        _FakeDb(user=SimpleNamespace(memory_summary="Summary", athlete_model={"goal_state": "A-race"})),  # type: ignore[arg-type]
        user_id=user_id,
        thread=thread,
        recent_events=recent_events,
        mode="proactive_eval",
        tool_registry=registry,  # type: ignore[arg-type]
        user_message="Daily readiness and training status check.",
    )

    assert registry.current_weekly_plan_called is True
    assert context["mode"] == "proactive_eval"
    assert context["current_season_plan"]["strategy_id"] == "strategy-1"
    assert context["current_weekly_plan_identity"]["weeks"][0]["days"][0]["day_label"] == "Fri — Strength-Endurance"
    assert context["derived_context"]["competition_context"]["competition_proximity_days"] is None
    assert context["long_term_memory"]["athlete_model"] == {"goal_state": "A-race"}


def test_schema_v3_plan_identity_preserves_day_and_session_patch_targets():
    identity = _summarize_current_weekly_plan_identity(
        {
            "schema_version": 3,
            "plan_id": "execution-3",
            "version": 4,
            "weeks": [
                {
                    "week_id": "week-1",
                    "title": "Foundation",
                    "start_date": "2026-08-03",
                    "end_date": "2026-08-09",
                    "days": [
                        {
                            "day_id": "day-2026-08-03",
                            "date": "2026-08-03",
                            "label": "Monday",
                            "focus_type": "aerobic",
                            "intensity": "low",
                            "total_duration_min": 45,
                            "is_completed": False,
                            "sessions": [
                                {
                                    "session_id": "session-2026-08-03-run",
                                    "title": "Easy run",
                                    "duration_min": 45,
                                    "intensity": "low",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    assert identity is not None
    assert identity["schema_version"] == 3
    assert identity["weeks"][0]["title"] == "Foundation"
    day = identity["weeks"][0]["days"][0]
    assert day["label"] == "Monday"
    assert day["total_duration_min"] == 45
    assert day["sessions"][0]["session_id"] == "session-2026-08-03-run"
    assert "workout_title" not in day


@pytest.mark.asyncio
async def test_build_turn_context_includes_memory_freshness_when_meta_timestamp_exists():
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    thread = CoachThread(id=thread_id, user_id=user_id, latest_seq=1, status="active")
    registry = _FakeRegistry()
    recent_events = [
        CoachEvent(
            id=uuid.uuid4(),
            thread_id=thread_id,
            seq=1,
            event_type="user_message",
            actor="user",
            payload={"text": "Hi"},
            created_at=datetime.now(UTC),
        )
    ]
    updated_at = datetime.now(UTC).isoformat()

    context = await build_turn_context(
        _FakeDb(
            user=SimpleNamespace(
                memory_summary="Summary",
                athlete_model={
                    "goal_state": "A-race",
                    "transient_state_notes": [
                        {
                            "topic": "illness",
                            "status": "recovering",
                            "summary": "Reported flu symptoms, now improving.",
                            "first_observed_at": "2026-02-20T09:00:00+00:00",
                            "last_observed_at": "2026-02-22T09:00:00+00:00",
                        }
                    ],
                    "_meta": {"updated_at": updated_at},
                },
            )
        ),  # type: ignore[arg-type]
        user_id=user_id,
        thread=thread,
        recent_events=recent_events,
        mode="coach_chat",
        tool_registry=registry,  # type: ignore[arg-type]
        user_message="Hi",
    )

    assert context["long_term_memory"]["memory_updated_at"] == updated_at
    assert context["long_term_memory"]["memory_age_days"] == 0
    assert context["long_term_memory"]["transient_state_notes"][0]["topic"] == "illness"
    assert context["long_term_memory"]["transient_state_notes"][0]["status"] == "recovering"
