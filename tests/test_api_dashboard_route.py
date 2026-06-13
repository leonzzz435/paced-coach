import uuid

from fastapi.testclient import TestClient

import api.deps as deps_module
from api.main import create_app
from api.routers import dashboard as dashboard_router


def test_dashboard_state_route_returns_service_payload(monkeypatch):
    user_id = uuid.uuid4()
    expected_user_id = user_id
    expected_payload: dict[str, object] = {
        "athlete_time": {
            "timezone": "America/Los_Angeles",
            "timezone_source": "profile",
            "today_local_date": "2026-03-05",
            "now_local_iso": "2026-03-05T06:00:00-08:00",
        },
        "analysis": None,
        "status_surface": {
            "kpis": [],
            "source": "none",
            "label": None,
            "updated_at": None,
            "target_date": None,
        },
        "coach_surface": {
            "source": "none",
            "scope": "none",
            "primary_label": None,
            "primary_text": None,
            "secondary_text": None,
            "updated_at": None,
        },
        "season": None,
        "weekly": None,
        "today_mission": {"warnings": ["Add at least one competition."], "day_override": None},
        "daily_sync": {
            "visible": True,
            "status": "idle",
            "run_id": None,
            "verdict_preview": None,
            "sources_used": [],
            "proposal_id": None,
            "thread_id": None,
            "error_message": None,
        },
        "weekly_recap": {
            "visible": False,
            "allowed": False,
            "status": "hidden",
            "thread_id": None,
            "proposal_id": None,
            "follow_up_question": None,
            "summary_preview": None,
            "pending_action": "none",
        },
        "pending_proposal_banner": None,
    }

    async def fake_get_db():
        yield object()

    async def fake_get_current_user():
        return user_id

    async def fake_build_dashboard_state(db, *, user_id):
        assert db is not None
        assert user_id == expected_user_id
        return expected_payload

    monkeypatch.setattr(dashboard_router, "build_dashboard_state", fake_build_dashboard_state)

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.get("/api/dashboard/state", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json() == expected_payload
