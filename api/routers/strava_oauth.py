import asyncio
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.deps import get_current_user, get_db
from api.models.credentials import StravaCredentials
from api.models.oauth_session import OAuthSession
from api.services.crypto import get_crypto_service
from api.services.integration_connections import mark_integration_connected
from services.strava.oauth import build_authorize_url, compute_expires_at, exchange_code_for_tokens

router = APIRouter()

_DEFAULT_STRAVA_SCOPES: tuple[str, ...] = ("activity:read_all",)


def _strava_enabled_or_403():
    settings = get_settings()
    if not settings.strava_oauth_enabled:
        raise HTTPException(status_code=403, detail="Strava OAuth is not enabled yet.")
    if not settings.strava_oauth_client_id or not settings.strava_oauth_client_secret:
        raise HTTPException(status_code=500, detail="Strava OAuth is not configured (missing client_id/client_secret).")
    if not settings.strava_oauth_redirect_uri:
        raise HTTPException(status_code=500, detail="Strava OAuth is not configured (missing redirect_uri).")
    return settings


def _extract_athlete_id(token_payload: dict) -> int | None:
    athlete = token_payload.get("athlete")
    if not isinstance(athlete, dict):
        return None
    raw_athlete_id = athlete.get("id")
    try:
        return int(raw_athlete_id) if raw_athlete_id is not None else None
    except (TypeError, ValueError):
        return None


async def _load_strava_oauth_session(
    db: AsyncSession,
    *,
    state: str,
    now: datetime,
) -> OAuthSession:
    session_row = await db.execute(
        select(OAuthSession)
        .where(
            OAuthSession.provider == "strava",
            OAuthSession.state == state,
        )
        .with_for_update()
    )
    session = session_row.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    if session.used_at is not None:
        raise HTTPException(status_code=409, detail="OAuth state already used.")
    if session.expires_at.astimezone(UTC) <= now:
        raise HTTPException(status_code=400, detail="OAuth state expired. Please restart the connection flow.")
    return session


async def _upsert_strava_credentials(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    encrypted_access_token: bytes,
    encrypted_refresh_token: bytes | None,
    expires_at: datetime,
    scope: str,
    strava_athlete_id: int | None,
):
    existing = await db.execute(select(StravaCredentials).where(StravaCredentials.user_id == user_id))
    creds = existing.scalar_one_or_none()
    if creds is None:
        db.add(
            StravaCredentials(
                user_id=user_id,
                encrypted_access_token=encrypted_access_token,
                encrypted_refresh_token=encrypted_refresh_token,
                expires_at=expires_at,
                scope=str(scope or ""),
                strava_athlete_id=strava_athlete_id,
            )
        )
        return

    await db.execute(
        update(StravaCredentials)
        .where(StravaCredentials.user_id == user_id)
        .values(
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            expires_at=expires_at,
            scope=str(scope or ""),
            strava_athlete_id=strava_athlete_id,
        )
    )


@router.get("/start")
async def strava_oauth_start(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> RedirectResponse:
    settings = _strava_enabled_or_403()

    now = datetime.now(UTC)
    state = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=10)

    db.add(
        OAuthSession(
            user_id=user_id,
            provider="strava",
            state=state,
            code_verifier=None,
            expires_at=expires_at,
            used_at=None,
        )
    )
    await db.flush()

    url = build_authorize_url(
        client_id=settings.strava_oauth_client_id,
        redirect_uri=settings.strava_oauth_redirect_uri,
        state=state,
        scope=",".join(_DEFAULT_STRAVA_SCOPES),
    )
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback")
async def strava_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    scope: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    settings = _strava_enabled_or_403()

    if error:
        raise HTTPException(status_code=400, detail=f"Strava OAuth error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth parameters (code/state).")

    now = datetime.now(UTC)
    session = await _load_strava_oauth_session(db, state=state, now=now)

    session.used_at = now
    db.add(session)
    await db.flush()

    try:
        token_payload = await asyncio.to_thread(
            exchange_code_for_tokens,
            code=code,
            client_id=settings.strava_oauth_client_id,
            client_secret=settings.strava_oauth_client_secret,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail="Strava token exchange failed. Please try again.") from exc

    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")
    expires_at = compute_expires_at(
        now=now,
        expires_at=token_payload.get("expires_at"),
        expires_in=token_payload.get("expires_in"),
    )
    accepted_scope = str(scope or "")
    strava_athlete_id = _extract_athlete_id(token_payload)
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=400, detail="Strava token exchange did not return an access token.")

    crypto = get_crypto_service()
    encrypted_access_token = crypto.encrypt(access_token)
    encrypted_refresh_token = crypto.encrypt(refresh_token) if isinstance(refresh_token, str) and refresh_token else None

    await _upsert_strava_credentials(
        db,
        user_id=session.user_id,
        encrypted_access_token=encrypted_access_token,
        encrypted_refresh_token=encrypted_refresh_token,
        expires_at=expires_at,
        scope=accepted_scope,
        strava_athlete_id=strava_athlete_id,
    )
    await mark_integration_connected(db, user_id=session.user_id, provider="strava", connected_at=now)

    return {"status": "connected"}
