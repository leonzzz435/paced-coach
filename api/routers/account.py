import asyncio
import logging
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.models.credentials import StravaCredentials, WhoopCredentials
from api.models.job import AnalysisJob
from api.models.oauth_session import OAuthSession
from api.services.account_deletion import delete_account_and_data as perform_account_delete
from api.services.crypto import get_crypto_service
from api.services.integration_connections import mark_integration_disconnected
from api.services.strava_tokens import ensure_valid_access_token as ensure_valid_strava_access_token
from services.strava.oauth import STRAVA_DEAUTHORIZE_URL
from services.whoop.oauth import WHOOP_REVOKE_URL

logger = logging.getLogger(__name__)

router = APIRouter()


def _revoke_whoop_access_sync(*, access_token: str) -> None:
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=10.0) as client:
        res = client.delete(WHOOP_REVOKE_URL, headers=headers)
        res.raise_for_status()


def _revoke_strava_access_sync(*, access_token: str) -> None:
    with httpx.Client(timeout=10.0) as client:
        res = client.post(STRAVA_DEAUTHORIZE_URL, data={"access_token": access_token})
        res.raise_for_status()


async def _cancel_inflight_analysis_jobs(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    await db.execute(
        update(AnalysisJob)
        .where(
            AnalysisJob.user_id == user_id,
            AnalysisJob.status.in_(["pending", "running"]),
        )
        .values(cancel_requested_at=datetime.now(tz=UTC))
    )


async def _invalidate_oauth_sessions(db: AsyncSession, *, user_id: uuid.UUID, provider: str) -> None:
    await db.execute(
        delete(OAuthSession).where(
            OAuthSession.user_id == user_id,
            OAuthSession.provider == provider,
        )
    )


@router.post("/strava/disconnect", status_code=202)
async def disconnect_strava(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> dict[str, str]:
    creds = await db.execute(select(StravaCredentials).where(StravaCredentials.user_id == user_id))
    row = creds.scalar_one_or_none()
    if row:
        try:
            access_token = await ensure_valid_strava_access_token(db, user_id=user_id)
            await asyncio.to_thread(_revoke_strava_access_sync, access_token=access_token)
        except Exception:
            logger.warning("Failed to revoke Strava token for user %s", user_id, exc_info=True)
        await db.delete(row)
        await mark_integration_disconnected(db, user_id=user_id, provider="strava", reason="user_initiated")

    await _invalidate_oauth_sessions(db, user_id=user_id, provider="strava")
    await _cancel_inflight_analysis_jobs(db, user_id=user_id)

    return {"status": "disconnected"}


@router.post("/whoop/disconnect", status_code=202)
async def disconnect_whoop(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> dict[str, str]:
    creds = await db.execute(select(WhoopCredentials).where(WhoopCredentials.user_id == user_id))
    row = creds.scalar_one_or_none()
    if row:
        try:
            crypto = get_crypto_service()
            access_token = crypto.decrypt(row.encrypted_access_token)
            await asyncio.to_thread(_revoke_whoop_access_sync, access_token=access_token)
        except Exception:
            logger.warning("Failed to revoke Whoop token for user %s", user_id, exc_info=True)
        await db.delete(row)
        await mark_integration_disconnected(db, user_id=user_id, provider="whoop", reason="user_initiated")
    await _invalidate_oauth_sessions(db, user_id=user_id, provider="whoop")
    await _cancel_inflight_analysis_jobs(db, user_id=user_id)

    return {"status": "disconnected"}


@router.delete("")
async def delete_account_and_data(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> dict[str, str]:
    return await perform_account_delete(db, user_id=user_id)
