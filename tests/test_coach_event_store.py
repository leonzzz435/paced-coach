import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from api.models.coach_event import CoachEvent
from api.models.coach_thread import CoachThread
from api.models.credentials import WhoopCredentials
from api.services import coach_event_store
from api.services.coach_event_store import (
    EVENT_PROPOSAL_CREATED,
    EVENT_RECAP_NARRATIVE,
    EVENT_RECAP_RESPONSE,
    EVENT_USER_MESSAGE,
    THREAD_STATUS_ACTIVE,
    build_thread_projection,
    get_or_create_coach_thread,
    serialize_thread_event,
)
from api.services.full_run_policy import WeeklyRecapAvailability
from api.services.integration_status import build_integrations_status


async def _healthy_integrations_status(*_args, **_kwargs):
    return build_integrations_status(
        settings=cast(
            "Any",
            SimpleNamespace(
                whoop_oauth_client_id="client-id",
                whoop_oauth_client_secret="client-secret",
            ),
        ),
        crypto_service=None,
        whoop=WhoopCredentials(
            user_id=uuid.uuid4(),
            encrypted_access_token=b"access-token",
            encrypted_refresh_token=b"refresh-token",
            expires_at=datetime(2026, 3, 8, tzinfo=UTC),
            scope="offline read:recovery",
            whoop_user_id=42,
        ),
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )


def test_serialize_thread_event_uses_normalized_proposal_status():
    proposal_id = str(uuid.uuid4())
    base_plan = {"type": "weekly_plan", "plan_id": "before"}
    preview_plan = {"type": "weekly_plan", "plan_id": "after"}
    event = CoachEvent(
        id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        seq=11,
        event_type=EVENT_PROPOSAL_CREATED,
        actor="coach",
        payload={
            "proposal_id": proposal_id,
            "origin": "coach_turn",
            "status": "pending",
            "assistant_message": "Let's adjust one session.",
            "ops": [],
            "base_weekly_plan": base_plan,
            "preview_weekly_plan": preview_plan,
        },
        created_at=datetime.now(UTC),
    )
    serialized = serialize_thread_event(event, proposal_status_by_id={proposal_id: "accepted"})
    assert serialized is not None
    assert serialized["status"] == "accepted"
    assert serialized["base_weekly_plan"] == base_plan
    assert serialized["preview_weekly_plan"] == preview_plan


def test_serialize_thread_event_hides_internal_recap_response_events():
    event = CoachEvent(
        id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        seq=12,
        event_type=EVENT_RECAP_RESPONSE,
        actor="user",
        payload={"recap_run_id": str(uuid.uuid4()), "response": "Legs felt good."},
        created_at=datetime.now(UTC),
    )

    assert serialize_thread_event(event, proposal_status_by_id={}) is None


class _FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)


class _FakeResult:
    def __init__(self, *, one_or_none=None, rows=None, scalars=None, scalar_one_or_none=None):
        self._one_or_none = one_or_none
        self._rows = rows or []
        self._scalars = scalars or []
        self._scalar_one_or_none = scalar_one_or_none

    def one_or_none(self):
        return self._one_or_none

    def all(self):
        return list(self._rows)

    def scalars(self):
        return _FakeScalarResult(self._scalars)

    def scalar_one_or_none(self):
        return self._scalar_one_or_none


class _FakeDb:
    def __init__(self, responses):
        self._responses = iter(responses)

    async def execute(self, _statement):
        return next(self._responses)


class _ProjectionThread:
    def __init__(self, thread_id):
        self.id = thread_id

    @property
    def latest_seq(self):
        raise AssertionError("latest_seq should come from explicit thread snapshot query")

    @property
    def updated_at(self):
        raise AssertionError("updated_at should come from explicit thread snapshot query")


@pytest.mark.asyncio
async def test_build_thread_projection_uses_explicit_thread_snapshot(monkeypatch):
    thread_id = uuid.uuid4()
    user_id = uuid.uuid4()
    snapshot_time = datetime.now(UTC)

    async def _fake_get_thread_events(*_args, **_kwargs):
        return []

    async def _fake_get_quota(*_args, **_kwargs):
        return {"is_limited": False}

    async def _fake_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=True,
            reason="eligible",
            last_full_run_at=None,
            current_anchor_utc=None,
            timezone="UTC",
            window_start=None,
            window_end=None,
            next_allowed_at=None,
            existing_run_id=None,
        )

    monkeypatch.setattr(coach_event_store, "get_thread_events", _fake_get_thread_events)
    monkeypatch.setattr(coach_event_store, "get_coach_weekly_quota", _fake_get_quota)
    monkeypatch.setattr(coach_event_store, "evaluate_weekly_recap_availability", _fake_recap_availability)
    monkeypatch.setattr(coach_event_store, "load_integrations_status", _healthy_integrations_status)
    async def _fake_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    monkeypatch.setattr(coach_event_store, "get_local_usage_context", _fake_usage_context)

    fake_db = _FakeDb(
        [
            _FakeResult(
                one_or_none=SimpleNamespace(
                    id=thread_id,
                    status="active",
                    title="Marathon taper week question",
                    latest_seq=7,
                    updated_at=snapshot_time,
                ),
            ),
            _FakeResult(rows=[]),
            _FakeResult(scalars=[]),
        ]
    )

    projection = await build_thread_projection(
        fake_db,  # type: ignore[arg-type]
        user_id=user_id,
        thread=cast("Any", _ProjectionThread(thread_id)),
    )

    assert projection["thread"]["id"] == str(thread_id)
    assert projection["thread"]["status"] == "active"
    assert projection["thread"]["title"] == "Marathon taper week question"
    assert projection["thread"]["latest_seq"] == 7
    assert projection["thread"]["updated_at"] == snapshot_time.isoformat()


@pytest.mark.asyncio
async def test_build_thread_projection_hydrates_answered_recap_follow_up(monkeypatch):
    thread_id = uuid.uuid4()
    user_id = uuid.uuid4()
    recap_run_id = uuid.uuid4()
    snapshot_time = datetime.now(UTC)
    response_text = "The climbs felt controlled and smooth."

    async def _fake_get_thread_events(*_args, **_kwargs):
        return [
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
                created_at=snapshot_time,
            ),
            CoachEvent(
                id=uuid.uuid4(),
                thread_id=thread_id,
                seq=2,
                event_type=EVENT_USER_MESSAGE,
                actor="user",
                payload={"text": response_text},
                created_at=snapshot_time,
            ),
            CoachEvent(
                id=uuid.uuid4(),
                thread_id=thread_id,
                seq=3,
                event_type=EVENT_RECAP_RESPONSE,
                actor="user",
                payload={"recap_run_id": str(recap_run_id), "response": response_text},
                created_at=snapshot_time,
            ),
        ]

    async def _fake_get_quota(*_args, **_kwargs):
        return {"is_limited": False}

    async def _fake_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=True,
            reason="eligible",
            last_full_run_at=None,
            current_anchor_utc=None,
            timezone="UTC",
            window_start=None,
            window_end=None,
            next_allowed_at=None,
            existing_run_id=None,
        )

    async def _fake_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    monkeypatch.setattr(coach_event_store, "get_thread_events", _fake_get_thread_events)
    monkeypatch.setattr(coach_event_store, "get_coach_weekly_quota", _fake_get_quota)
    monkeypatch.setattr(coach_event_store, "evaluate_weekly_recap_availability", _fake_recap_availability)
    monkeypatch.setattr(coach_event_store, "load_integrations_status", _healthy_integrations_status)
    monkeypatch.setattr(coach_event_store, "get_local_usage_context", _fake_usage_context)

    fake_db = _FakeDb(
        [
            _FakeResult(
                one_or_none=SimpleNamespace(
                    id=thread_id,
                    status="active",
                    title="Weekly Recap",
                    latest_seq=3,
                    updated_at=snapshot_time,
                ),
            ),
            _FakeResult(rows=[]),
            _FakeResult(rows=[(recap_run_id, "Did the climbs feel smooth?", response_text)]),
            _FakeResult(scalars=[]),
        ]
    )

    projection = await build_thread_projection(
        fake_db,  # type: ignore[arg-type]
        user_id=user_id,
        thread=cast("Any", _ProjectionThread(thread_id)),
    )

    assert len(projection["messages"]) == 2
    assert projection["messages"][0]["kind"] == "recap"
    assert projection["messages"][0]["recap"]["athlete_response"] == response_text
    assert projection["messages"][1]["kind"] == "text"
    assert projection["messages"][1]["text"] == response_text


class _CreateThreadDb:
    def __init__(self, existing_thread: CoachThread | None = None):
        self._existing_thread = existing_thread
        self.added: list[object] = []
        self.flushed = False

    async def execute(self, _statement):
        return _FakeResult(scalar_one_or_none=self._existing_thread)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_get_or_create_coach_thread_creates_new_when_thread_id_missing():
    user_id = uuid.uuid4()
    fake_db = _CreateThreadDb()

    thread = await get_or_create_coach_thread(cast("Any", fake_db), user_id=user_id)

    assert thread.user_id == user_id
    assert thread.status == THREAD_STATUS_ACTIVE
    assert fake_db.flushed is True


@pytest.mark.asyncio
async def test_get_or_create_coach_thread_loads_existing_when_thread_id_provided():
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    existing = CoachThread(id=thread_id, user_id=user_id, latest_seq=2, status=THREAD_STATUS_ACTIVE)
    fake_db = _CreateThreadDb(existing_thread=existing)

    loaded = await get_or_create_coach_thread(
        cast("Any", fake_db),
        user_id=user_id,
        thread_id=thread_id,
    )

    assert loaded.id == thread_id
    assert fake_db.flushed is False
