from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

import api.deps as deps_module
from api.main import create_app
from api.models.credentials import StravaCredentials
from api.models.oauth_session import OAuthSession


async def _noop_mark_integration_connected(*_args, **_kwargs):
    return None


def test_strava_start_creates_oauth_session_and_redirects(monkeypatch):
    from api.routers import strava_oauth as strava_oauth_router

    user_id = uuid4()
    captured_authorize_kwargs: dict[str, str] = {}

    class FakeAsyncSession:
        def __init__(self):
            self.added: list[object] = []

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            return None

    fake_session = FakeAsyncSession()

    async def fake_get_db():
        yield fake_session

    monkeypatch.setattr(
        strava_oauth_router,
        "get_settings",
        lambda: SimpleNamespace(
            strava_oauth_enabled=True,
            strava_oauth_client_id="strava-client-id",
            strava_oauth_client_secret="strava-client-secret",
            strava_oauth_redirect_uri="http://localhost:3000/app/api/oauth/strava/callback",
        ),
    )

    def _fake_build_authorize_url(**kwargs):
        captured_authorize_kwargs.update(kwargs)
        return "https://www.strava.com/oauth/authorize?state=test-state"

    monkeypatch.setattr(strava_oauth_router, "build_authorize_url", _fake_build_authorize_url)

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = lambda: user_id

    client = TestClient(app)
    response = client.get("/api/oauth/strava/start", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://www.strava.com/oauth/authorize?state=test-state"
    saved_session = next(obj for obj in fake_session.added if isinstance(obj, OAuthSession))
    assert saved_session.user_id == user_id
    assert saved_session.provider == "strava"
    assert captured_authorize_kwargs["client_id"] == "strava-client-id"
    assert captured_authorize_kwargs["redirect_uri"] == "http://localhost:3000/app/api/oauth/strava/callback"
    assert captured_authorize_kwargs["scope"] == "activity:read_all"
    assert captured_authorize_kwargs["state"] == saved_session.state


def test_strava_callback_accepts_browser_redirect_without_auth_header(monkeypatch):
    from api.routers import strava_oauth as strava_oauth_router

    user_id = uuid4()
    oauth_session = OAuthSession(
        user_id=user_id,
        provider="strava",
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
            if "FROM strava_credentials" in sql:
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
        strava_oauth_router,
        "get_settings",
        lambda: SimpleNamespace(
            strava_oauth_enabled=True,
            strava_oauth_client_id="strava-client-id",
            strava_oauth_client_secret="strava-client-secret",
            strava_oauth_redirect_uri="http://localhost:3000/app/api/oauth/strava/callback",
        ),
    )
    monkeypatch.setattr(
        strava_oauth_router,
        "exchange_code_for_tokens",
        lambda **_kwargs: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_at": int((datetime.now(UTC) + timedelta(hours=6)).timestamp()),
            "athlete": {"id": 90210},
        },
    )
    monkeypatch.setattr(
        strava_oauth_router,
        "get_crypto_service",
        lambda: SimpleNamespace(encrypt=lambda value: f"enc:{value}".encode()),
    )
    monkeypatch.setattr(
        strava_oauth_router,
        "mark_integration_connected",
        _noop_mark_integration_connected,
    )

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db

    client = TestClient(app)
    response = client.get("/api/oauth/strava/callback?code=test-code&state=state-123&scope=activity:read_all")

    assert response.status_code == 200
    assert response.json() == {"status": "connected"}
    assert oauth_session.used_at is not None

    saved_credentials = next(obj for obj in fake_session.added if isinstance(obj, StravaCredentials))
    assert saved_credentials.user_id == user_id
    assert saved_credentials.encrypted_access_token == b"enc:access-token"
    assert saved_credentials.encrypted_refresh_token == b"enc:refresh-token"
    assert saved_credentials.scope == "activity:read_all"
    assert saved_credentials.strava_athlete_id == 90210
