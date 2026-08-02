import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from api.services import recap
from api.services.full_run_policy import WeeklyRecapAvailability


class _RefreshTrackingDb:
    def __init__(self):
        self.refresh_calls = 0
        self.flush_calls = 0
        self.added: list[object] = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_calls += 1

    async def refresh(self, _obj):
        self.refresh_calls += 1


class _FakeRecapWeeklyPlan:
    def model_dump(self, mode="json"):
        assert mode == "json"
        return {"type": "weekly_plan", "plan_id": "demo"}


class _FakeRecapBlock:
    def model_dump(self, mode="json"):
        assert mode == "json"
        return {"key": "block-1", "content_html": "<p>Strong week</p>"}


class _RecapSerializerSpy:
    def __init__(self, db: _RefreshTrackingDb):
        self.db = db
        self.calls = 0

    def __call__(self, run):
        self.calls += 1
        required_refreshes = 1 if self.calls == 1 else 2
        assert self.db.refresh_calls >= required_refreshes
        return {
            "run_id": str(run.id),
            "follow_up_question": run.follow_up_question,
            "proposal_id": run.proposal_id,
        }


async def _fake_recap_usage_context(*_args, **_kwargs):
    return SimpleNamespace(
        has_access=True,
        effective_plan=SimpleNamespace(weekly_recap_included=True),
    )


async def _fake_completed_recap_narrative(*_args, **_kwargs):
    narrative = SimpleNamespace(
        this_week_blocks=[_FakeRecapBlock()],
        looking_ahead_blocks=[_FakeRecapBlock()],
        optional_proposal_ops=[],
        follow_up_question="How did the long run feel after the final climb?",
    )
    return narrative, {"tool_observability": []}, None, SimpleNamespace()


async def _fake_no_recap_run_for_anchor(*_args, **_kwargs):
    return None


async def _fake_no_latest_answered_recap_follow_up(*_args, **_kwargs):
    return None


async def _fake_no_optional_recap_proposal(*_args, **_kwargs):
    return None, None, False


async def _fake_append_recap_events(*_args, **_kwargs):
    return [SimpleNamespace(id=uuid.uuid4())]


def _eligible_recap_availability(anchor: datetime, window_start: datetime, window_end: datetime):
    async def _fake_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=True,
            reason="eligible",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=anchor,
            timezone="UTC",
            window_start=window_start,
            window_end=window_end,
            next_allowed_at=None,
            existing_run_id=None,
        )

    return _fake_availability


def _patch_completed_recap_dependencies(monkeypatch, *, db, recap_run, anchor, window_start, window_end):
    async def _fake_prepare_pending_recap_run(*_args, **_kwargs):
        return recap_run, False

    async def _fake_get_active_weekly_plan_for_recap(*_args, **_kwargs):
        return SimpleNamespace(), _FakeRecapWeeklyPlan()

    async def _fake_get_quota(*_args, **_kwargs):
        return {"week_anchor_utc": anchor.isoformat(), "remaining": 5}

    serializer = _RecapSerializerSpy(db)
    monkeypatch.setattr(recap, "get_local_usage_context", _fake_recap_usage_context)
    monkeypatch.setattr(recap, "evaluate_weekly_recap_availability", _eligible_recap_availability(anchor, window_start, window_end))
    monkeypatch.setattr(recap, "_get_recap_run_for_anchor", _fake_no_recap_run_for_anchor)
    monkeypatch.setattr(recap, "_prepare_pending_recap_run", _fake_prepare_pending_recap_run)
    monkeypatch.setattr(recap, "_get_active_weekly_plan_for_recap", _fake_get_active_weekly_plan_for_recap)
    monkeypatch.setattr(recap, "get_latest_answered_recap_follow_up", _fake_no_latest_answered_recap_follow_up)
    monkeypatch.setattr(recap, "_generate_recap_narrative", _fake_completed_recap_narrative)
    monkeypatch.setattr(recap, "get_coach_weekly_quota", _fake_get_quota)
    monkeypatch.setattr(recap, "build_ai_run_cost_record", lambda **_kwargs: object())
    monkeypatch.setattr(recap, "_create_optional_recap_proposal", _fake_no_optional_recap_proposal)
    monkeypatch.setattr(recap, "append_coach_events", _fake_append_recap_events)
    monkeypatch.setattr(recap, "serialize_recap_run", serializer)
    return serializer


@pytest.mark.asyncio
async def test_execute_recap_turn_blocks_when_window_not_open(monkeypatch):
    next_allowed_at = datetime(2026, 3, 7, 20, 0, tzinfo=UTC)

    async def _fake_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=datetime(2026, 2, 28, 20, 0, tzinfo=UTC),
            current_anchor_utc=None,
            timezone="UTC",
            window_start=None,
            window_end=None,
            next_allowed_at=next_allowed_at,
            existing_run_id=None,
        )

    monkeypatch.setattr(recap, "evaluate_weekly_recap_availability", _fake_availability)
    async def _fake_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    monkeypatch.setattr(recap, "get_local_usage_context", _fake_usage_context)

    fake_thread = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await recap.execute_recap_turn(
            object(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
            thread=fake_thread,
        )

    assert exc.value.status_code == 409
    assert "every 7 days after full run creation" in str(exc.value.detail)
    assert next_allowed_at.isoformat() in str(exc.value.detail)


@pytest.mark.asyncio
async def test_execute_recap_turn_skips_usage_gate_when_dev_bypass_enabled(monkeypatch):
    next_allowed_at = datetime(2026, 3, 7, 20, 0, tzinfo=UTC)
    monkeypatch.setenv("WEB_APP_URL", "http://localhost:3000")

    async def _fake_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=datetime(2026, 2, 28, 20, 0, tzinfo=UTC),
            current_anchor_utc=None,
            timezone="UTC",
            window_start=None,
            window_end=None,
            next_allowed_at=next_allowed_at,
            existing_run_id=None,
        )

    monkeypatch.setattr(recap, "evaluate_weekly_recap_availability", _fake_availability)

    async def _fake_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=False,
            effective_plan=None,
        )

    monkeypatch.setattr(recap, "get_local_usage_context", _fake_usage_context)
    monkeypatch.setattr(
        "api.services.local_usage.limits.get_settings",
        lambda: SimpleNamespace(local_usage_dev_bypass=True, web_app_url="http://localhost:3000"),
    )

    fake_thread = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await recap.execute_recap_turn(
            object(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
            thread=fake_thread,
        )

    assert exc.value.status_code == 409
    assert "every 7 days after full run creation" in str(exc.value.detail)
    assert next_allowed_at.isoformat() in str(exc.value.detail)


@pytest.mark.asyncio
async def test_execute_recap_turn_refreshes_run_before_serializing_completed_recap(monkeypatch):
    anchor = datetime(2026, 3, 9, 0, 0, tzinfo=UTC)
    window_start = datetime(2026, 3, 9, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 3, 16, 0, 0, tzinfo=UTC)
    user_id = uuid.uuid4()
    fake_db = _RefreshTrackingDb()
    recap_run = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        week_anchor_utc=anchor,
        trigger_source="manual",
        status="pending",
        error_message=None,
        follow_up_question=None,
        athlete_response=None,
        proposal_id=None,
        recap_event_id=None,
        recap_payload=None,
        context_snapshot=None,
        created_at=window_start,
        updated_at=window_start,
    )
    fake_thread = SimpleNamespace(id=uuid.uuid4(), title="Weekly recap")
    serializer = _patch_completed_recap_dependencies(
        monkeypatch,
        db=fake_db,
        recap_run=recap_run,
        anchor=anchor,
        window_start=window_start,
        window_end=window_end,
    )

    turn_payload, created_events = await recap.execute_recap_turn(
        fake_db,  # type: ignore[arg-type]
        user_id=user_id,
        thread=fake_thread,  # type: ignore[arg-type]
    )

    assert turn_payload["kind"] == "recap"
    assert turn_payload["recap"]["follow_up_question"] == "How did the long run feel after the final climb?"
    assert fake_db.refresh_calls == 2
    assert serializer.calls == 2
    assert len(created_events) == 2


@pytest.mark.asyncio
async def test_execute_recap_turn_continues_when_training_provider_is_disconnected(monkeypatch):
    async def _fake_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    async def _fake_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=True,
            reason="eligible",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=datetime(2026, 3, 9, 0, 0, tzinfo=UTC),
            timezone="UTC",
            window_start=datetime(2026, 3, 9, 0, 0, tzinfo=UTC),
            window_end=datetime(2026, 3, 16, 0, 0, tzinfo=UTC),
            next_allowed_at=None,
            existing_run_id=None,
        )

    async def _provider_free_path_reached(*_args, **_kwargs):
        raise RuntimeError("provider-free recap path reached")

    monkeypatch.setattr(recap, "get_local_usage_context", _fake_usage_context)
    monkeypatch.setattr(recap, "evaluate_weekly_recap_availability", _fake_availability)
    monkeypatch.setattr(recap, "_get_recap_run_for_anchor", _provider_free_path_reached)

    with pytest.raises(RuntimeError, match="provider-free recap path reached"):
        await recap.execute_recap_turn(
            object(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
            thread=MagicMock(),
        )



@pytest.mark.asyncio
async def test_get_latest_weekly_recap_report_returns_report_metadata(monkeypatch):
    user_id = uuid.uuid4()
    thread_id = str(uuid.uuid4())

    class _FakeScalarResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _FakeDb:
        def __init__(self, run):
            self._run = run
            self.refresh_calls = 0

        async def execute(self, statement, *_args, **_kwargs):
            sql = str(statement)
            assert "FROM weekly_recap_runs" in sql
            return _FakeScalarResult(self._run)

        async def refresh(self, _obj):
            self.refresh_calls += 1

    fake_run = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        week_anchor_utc=datetime(2026, 3, 15, 23, 0, tzinfo=UTC),
        trigger_source="manual",
        status="completed",
        proposal_id=None,
        created_at=datetime(2026, 3, 15, 18, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 15, 18, 1, tzinfo=UTC),
        follow_up_question=None,
        athlete_response=None,
        recap_payload={
            "narrative": {
                "this_week_blocks": [
                    {
                        "title": "High compliance, but load rose faster than ideal",
                        "content_html": "<p>Detailed recap copy.</p>",
                    }
                ],
                "looking_ahead_blocks": [],
            },
            "base_weekly_plan": None,
            "preview_weekly_plan": None,
            "ops": [],
        },
    )

    async def _fake_get_recap_thread_id(*_args, **_kwargs):
        return thread_id

    async def _fake_get_recap_pending_action(*_args, **_kwargs):
        return "none"

    monkeypatch.setattr(recap, "get_recap_thread_id", _fake_get_recap_thread_id)
    monkeypatch.setattr(recap, "get_recap_pending_action", _fake_get_recap_pending_action)

    fake_db = _FakeDb(fake_run)
    payload = await recap.get_latest_weekly_recap_report(fake_db, user_id=user_id)  # type: ignore[arg-type]
    recap_payload = payload["recap"]

    assert payload["thread_id"] == thread_id
    assert payload["pending_action"] == "none"
    assert payload["summary_preview"] == "High compliance, but load rose faster than ideal"
    assert isinstance(recap_payload, dict)
    assert recap_payload["run_id"] == str(fake_run.id)
    assert fake_db.refresh_calls == 1
