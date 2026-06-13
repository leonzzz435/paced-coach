from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import ProgrammingError

from api.models.credentials import StravaCredentials, WhoopCredentials
from api.models.integration_connection import IntegrationConnection
from api.models.oauth_session import OAuthSession
from api.services.integration_connections import get_connection_history_map
from api.services.integration_status import (
    build_integrations_status,
    has_operational_training_provider,
    training_provider_requirement_message,
)


def _settings(**overrides):
    values = {
        "strava_oauth_enabled": True,
        "strava_oauth_client_id": "client-id",
        "strava_oauth_client_secret": "client-secret",
        "strava_oauth_redirect_uri": "http://localhost:3000/app/api/oauth/strava/callback",
        "whoop_oauth_enabled": True,
        "whoop_oauth_client_id": "client-id",
        "whoop_oauth_client_secret": "client-secret",
        "whoop_oauth_redirect_uri": "http://localhost:3000/app/api/oauth/whoop/callback",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _history(provider: str, **overrides) -> IntegrationConnection:
    values = {
        "user_id": uuid4(),
        "provider": provider,
        "first_connected_at": datetime(2026, 3, 1, tzinfo=UTC),
        "last_connected_at": datetime(2026, 3, 6, tzinfo=UTC),
        "last_disconnected_at": datetime(2026, 3, 7, tzinfo=UTC),
        "last_disconnect_reason": "user_initiated",
    }
    values.update(overrides)
    return IntegrationConnection(**values)


@pytest.mark.unit
def test_integrations_status_marks_absent_providers_disconnected():
    status = build_integrations_status(
        settings=_settings(),
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )

    assert status.strava.state == "disconnected"
    assert status.strava.connection_state == "disconnected"
    assert status.whoop.state == "disconnected"
    assert status.whoop.connection_state == "disconnected"
    assert status.strava.ever_connected is False
    assert status.whoop.ever_connected is False
    assert has_operational_training_provider(status) is False
    assert training_provider_requirement_message(status) == "No training data source connected. Connect a supported training source first."


@pytest.mark.unit
def test_integrations_status_marks_strava_attention_when_scope_is_insufficient():
    strava = StravaCredentials(
        user_id=uuid4(),
        encrypted_access_token=b"access-token",
        encrypted_refresh_token=b"refresh-token",
        expires_at=datetime(2026, 3, 8, tzinfo=UTC),
        scope="activity:read",
        strava_athlete_id=12345,
    )

    status = build_integrations_status(
        settings=_settings(),
        strava=strava,
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )

    assert status.strava.linked is True
    assert status.strava.operational is False
    assert status.strava.connected is False
    assert status.strava.state == "attention_needed"
    assert status.strava.connection_state == "partial_permissions"
    assert status.strava.athlete_id == 12345
    assert "accepted scopes do not allow complete activity history" in (status.strava.attention_message or "")


@pytest.mark.unit
def test_integrations_status_treats_refreshable_strava_as_operational():
    strava = StravaCredentials(
        user_id=uuid4(),
        encrypted_access_token=b"access-token",
        encrypted_refresh_token=b"refresh-token",
        expires_at=datetime(2026, 3, 6, tzinfo=UTC),
        scope="activity:read_all",
        strava_athlete_id=12345,
    )

    status = build_integrations_status(
        settings=_settings(),
        strava=strava,
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )

    assert status.strava.linked is True
    assert status.strava.operational is True
    assert status.strava.connected is True
    assert status.strava.state == "connected"
    assert status.strava.connection_state == "connected_usable"
    assert has_operational_training_provider(status) is True


@pytest.mark.unit
def test_integrations_status_refreshable_tokens_do_not_require_redirect_uri():
    whoop = WhoopCredentials(
        user_id=uuid4(),
        encrypted_access_token=b"access-token",
        encrypted_refresh_token=b"refresh-token",
        expires_at=datetime(2026, 3, 6, tzinfo=UTC),
        scope="offline read:recovery",
        whoop_user_id=42,
    )

    status = build_integrations_status(
        settings=_settings(whoop_oauth_redirect_uri=""),
        whoop=whoop,
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )

    assert status.whoop.operational is True
    assert status.whoop.connection_state == "connected_usable"


@pytest.mark.unit
def test_integrations_status_marks_expired_whoop_without_refresh_as_attention_needed():
    whoop = WhoopCredentials(
        user_id=uuid4(),
        encrypted_access_token=b"access-token",
        encrypted_refresh_token=None,
        expires_at=datetime(2026, 3, 6, tzinfo=UTC),
        scope="offline read:recovery",
        whoop_user_id=42,
    )

    status = build_integrations_status(
        settings=_settings(),
        whoop=whoop,
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )

    assert status.whoop.linked is True
    assert status.whoop.operational is False
    assert status.whoop.connected is False
    assert status.whoop.state == "attention_needed"
    assert status.whoop.connection_state == "token_expired"
    assert "Reconnect WHOOP" in (status.whoop.attention_message or "")


@pytest.mark.unit
def test_integrations_status_marks_previously_connected_provider_as_disconnected_history():
    history = _history("strava", last_disconnect_reason="provider_deregistered")

    status = build_integrations_status(
        settings=_settings(),
        strava_history=history,
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )

    assert status.strava.linked is False
    assert status.strava.connection_state == "disconnected"
    assert status.strava.ever_connected is True
    assert status.strava.last_disconnect_reason == "provider_deregistered"
    assert status.strava.last_disconnected_at == "2026-03-07T00:00:00+00:00"
    assert training_provider_requirement_message(status) == (
        "Strava was disconnected. Reconnect it in Settings before starting a run."
    )


@pytest.mark.unit
def test_integrations_status_marks_provider_unconfigured_when_enabled_without_redirect_uri():
    status = build_integrations_status(
        settings=_settings(strava_oauth_redirect_uri=""),
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )

    assert status.strava.linked is False
    assert status.strava.state == "attention_needed"
    assert status.strava.connection_state == "unconfigured"
    assert status.strava.configured is False
    assert status.strava.oauth_enabled is True
    assert "redirect URI are missing" in (status.strava.attention_message or "")


@pytest.mark.unit
def test_integrations_status_marks_disabled_provider_without_blocking_manual_mode():
    status = build_integrations_status(
        settings=_settings(strava_oauth_enabled=False),
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )

    assert status.strava.state == "disconnected"
    assert status.strava.connection_state == "disabled"
    assert status.strava.oauth_enabled is False
    assert has_operational_training_provider(status) is False
    assert training_provider_requirement_message(status) == "No training data source connected. Connect a supported training source first."


@pytest.mark.unit
def test_integrations_status_marks_started_oauth_session():
    session = OAuthSession(
        user_id=uuid4(),
        provider="strava",
        state="state-123",
        code_verifier=None,
        expires_at=datetime(2026, 3, 7, 0, 10, tzinfo=UTC),
        used_at=None,
    )

    status = build_integrations_status(
        settings=_settings(),
        strava_oauth_session=session,
        now=datetime(2026, 3, 7, tzinfo=UTC),
    )

    assert status.strava.linked is False
    assert status.strava.state == "attention_needed"
    assert status.strava.connection_state == "started"
    assert "Complete the provider approval flow" in (status.strava.attention_message or "")


@pytest.mark.unit
def test_integrations_status_marks_callback_failed_only_until_disconnect_supersedes_session():
    user_id = uuid4()
    used_at = datetime(2026, 3, 7, 0, 5, tzinfo=UTC)
    session = OAuthSession(
        user_id=user_id,
        provider="whoop",
        state="state-123",
        code_verifier=None,
        expires_at=used_at + timedelta(minutes=5),
        used_at=used_at,
    )

    failed_status = build_integrations_status(
        settings=_settings(),
        whoop_oauth_session=session,
        now=datetime(2026, 3, 7, 0, 6, tzinfo=UTC),
    )
    assert failed_status.whoop.connection_state == "callback_failed"

    disconnected_status = build_integrations_status(
        settings=_settings(),
        whoop_oauth_session=session,
        whoop_history=_history(
            "whoop",
            user_id=user_id,
            last_disconnected_at=used_at + timedelta(minutes=1),
        ),
        now=datetime(2026, 3, 7, 0, 7, tzinfo=UTC),
    )
    assert disconnected_status.whoop.connection_state == "disconnected"


class _FakeUndefinedTableError(Exception):
    sqlstate = "42P01"

    def __str__(self) -> str:
        return 'relation "integration_connections" does not exist'


@pytest.mark.asyncio
async def test_get_connection_history_map_returns_empty_when_history_table_missing():
    fake_db = SimpleNamespace(
        execute=AsyncMock(side_effect=ProgrammingError("SELECT 1", {}, _FakeUndefinedTableError()))
    )

    history_map = await get_connection_history_map(fake_db, user_id=uuid4())

    assert history_map == {}
