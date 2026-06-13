import uuid

from fastapi.testclient import TestClient

import api.deps as deps_module
from api.main import create_app
from api.routers import weekly_recap as weekly_recap_router


def test_weekly_recap_latest_route_returns_service_payload(monkeypatch):
    user_id = uuid.uuid4()
    expected_user_id = user_id
    expected_payload: dict[str, object] = {
        "recap": {
            "run_id": str(uuid.uuid4()),
            "user_id": str(user_id),
            "week_anchor_utc": "2026-03-15T23:00:00+00:00",
            "status": "completed",
            "trigger_source": "manual",
            "proposal_id": None,
            "created_at": "2026-03-15T18:00:00+00:00",
            "updated_at": "2026-03-15T18:01:00+00:00",
            "narrative": {
                "this_week_blocks": [],
                "looking_ahead_blocks": [],
            },
            "base_weekly_plan": None,
            "preview_weekly_plan": None,
            "ops": [],
            "follow_up_question": None,
            "athlete_response": None,
        },
        "thread_id": str(uuid.uuid4()),
        "summary_preview": "High compliance, but load rose faster than ideal.",
        "pending_action": "none",
    }

    async def fake_get_db():
        yield object()

    async def fake_get_current_user():
        return user_id

    async def fake_get_latest_weekly_recap_report(db, *, user_id):
        assert db is not None
        assert user_id == expected_user_id
        return expected_payload

    monkeypatch.setattr(
        weekly_recap_router,
        "get_latest_weekly_recap_report",
        fake_get_latest_weekly_recap_report,
    )

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.get("/api/weekly-recap/latest", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json() == expected_payload
