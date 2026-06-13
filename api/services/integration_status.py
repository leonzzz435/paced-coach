from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Settings, get_settings
from api.models.credentials import StravaCredentials, WhoopCredentials
from api.models.integration_connection import IntegrationConnection
from api.models.oauth_session import OAuthSession
from api.services.integration_connections import get_connection_history_map

IntegrationState = Literal["connected", "attention_needed", "disconnected"]
ProviderConnectionState = Literal[
    "disabled",
    "unconfigured",
    "disconnected",
    "started",
    "callback_failed",
    "token_missing",
    "token_expired",
    "partial_permissions",
    "stale",
    "syncing",
    "connected_no_data",
    "connected_usable",
]

_REQUIRED_STRAVA_SCOPES = frozenset({"activity:read_all"})
_STRAVA_TOKEN_MISSING = "Strava is linked, but the access token is missing. Reconnect Strava."
_STRAVA_SCOPE_MISSING = (
    "Strava is linked, but the accepted scopes do not allow complete activity history. "
    "Reconnect Strava and grant full activity access."
)
_STRAVA_REFRESH_MISSING = "Strava connection expired and cannot refresh. Reconnect Strava."
_STRAVA_REFRESH_UNCONFIGURED = "Strava needs token refresh, but OAuth refresh is not configured in this environment."
_WHOOP_TOKEN_MISSING = "WHOOP is linked, but the access token is missing. Reconnect WHOOP."
_WHOOP_REFRESH_MISSING = "WHOOP connection expired and cannot refresh. Reconnect WHOOP."
_WHOOP_REFRESH_UNCONFIGURED = "WHOOP needs token refresh, but OAuth refresh is not configured in this environment."
_STRAVA_DISABLED = "Strava connector is disabled. Set STRAVA_OAUTH_ENABLED=true to use it."
_WHOOP_DISABLED = "WHOOP connector is disabled. Set WHOOP_OAUTH_ENABLED=true to use it."
_STRAVA_UNCONFIGURED = "Strava connector is enabled, but local OAuth credentials or redirect URI are missing."
_WHOOP_UNCONFIGURED = "WHOOP connector is enabled, but local OAuth credentials or redirect URI are missing."
_STRAVA_STARTED = "Strava connection was started. Complete the provider approval flow or restart it."
_WHOOP_STARTED = "WHOOP connection was started. Complete the provider approval flow or restart it."
_STRAVA_CALLBACK_FAILED = "The last Strava callback did not store credentials. Restart the connection flow."
_WHOOP_CALLBACK_FAILED = "The last WHOOP callback did not store credentials. Restart the connection flow."


class StravaIntegrationStatus(BaseModel):
    linked: bool
    ever_connected: bool
    connected: bool
    operational: bool
    state: IntegrationState
    connection_state: ProviderConnectionState
    configured: bool
    oauth_enabled: bool
    attention_message: str | None = None
    athlete_id: int | None = None
    expires_at: str | None = None
    scope: str | None = None
    first_connected_at: str | None = None
    last_connected_at: str | None = None
    last_disconnected_at: str | None = None
    last_disconnect_reason: str | None = None


class WhoopIntegrationStatus(BaseModel):
    linked: bool
    ever_connected: bool
    connected: bool
    operational: bool
    state: IntegrationState
    connection_state: ProviderConnectionState
    configured: bool
    oauth_enabled: bool
    attention_message: str | None = None
    whoop_user_id: int | None = None
    expires_at: str | None = None
    scope: str | None = None
    first_connected_at: str | None = None
    last_connected_at: str | None = None
    last_disconnected_at: str | None = None
    last_disconnect_reason: str | None = None


class IntegrationsStatus(BaseModel):
    strava: StravaIntegrationStatus
    whoop: WhoopIntegrationStatus


class _HistoryPayload(TypedDict):
    ever_connected: bool
    first_connected_at: str | None
    last_connected_at: str | None
    last_disconnected_at: str | None
    last_disconnect_reason: str | None


def _iso_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _history_payload(history: IntegrationConnection | None) -> _HistoryPayload:
    return {
        "ever_connected": history is not None,
        "first_connected_at": _iso_timestamp(history.first_connected_at) if history is not None else None,
        "last_connected_at": _iso_timestamp(history.last_connected_at) if history is not None else None,
        "last_disconnected_at": _iso_timestamp(history.last_disconnected_at) if history is not None else None,
        "last_disconnect_reason": history.last_disconnect_reason if history is not None else None,
    }


def _strava_oauth_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "strava_oauth_enabled", False))


def _whoop_oauth_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "whoop_oauth_enabled", False))


def _strava_configured(settings: Settings) -> bool:
    return all(
        bool(str(getattr(settings, field, "") or "").strip())
        for field in (
            "strava_oauth_client_id",
            "strava_oauth_client_secret",
            "strava_oauth_redirect_uri",
        )
    )


def _strava_refresh_configured(settings: Settings) -> bool:
    return all(
        bool(str(getattr(settings, field, "") or "").strip())
        for field in (
            "strava_oauth_client_id",
            "strava_oauth_client_secret",
        )
    )


def _whoop_configured(settings: Settings) -> bool:
    return all(
        bool(str(getattr(settings, field, "") or "").strip())
        for field in (
            "whoop_oauth_client_id",
            "whoop_oauth_client_secret",
            "whoop_oauth_redirect_uri",
        )
    )


def _whoop_refresh_configured(settings: Settings) -> bool:
    return all(
        bool(str(getattr(settings, field, "") or "").strip())
        for field in (
            "whoop_oauth_client_id",
            "whoop_oauth_client_secret",
        )
    )


def _oauth_session_state(
    session: OAuthSession | None,
    *,
    history: IntegrationConnection | None,
    now: datetime,
    started_state: ProviderConnectionState,
    callback_failed_state: ProviderConnectionState,
) -> ProviderConnectionState | None:
    if session is None:
        return None
    if (
        session.used_at is not None
        and history is not None
        and history.last_disconnected_at is not None
        and history.last_disconnected_at.astimezone(UTC) >= session.used_at.astimezone(UTC)
    ):
        return None
    if session.used_at is not None:
        return callback_failed_state
    if session.expires_at.astimezone(UTC) > now:
        return started_state
    return None


def _session_attention_message(provider: str, state: ProviderConnectionState | None) -> str | None:
    if state == "started":
        return _STRAVA_STARTED if provider == "strava" else _WHOOP_STARTED
    if state == "callback_failed":
        return _STRAVA_CALLBACK_FAILED if provider == "strava" else _WHOOP_CALLBACK_FAILED
    return None


def _join_provider_names(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _scope_tokens(scope: str | None) -> set[str]:
    normalized_scope = str(scope or "").replace(",", " ")
    return {token.strip() for token in normalized_scope.split() if token.strip()}


def _attention_provider_names(status: IntegrationsStatus) -> list[str]:
    names: list[str] = []
    if status.strava.state == "attention_needed":
        names.append("Strava")
    if status.whoop.state == "attention_needed":
        names.append("WHOOP")
    return names


def attention_messages(status: IntegrationsStatus) -> list[str]:
    messages: list[str] = []
    for provider_status in (status.strava, status.whoop):
        if provider_status.state != "attention_needed":
            continue
        message = str(provider_status.attention_message or "").strip()
        if message and message not in messages:
            messages.append(message)
    return messages


def _previously_connected_provider_names(status: IntegrationsStatus) -> list[str]:
    names: list[str] = []
    if not status.strava.linked and status.strava.ever_connected:
        names.append("Strava")
    if not status.whoop.linked and status.whoop.ever_connected:
        names.append("WHOOP")
    return names


def _build_strava_status(
    *,
    strava: StravaCredentials | None,
    history: IntegrationConnection | None,
    oauth_session: OAuthSession | None,
    settings: Settings,
    now: datetime,
) -> StravaIntegrationStatus:
    oauth_enabled = _strava_oauth_enabled(settings)
    configured = _strava_configured(settings)
    if strava is None:
        session_state = _oauth_session_state(
            oauth_session,
            history=history,
            now=now,
            started_state="started",
            callback_failed_state="callback_failed",
        )
        if session_state is not None:
            return StravaIntegrationStatus(
                linked=False,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="attention_needed",
                connection_state=session_state,
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_session_attention_message("strava", session_state),
            )
        if not oauth_enabled:
            return StravaIntegrationStatus(
                linked=False,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="disconnected",
                connection_state="disabled",
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_STRAVA_DISABLED,
            )
        if not configured:
            return StravaIntegrationStatus(
                linked=False,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="attention_needed",
                connection_state="unconfigured",
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_STRAVA_UNCONFIGURED,
            )
        return StravaIntegrationStatus(
            linked=False,
            **_history_payload(history),
            connected=False,
            operational=False,
            state="disconnected",
            connection_state="disconnected",
            configured=configured,
            oauth_enabled=oauth_enabled,
        )

    expires_at = strava.expires_at.astimezone(UTC) if strava.expires_at is not None else None
    expires_at_iso = expires_at.isoformat() if expires_at is not None else None

    if not strava.encrypted_access_token:
        return StravaIntegrationStatus(
            linked=True,
            **_history_payload(history),
            connected=False,
            operational=False,
            state="attention_needed",
            connection_state="token_missing",
            configured=configured,
            oauth_enabled=oauth_enabled,
            attention_message=_STRAVA_TOKEN_MISSING,
            athlete_id=strava.strava_athlete_id,
            expires_at=expires_at_iso,
            scope=strava.scope or None,
        )

    if not _REQUIRED_STRAVA_SCOPES.issubset(_scope_tokens(strava.scope)):
        return StravaIntegrationStatus(
            linked=True,
            **_history_payload(history),
            connected=False,
            operational=False,
            state="attention_needed",
            connection_state="partial_permissions",
            configured=configured,
            oauth_enabled=oauth_enabled,
            attention_message=_STRAVA_SCOPE_MISSING,
            athlete_id=strava.strava_athlete_id,
            expires_at=expires_at_iso,
            scope=strava.scope or None,
        )

    if expires_at is not None and expires_at <= now:
        if not strava.encrypted_refresh_token:
            return StravaIntegrationStatus(
                linked=True,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="attention_needed",
                connection_state="token_expired",
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_STRAVA_REFRESH_MISSING,
                athlete_id=strava.strava_athlete_id,
                expires_at=expires_at_iso,
                scope=strava.scope or None,
            )
        if not _strava_refresh_configured(settings):
            return StravaIntegrationStatus(
                linked=True,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="attention_needed",
                connection_state="stale",
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_STRAVA_REFRESH_UNCONFIGURED,
                athlete_id=strava.strava_athlete_id,
                expires_at=expires_at_iso,
                scope=strava.scope or None,
            )

    return StravaIntegrationStatus(
        linked=True,
        **_history_payload(history),
        connected=True,
        operational=True,
        state="connected",
        connection_state="connected_usable",
        configured=configured,
        oauth_enabled=oauth_enabled,
        athlete_id=strava.strava_athlete_id,
        expires_at=expires_at_iso,
        scope=strava.scope or None,
    )


def _build_whoop_status(
    *,
    whoop: WhoopCredentials | None,
    history: IntegrationConnection | None,
    oauth_session: OAuthSession | None,
    settings: Settings,
    now: datetime,
) -> WhoopIntegrationStatus:
    oauth_enabled = _whoop_oauth_enabled(settings)
    configured = _whoop_configured(settings)
    if whoop is None:
        session_state = _oauth_session_state(
            oauth_session,
            history=history,
            now=now,
            started_state="started",
            callback_failed_state="callback_failed",
        )
        if session_state is not None:
            return WhoopIntegrationStatus(
                linked=False,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="attention_needed",
                connection_state=session_state,
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_session_attention_message("whoop", session_state),
            )
        if not oauth_enabled:
            return WhoopIntegrationStatus(
                linked=False,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="disconnected",
                connection_state="disabled",
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_WHOOP_DISABLED,
            )
        if not configured:
            return WhoopIntegrationStatus(
                linked=False,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="attention_needed",
                connection_state="unconfigured",
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_WHOOP_UNCONFIGURED,
            )
        return WhoopIntegrationStatus(
            linked=False,
            **_history_payload(history),
            connected=False,
            operational=False,
            state="disconnected",
            connection_state="disconnected",
            configured=configured,
            oauth_enabled=oauth_enabled,
        )

    expires_at = whoop.expires_at.astimezone(UTC) if whoop.expires_at is not None else None
    expires_at_iso = expires_at.isoformat() if expires_at is not None else None

    if not whoop.encrypted_access_token:
        return WhoopIntegrationStatus(
            linked=True,
            **_history_payload(history),
            connected=False,
            operational=False,
            state="attention_needed",
            connection_state="token_missing",
            configured=configured,
            oauth_enabled=oauth_enabled,
            attention_message=_WHOOP_TOKEN_MISSING,
            whoop_user_id=whoop.whoop_user_id,
            expires_at=expires_at_iso,
            scope=whoop.scope or None,
        )

    if expires_at is not None and expires_at <= now:
        if not whoop.encrypted_refresh_token:
            return WhoopIntegrationStatus(
                linked=True,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="attention_needed",
                connection_state="token_expired",
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_WHOOP_REFRESH_MISSING,
                whoop_user_id=whoop.whoop_user_id,
                expires_at=expires_at_iso,
                scope=whoop.scope or None,
            )
        if not _whoop_refresh_configured(settings):
            return WhoopIntegrationStatus(
                linked=True,
                **_history_payload(history),
                connected=False,
                operational=False,
                state="attention_needed",
                connection_state="stale",
                configured=configured,
                oauth_enabled=oauth_enabled,
                attention_message=_WHOOP_REFRESH_UNCONFIGURED,
                whoop_user_id=whoop.whoop_user_id,
                expires_at=expires_at_iso,
                scope=whoop.scope or None,
            )

    return WhoopIntegrationStatus(
        linked=True,
        **_history_payload(history),
        connected=True,
        operational=True,
        state="connected",
        connection_state="connected_usable",
        configured=configured,
        oauth_enabled=oauth_enabled,
        whoop_user_id=whoop.whoop_user_id,
        expires_at=expires_at_iso,
        scope=whoop.scope or None,
    )


def build_integrations_status(
    *,
    settings: Settings,
    crypto_service: Any | None = None,
    strava: StravaCredentials | None = None,
    whoop: WhoopCredentials | None = None,
    strava_history: IntegrationConnection | None = None,
    whoop_history: IntegrationConnection | None = None,
    strava_oauth_session: OAuthSession | None = None,
    whoop_oauth_session: OAuthSession | None = None,
    now: datetime | None = None,
) -> IntegrationsStatus:
    del crypto_service
    resolved_now = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    return IntegrationsStatus(
        strava=_build_strava_status(
            strava=strava,
            history=strava_history,
            oauth_session=strava_oauth_session,
            settings=settings,
            now=resolved_now,
        ),
        whoop=_build_whoop_status(
            whoop=whoop,
            history=whoop_history,
            oauth_session=whoop_oauth_session,
            settings=settings,
            now=resolved_now,
        ),
    )


async def _load_latest_oauth_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
) -> OAuthSession | None:
    row = await db.execute(
        select(OAuthSession)
        .where(
            OAuthSession.user_id == user_id,
            OAuthSession.provider == provider,
        )
        .order_by(OAuthSession.created_at.desc())
        .limit(1)
    )
    return row.scalar_one_or_none()


async def load_integrations_status(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> IntegrationsStatus:
    strava_row = await db.execute(select(StravaCredentials).where(StravaCredentials.user_id == user_id))
    whoop_row = await db.execute(select(WhoopCredentials).where(WhoopCredentials.user_id == user_id))
    strava_session = await _load_latest_oauth_session(db, user_id=user_id, provider="strava")
    whoop_session = await _load_latest_oauth_session(db, user_id=user_id, provider="whoop")
    history_map = await get_connection_history_map(db, user_id=user_id)

    resolved_settings = settings or get_settings()
    return build_integrations_status(
        settings=resolved_settings,
        strava=strava_row.scalar_one_or_none(),
        whoop=whoop_row.scalar_one_or_none(),
        strava_history=history_map.get("strava"),
        whoop_history=history_map.get("whoop"),
        strava_oauth_session=strava_session,
        whoop_oauth_session=whoop_session,
        now=now,
    )


def has_operational_training_provider(status: IntegrationsStatus) -> bool:
    return status.strava.operational or status.whoop.operational


def has_linked_training_provider(status: IntegrationsStatus) -> bool:
    return status.strava.linked or status.whoop.linked


def has_ever_connected_training_provider(status: IntegrationsStatus) -> bool:
    return status.strava.ever_connected or status.whoop.ever_connected


def training_provider_requirement_message(status: IntegrationsStatus) -> str:
    if has_operational_training_provider(status):
        return ""
    attention_names = _attention_provider_names(status)
    if attention_names:
        subject = _join_provider_names(attention_names)
        verb = "needs" if len(attention_names) == 1 else "need"
        return f"{subject} {verb} attention before a run can start. Check integration settings."
    disconnected_names = _previously_connected_provider_names(status)
    if disconnected_names:
        subject = _join_provider_names(disconnected_names)
        verb = "was" if len(disconnected_names) == 1 else "were"
        noun = "it" if len(disconnected_names) == 1 else "a training source"
        return f"{subject} {verb} disconnected. Reconnect {noun} in Settings before starting a run."
    return "No training data source connected. Connect a supported training source first."


def training_provider_block_message(status: IntegrationsStatus) -> str:
    if has_operational_training_provider(status):
        return ""
    messages = attention_messages(status)
    if messages:
        return " ".join(messages)
    return training_provider_requirement_message(status)


def training_provider_notice_message(status: IntegrationsStatus) -> str | None:
    messages = attention_messages(status)
    if messages:
        return " ".join(messages)
    if not has_operational_training_provider(status):
        message = training_provider_requirement_message(status)
        return message or None
    return None
