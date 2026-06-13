from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

import api.deps as deps_module
from api.main import create_app
from api.models.credentials import WhoopCredentials
from api.models.oauth_session import OAuthSession


async def _noop_mark_integration_connected(*_args, **_kwargs):
    return None


def test_whoop_callback_accepts_browser_redirect_without_auth_header(monkeypatch):
    from api.routers import whoop_oauth as whoop_oauth_router

    user_id = uuid4()
    oauth_session = OAuthSession(
        user_id=user_id,
        provider="whoop",
        state="state-123",
        code_verifier=None,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        used_at=None,
    )

    class FakeScalarResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class FakeAsyncSession:
        def __init__(self):
            self.added: list[object] = []

        async def execute(self, statement):
            sql = str(statement)
            if "FROM oauth_sessions" in sql:
                return FakeScalarResult(oauth_session)
            if "FROM whoop_credentials" in sql:
                return FakeScalarResult(None)
            raise AssertionError(f"Unexpected SQL: {sql}")

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            return None

    fake_session = FakeAsyncSession()

    async def fake_get_db():
        yield fake_session

    monkeypatch.setattr(
        whoop_oauth_router,
        "get_settings",
        lambda: SimpleNamespace(
            whoop_oauth_enabled=True,
            whoop_oauth_client_id="client-id",
            whoop_oauth_client_secret="client-secret",
            whoop_oauth_redirect_uri="http://localhost:3000/app/api/oauth/whoop/callback",
        ),
    )
    monkeypatch.setattr(
        whoop_oauth_router,
        "exchange_code_for_tokens",
        lambda **_kwargs: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
            "scope": "offline read:recovery",
        },
    )
    monkeypatch.setattr(whoop_oauth_router, "_fetch_whoop_user_id", lambda **_kwargs: 4242)
    monkeypatch.setattr(
        whoop_oauth_router,
        "get_crypto_service",
        lambda: SimpleNamespace(encrypt=lambda value: f"enc:{value}".encode()),
    )
    monkeypatch.setattr(
        whoop_oauth_router,
        "mark_integration_connected",
        _noop_mark_integration_connected,
    )

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db

    client = TestClient(app)
    response = client.get("/api/oauth/whoop/callback?code=test-code&state=state-123")

    assert response.status_code == 200
    assert response.json() == {"status": "connected"}
    assert oauth_session.used_at is not None

    saved_credentials = next(obj for obj in fake_session.added if isinstance(obj, WhoopCredentials))
    assert saved_credentials.user_id == user_id
    assert saved_credentials.encrypted_access_token == b"enc:access-token"
    assert saved_credentials.encrypted_refresh_token == b"enc:refresh-token"
    assert saved_credentials.scope == "offline read:recovery"
    assert saved_credentials.whoop_user_id == 4242
