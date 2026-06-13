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
from api.models.credentials import WhoopCredentials
from api.models.oauth_session import OAuthSession
from api.services.crypto import get_crypto_service
from api.services.integration_connections import mark_integration_connected
from services.whoop.oauth import (
    WHOOP_PROFILE_URL,
    build_authorize_url,
    compute_expires_at,
    exchange_code_for_tokens,
)

router = APIRouter()

# Keep scopes explicit and minimal; add more only when the product needs it.
_DEFAULT_WHOOP_SCOPES: tuple[str, ...] = (
    "read:recovery",
    "read:cycles",
    "read:workout",
    "read:sleep",
    "read:profile",
    "read:body_measurement",
    "offline",
)


def _whoop_enabled_or_403():
    settings = get_settings()
    if not settings.whoop_oauth_enabled:
        raise HTTPException(status_code=403, detail="WHOOP OAuth is not enabled yet.")
    if not settings.whoop_oauth_client_id or not settings.whoop_oauth_client_secret:
        raise HTTPException(status_code=500, detail="WHOOP OAuth is not configured (missing client_id/client_secret).")
    if not settings.whoop_oauth_redirect_uri:
        raise HTTPException(status_code=500, detail="WHOOP OAuth is not configured (missing redirect_uri).")
    return settings


def _fetch_whoop_user_id(*, access_token: str) -> int | None:
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=10.0) as client:
        res = client.get(WHOOP_PROFILE_URL, headers=headers)
        res.raise_for_status()
        payload = res.json()
    raw_user_id = payload.get("user_id") if isinstance(payload, dict) else None
    try:
        return int(raw_user_id) if raw_user_id is not None else None
    except (TypeError, ValueError):
        return None


async def _load_whoop_oauth_session(
    db: AsyncSession,
    *,
    state: str,
    now: datetime,
) -> OAuthSession:
    session_row = await db.execute(
        select(OAuthSession)
        .where(
            OAuthSession.provider == "whoop",
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


async def _upsert_whoop_credentials(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    encrypted_access_token: bytes,
    encrypted_refresh_token: bytes | None,
    expires_at: datetime,
    scope: str,
    whoop_user_id: int | None,
):
    existing = await db.execute(select(WhoopCredentials).where(WhoopCredentials.user_id == user_id))
    creds = existing.scalar_one_or_none()
    if creds is None:
        db.add(
            WhoopCredentials(
                user_id=user_id,
                encrypted_access_token=encrypted_access_token,
                encrypted_refresh_token=encrypted_refresh_token,
                expires_at=expires_at,
                scope=str(scope or ""),
                whoop_user_id=whoop_user_id,
            )
        )
        return

    await db.execute(
        update(WhoopCredentials)
        .where(WhoopCredentials.user_id == user_id)
        .values(
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            expires_at=expires_at,
            scope=str(scope or ""),
            whoop_user_id=whoop_user_id,
        )
    )


@router.get("/start")
async def whoop_oauth_start(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> RedirectResponse:
    settings = _whoop_enabled_or_403()

    now = datetime.now(UTC)
    state = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=10)

    db.add(
        OAuthSession(
            user_id=user_id,
            provider="whoop",
            state=state,
            code_verifier=None,
            expires_at=expires_at,
            used_at=None,
        )
    )
    await db.flush()

    url = build_authorize_url(
        client_id=settings.whoop_oauth_client_id,
        redirect_uri=settings.whoop_oauth_redirect_uri,
        state=state,
        scope=" ".join(_DEFAULT_WHOOP_SCOPES),
    )
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback")
async def whoop_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    settings = _whoop_enabled_or_403()

    if error:
        description = error_description.strip() if isinstance(error_description, str) else ""
        detail = f"WHOOP OAuth error: {error}" + (f" ({description})" if description else "")
        raise HTTPException(status_code=400, detail=detail)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth parameters (code/state).")

    now = datetime.now(UTC)
    session = await _load_whoop_oauth_session(db, state=state, now=now)

    session.used_at = now
    db.add(session)
    await db.flush()

    try:
        token_payload = await asyncio.to_thread(
            exchange_code_for_tokens,
            code=code,
            client_id=settings.whoop_oauth_client_id,
            client_secret=settings.whoop_oauth_client_secret,
            redirect_uri=settings.whoop_oauth_redirect_uri,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail="WHOOP token exchange failed. Please try again.") from exc

    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")
    expires_in = token_payload.get("expires_in")
    scope = token_payload.get("scope") or ""
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=400, detail="WHOOP token exchange did not return an access token.")

    expires_at = compute_expires_at(now=now, expires_in=expires_in)

    whoop_user_id: int | None = None
    try:
        whoop_user_id = await asyncio.to_thread(_fetch_whoop_user_id, access_token=access_token)
    except Exception:
        # Optional enrichment only; do not fail the OAuth flow on profile lookup.
        whoop_user_id = None

    crypto = get_crypto_service()
    encrypted_access_token = crypto.encrypt(access_token)
    encrypted_refresh_token = crypto.encrypt(refresh_token) if isinstance(refresh_token, str) and refresh_token else None

    await _upsert_whoop_credentials(
        db,
        user_id=session.user_id,
        encrypted_access_token=encrypted_access_token,
        encrypted_refresh_token=encrypted_refresh_token,
        expires_at=expires_at,
        scope=str(scope or ""),
        whoop_user_id=whoop_user_id,
    )
    await mark_integration_connected(db, user_id=session.user_id, provider="whoop", connected_at=now)

    return {"status": "connected"}
