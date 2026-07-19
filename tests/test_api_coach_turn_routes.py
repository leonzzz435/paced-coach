import asyncio
import json
import os
import uuid
from datetime import datetime

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from fastapi import HTTPException
from fastapi.testclient import TestClient

import api.deps as deps_module
from api.main import create_app
from api.routers import coach as coach_router


def _build_turn_payload() -> dict:
    return {
        "thread": {
            "id": str(uuid.uuid4()),
            "status": "active",
            "title": "Marathon taper week question",
            "latest_seq": 4,
            "updated_at": datetime.now().isoformat(),
        },
        "events_appended": [{"seq": 4, "event_type": "coach_message"}],
        "projection": {
            "messages": [],
            "quota": {"is_limited": False, "remaining": None, "limit": None, "used": 0, "week_anchor_utc": ""},
            "has_pending_proposal": False,
            "pending_proposal_ids": [],
            "next_after_seq": 4,
        },
        "turn": {"kind": "message"},
    }


def _parse_sse_events(raw_payload: str) -> list[tuple[str, dict | None]]:
    events: list[tuple[str, dict | None]] = []
    normalized = raw_payload.replace("\r\n", "\n")
    for frame in normalized.split("\n\n"):
        if not frame.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in frame.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
                continue
            if line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].lstrip())
        data = json.loads("\n".join(data_lines)) if data_lines else None
        events.append((event_name, data))
    return events


class _DummyDB:
    def __init__(self):
        self.info: dict[str, object] = {}
        self.commit_calls = 0
        self.rollback_calls = 0

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1


def test_coach_turn_route_available(monkeypatch):
    user_id = uuid.uuid4()
    captured_kwargs: dict[str, object] = {}

    async def fake_get_db():
        yield object()

    async def fake_get_current_user():
        return user_id

    async def fake_post_coach_turn(*_args, **_kwargs):
        captured_kwargs.update(_kwargs)
        return _build_turn_payload()

    monkeypatch.setattr(coach_router, "post_coach_turn", fake_post_coach_turn)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(
        "/api/coach/turn",
        json={
            "action": "text",
            "message": "How was my week?",
            "idempotency_key": "test-key",
            "ui_context": {
                "source": "today_mission",
                "day_id": "2026-03-27",
                "week_id": "wk-2026-03-27",
                "date": "2026-03-27",
                "day_label": "Fri - Strength-Endurance",
                "workout_title": "Strength-Endurance",
            },
        },
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "thread" in payload
    assert payload["events_appended"][0]["event_type"] == "coach_message"
    assert captured_kwargs["ui_context"] == {
        "source": "today_mission",
        "day_id": "2026-03-27",
        "week_id": "wk-2026-03-27",
        "date": "2026-03-27",
        "day_label": "Fri - Strength-Endurance",
        "workout_title": "Strength-Endurance",
    }


def test_coach_turn_route_streams_sse_success(monkeypatch):
    user_id = uuid.uuid4()
    db = _DummyDB()

    async def fake_get_db():
        yield db

    async def fake_get_current_user():
        return user_id

    async def fake_post_coach_turn(*_args, **_kwargs):
        status_emitter = _kwargs.get("status_emitter")
        if status_emitter is not None:
            await status_emitter({"step": "preparing", "message": "Preparing coaching context..."})
        return _build_turn_payload()

    monkeypatch.setattr(coach_router, "post_coach_turn", fake_post_coach_turn)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(
        "/api/coach/turn",
        json={"action": "text", "message": "How was my week?", "idempotency_key": "stream-ok-key"},
        headers={"Authorization": "Bearer test", "Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]

    assert "status" in event_names
    assert "result" in event_names
    assert event_names[-1] == "done"
    result_payload = next(payload for event_name, payload in events if event_name == "result")
    assert isinstance(result_payload, dict)
    assert result_payload["events_appended"][0]["event_type"] == "coach_message"
    assert db.commit_calls == 1
    assert db.rollback_calls == 0
    assert db.info.get(deps_module.DB_SKIP_AUTO_COMMIT_FLAG) is True


def test_coach_turn_route_streams_sse_http_exception(monkeypatch):
    user_id = uuid.uuid4()
    db = _DummyDB()

    async def fake_get_db():
        yield db

    async def fake_get_current_user():
        return user_id

    async def fake_post_coach_turn(*_args, **_kwargs):
        raise HTTPException(status_code=409, detail="Idempotent request already in progress")

    monkeypatch.setattr(coach_router, "post_coach_turn", fake_post_coach_turn)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(
        "/api/coach/turn",
        json={"action": "text", "message": "How was my week?", "idempotency_key": "stream-http-error-key"},
        headers={"Authorization": "Bearer test", "Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "error" in event_names
    assert event_names[-1] == "done"
    error_payload = next(payload for event_name, payload in events if event_name == "error")
    assert isinstance(error_payload, dict)
    assert error_payload["status_code"] == 409
    assert error_payload["detail"] == "Idempotent request already in progress"
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
    assert db.info.get(deps_module.DB_SKIP_AUTO_COMMIT_FLAG) is True


def test_coach_turn_route_streams_provider_unavailable_error_deterministically(monkeypatch):
    user_id = uuid.uuid4()
    db = _DummyDB()

    async def fake_get_db():
        yield db

    async def fake_get_current_user():
        return user_id

    async def fake_post_coach_turn(*_args, **_kwargs):
        raise HTTPException(
            status_code=503,
            detail="Connected provider data is currently unavailable.",
        )

    monkeypatch.setattr(coach_router, "post_coach_turn", fake_post_coach_turn)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(
        "/api/coach/turn",
        json={"action": "text", "message": "How was my week?", "idempotency_key": "stream-provider-unavailable-key"},
        headers={"Authorization": "Bearer test", "Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "error" in event_names
    assert event_names[-1] == "done"
    error_payload = next(payload for event_name, payload in events if event_name == "error")
    assert isinstance(error_payload, dict)
    assert error_payload["status_code"] == 503
    assert error_payload["detail"] == "Connected provider data is currently unavailable."
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
    assert db.info.get(deps_module.DB_SKIP_AUTO_COMMIT_FLAG) is True


def test_coach_turn_route_streams_sse_generic_exception(monkeypatch):
    user_id = uuid.uuid4()
    db = _DummyDB()

    async def fake_get_db():
        yield db

    async def fake_get_current_user():
        return user_id

    async def fake_post_coach_turn(*_args, **_kwargs):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(coach_router, "post_coach_turn", fake_post_coach_turn)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(
        "/api/coach/turn",
        json={"action": "text", "message": "How was my week?", "idempotency_key": "stream-generic-error-key"},
        headers={"Authorization": "Bearer test", "Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "error" in event_names
    assert event_names[-1] == "done"
    error_payload = next(payload for event_name, payload in events if event_name == "error")
    assert isinstance(error_payload, dict)
    assert error_payload["status_code"] == 500
    assert error_payload["detail"] == "Coach turn failed"
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
    assert db.info.get(deps_module.DB_SKIP_AUTO_COMMIT_FLAG) is True


def test_coach_turn_route_streams_sse_timeout(monkeypatch):
    user_id = uuid.uuid4()
    db = _DummyDB()

    async def fake_get_db():
        yield db

    async def fake_get_current_user():
        return user_id

    async def fake_post_coach_turn(*_args, **_kwargs):
        await asyncio.sleep(0.5)
        return _build_turn_payload()

    monkeypatch.setattr(coach_router, "post_coach_turn", fake_post_coach_turn)
    monkeypatch.setattr(coach_router, "_COACH_TURN_STREAM_TIMEOUT_SECONDS", 0.01)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(
        "/api/coach/turn",
        json={"action": "text", "message": "How was my week?", "idempotency_key": "stream-timeout-key"},
        headers={"Authorization": "Bearer test", "Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]
    assert "error" in event_names
    assert event_names[-1] == "done"
    error_payload = next(payload for event_name, payload in events if event_name == "error")
    assert isinstance(error_payload, dict)
    assert error_payload["status_code"] == 504
    assert error_payload["detail"] == "Coach turn timed out while generating a response"
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
    assert db.info.get(deps_module.DB_SKIP_AUTO_COMMIT_FLAG) is True


def test_coach_turn_non_text_action_bypasses_sse(monkeypatch):
    user_id = uuid.uuid4()

    async def fake_get_db():
        yield object()

    async def fake_get_current_user():
        return user_id

    async def fake_post_coach_turn(*_args, **_kwargs):
        return {"status": "accepted", "changed": True}

    monkeypatch.setattr(coach_router, "post_coach_turn", fake_post_coach_turn)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(
        "/api/coach/turn",
        json={
            "action": "proposal_accept",
            "proposal_id": str(uuid.uuid4()),
            "idempotency_key": "proposal-accept-key",
        },
        headers={"Authorization": "Bearer test", "Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    assert response.json()["status"] == "accepted"


def test_coach_turn_rejects_removed_recap_action():
    user_id = uuid.uuid4()

    async def fake_get_db():
        yield object()

    async def fake_get_current_user():
        return user_id

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(
        "/api/coach/turn",
        json={"action": "recap", "idempotency_key": "removed-recap-action"},
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 422


def test_legacy_coach_action_endpoints_are_removed():
    app = create_app()
    client = TestClient(app)

    for path in ("/api/coach/chat", "/api/coach/accept", "/api/coach/reject"):
        response = client.post(path, headers={"Authorization": "Bearer test"}, json={})
        assert response.status_code == 404


def test_coach_thread_route_available(monkeypatch):
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()

    async def fake_get_db():
        yield object()

    async def fake_get_current_user():
        return user_id

    async def fake_get_thread(*_args, **_kwargs):
        return {
            "thread": {
                "id": str(thread_id),
                "status": "active",
                "title": "Marathon taper week question",
                "latest_seq": 3,
                "updated_at": datetime.now().isoformat(),
            },
            "messages": [],
            "quota": {"is_limited": False, "remaining": None, "limit": None, "used": 0, "week_anchor_utc": ""},
            "has_pending_proposal": False,
            "pending_proposal_ids": [],
            "next_after_seq": 3,
            "week_anchor_utc": datetime.now().isoformat(),
        }

    monkeypatch.setattr(coach_router, "get_coach_thread_v2", fake_get_thread)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.get("/api/coach/thread", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["thread"]["id"] == str(thread_id)
    assert payload["messages"] == []


def test_coach_threads_route_available(monkeypatch):
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()

    async def fake_get_db():
        yield object()

    async def fake_get_current_user():
        return user_id

    async def fake_list_threads(*_args, **_kwargs):
        return {
            "items": [
                {
                    "id": str(thread_id),
                    "status": "active",
                    "title": "Marathon taper week question",
                    "latest_seq": 2,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            ],
            "limit": 20,
            "offset": 0,
            "has_more": False,
            "next_offset": None,
        }

    monkeypatch.setattr(coach_router, "list_coach_threads_v2", fake_list_threads)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.get("/api/coach/threads", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["id"] == str(thread_id)


def test_archive_thread_route_available(monkeypatch):
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()

    async def fake_get_db():
        yield object()

    async def fake_get_current_user():
        return user_id

    async def fake_archive(*_args, **_kwargs):
        return {
            "thread": {
                "id": str(thread_id),
                "status": "archived",
                "title": "Marathon taper week question",
                "latest_seq": 3,
                "updated_at": datetime.now().isoformat(),
            }
        }

    monkeypatch.setattr(coach_router, "archive_coach_thread_v2", fake_archive)
    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(f"/api/coach/thread/{thread_id}/archive", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["thread"]["status"] == "archived"
