import os
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from fastapi.testclient import TestClient

import api.deps as deps_module
from api.main import create_app


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeAsyncSession:
    def __init__(self, row=None):
        self.row = row
        self.add_calls = 0

    async def execute(self, *_args, **_kwargs):
        return _FakeScalarResult(self.row)

    def add(self, _obj):
        self.add_calls += 1

    async def flush(self):
        return None

    async def refresh(self, _obj):
        return None


def test_get_athlete_profile_ignores_legacy_storage_fields():
    user_id = uuid.uuid4()
    fake_session = _FakeAsyncSession(
        row=SimpleNamespace(
            user_id=user_id,
            updated_at=datetime(2026, 3, 7, 9, 30, tzinfo=UTC),
            profile={
                "physiology": {
                    "ftp": 250,
                    "zone_model": "mixed",
                    "zones_notes": "define zones based on your best knowledge",
                },
                "goals": {
                    "primary_goal": "Build toward a strong half marathon",
                    "timeline": None,
                },
            },
        )
    )

    async def fake_get_db():
        yield fake_session

    async def fake_get_current_user():
        return user_id

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.get("/api/athlete-profile", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == str(user_id)
    assert payload["profile"]["physiology"]["ftp"] == 250
    assert payload["profile"]["goals"]["primary_goal"] == "Build toward a strong half marathon"
    assert "zone_model" not in payload["profile"]["physiology"]
    assert "zones_notes" not in payload["profile"]["physiology"]
    assert "timeline" not in payload["profile"]["goals"]


def test_put_athlete_profile_rejects_unknown_client_fields():
    user_id = uuid.uuid4()
    fake_session = _FakeAsyncSession(row=None)

    async def fake_get_db():
        yield fake_session

    async def fake_get_current_user():
        return user_id

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.put(
        "/api/athlete-profile",
        json={
            "profile": {
                "physiology": {
                    "ftp": 250,
                    "zone_model": "mixed",
                }
            }
        },
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 422
    assert fake_session.add_calls == 0
    error_locations = [error["loc"] for error in response.json()["detail"]]
    assert ["body", "profile", "physiology", "zone_model"] in error_locations
