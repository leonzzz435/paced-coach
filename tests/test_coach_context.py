import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from api.models.coach_event import CoachEvent
from api.models.coach_thread import CoachThread
from api.services.coach_context import build_turn_context
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
        self.training_snapshot_called = False
        self.expert_summary_called = False
        self.current_weekly_plan_called = False

    async def get_training_snapshot(self):
        self.training_snapshot_called = True
        return {
            "as_of_date": "2026-02-27",
            "sessions_7d": 5,
            "competition_proximity_days": 12,
            "load_trend": "rising",
        }

    async def get_expert_analysis_summary(self):
        self.expert_summary_called = True
        return {
            "run_date": "2026-02-20",
            "age_days": 7,
            "staleness": "moderate",
            "domains": {},
        }

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

    def get_observability_snapshot(self):
        return {
            "tool_usage": {},
            "cache_keys": [],
            "provider": {"training_providers": {"strava": {"kind": None, "available": False}}},
            "evidence_profile": {
                "connected_mode": "strava_only",
                "dimensions": {
                    "activity_history": {"availability": "strong", "confidence": "high"},
                    "recovery_biometrics": {"availability": "none", "confidence": "low"},
                },
                "claims_policy": {
                    "can_make_activity_completeness_claims": True,
                    "can_make_readiness_claims": False,
                },
            },
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

    assert registry.training_snapshot_called is False
    assert registry.expert_summary_called is False
    assert registry.current_weekly_plan_called is True
    assert context["mode"] == "coach_chat"
    assert isinstance(context["now_utc"], str)
    assert context["ui_context"] == {"source": "today_mission", "day": {"day_id": "2026-02-27"}}
    assert context["training_snapshot"] is None
    assert context["expert_analysis_summary"] is None
    assert context["evidence_profile"]["connected_mode"] == "strava_only"
    assert context["evidence_profile"]["claims_policy"]["can_make_readiness_claims"] is False
    assert context["current_weekly_plan_identity"]["plan_id"] == "plan-1"
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
    assert context["tool_observability"]["provider"]["training_providers"]["strava"]["available"] is False
    assert len(context["recent_tool_results"]) == 1
    assert len(context["recent_events"]) == 3


@pytest.mark.asyncio
async def test_build_turn_context_proactive_mode_prefetches_snapshot_and_expert_summary():
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

    assert registry.training_snapshot_called is True
    assert registry.expert_summary_called is True
    assert registry.current_weekly_plan_called is True
    assert context["mode"] == "proactive_eval"
    assert context["training_snapshot"]["sessions_7d"] == 5
    assert context["evidence_profile"]["connected_mode"] == "strava_only"
    assert context["expert_analysis_summary"]["staleness"] == "moderate"
    assert context["current_weekly_plan_identity"]["weeks"][0]["days"][0]["day_label"] == "Fri — Strength-Endurance"
    assert context["derived_context"]["competition_context"]["competition_proximity_days"] == 12
    assert context["long_term_memory"]["athlete_model"] == {"goal_state": "A-race"}


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
