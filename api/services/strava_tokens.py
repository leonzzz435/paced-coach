from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException
from sqlalchemy import delete, select

from api.config import get_settings
from api.models.credentials import StravaCredentials
from api.services.crypto import get_crypto_service
from api.services.integration_connections import mark_integration_disconnected
from services.strava.oauth import compute_expires_at
from services.strava.oauth import refresh_tokens as _refresh_tokens_sync

logger = logging.getLogger(__name__)


async def ensure_valid_access_token(db, *, user_id) -> str:
    settings = get_settings()
    if not settings.strava_oauth_client_id or not settings.strava_oauth_client_secret:
        raise HTTPException(status_code=500, detail="Strava OAuth is not configured (missing client_id/client_secret).")

    row = await db.execute(
        select(StravaCredentials).where(StravaCredentials.user_id == user_id).with_for_update()
    )
    creds = row.scalar_one_or_none()
    if creds is None:
        raise HTTPException(status_code=404, detail="Strava is not connected for this account.")

    crypto = get_crypto_service()
    now = datetime.now(UTC)
    if creds.expires_at is not None and creds.expires_at.astimezone(UTC) > (now + timedelta(seconds=30)):
        return crypto.decrypt(creds.encrypted_access_token)

    if not creds.encrypted_refresh_token:
        raise HTTPException(status_code=409, detail="Strava refresh token is missing. Please reconnect Strava.")

    refresh_token = crypto.decrypt(creds.encrypted_refresh_token)
    try:
        payload = await asyncio.to_thread(
            _refresh_tokens_sync,
            refresh_token=refresh_token,
            client_id=settings.strava_oauth_client_id,
            client_secret=settings.strava_oauth_client_secret,
        )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in {400, 401}:
            logger.info("Strava token refresh rejected (status=%s); deleting stored credentials", status_code)
            await db.execute(delete(StravaCredentials).where(StravaCredentials.user_id == user_id))
            await mark_integration_disconnected(
                db,
                user_id=user_id,
                provider="strava",
                reason="token_refresh_rejected",
            )
            await db.commit()
            raise HTTPException(status_code=401, detail="Strava connection expired. Please reconnect Strava.") from exc
        raise HTTPException(status_code=502, detail="Strava token refresh failed. Please try again.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Strava token refresh failed. Please try again.") from exc

    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=502, detail="Strava token refresh returned an invalid access token.")

    new_refresh = payload.get("refresh_token")
    expires_at = compute_expires_at(
        now=now,
        expires_at=payload.get("expires_at"),
        expires_in=payload.get("expires_in"),
    )
    scope = creds.scope or ""

    creds.encrypted_access_token = crypto.encrypt(access_token)
    if isinstance(new_refresh, str) and new_refresh.strip():
        creds.encrypted_refresh_token = crypto.encrypt(new_refresh)
    creds.expires_at = expires_at
    creds.scope = str(scope or "")
    db.add(creds)

    return access_token
