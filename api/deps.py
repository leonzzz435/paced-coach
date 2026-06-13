import uuid
from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import get_settings
from api.models.active_analysis import ActiveAnalysis
from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.athlete_profile import AthleteProfile
from api.models.competition import Competition
from api.models.credentials import StravaCredentials, WhoopCredentials
from api.models.integration_connection import IntegrationConnection
from api.models.user import User

settings = get_settings()
DB_SKIP_AUTO_COMMIT_FLAG = "skip_auto_commit"
_LOCAL_AUTH_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "testserver", "api"}
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

engine = create_async_engine(settings.database_url_async, echo=settings.debug)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        try:
            yield session
            if session.info.get(DB_SKIP_AUTO_COMMIT_FLAG):
                return
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _hostname_from_header(raw_host: str | None) -> str:
    if not raw_host:
        return ""
    return urlparse(f"//{raw_host.strip()}").hostname or raw_host.strip().split(":", 1)[0]


def _is_local_request_host(raw_host: str | None) -> bool:
    host = _hostname_from_header(raw_host).lower()
    if not host:
        return True
    return host in _LOCAL_AUTH_ALLOWED_HOSTS


def _origin_matches_request_host(origin: str, request_host: str | None) -> bool:
    origin_host = urlparse(origin).hostname or ""
    if not origin_host:
        return False
    request_hostname = _hostname_from_header(request_host)
    return origin_host.lower() == request_hostname.lower()


def _local_auth_context_is_safe() -> bool:
    if bool(getattr(settings, "allow_local_auth_public_access", False)):
        return True
    configured_safe = getattr(settings, "local_auth_context_is_safe", None)
    if isinstance(configured_safe, bool):
        return configured_safe
    app_env = str(getattr(settings, "app_env", "local") or "local").strip().lower()
    return app_env not in {"prod", "production", "staging", "preview"}


def _assert_local_auth_request_allowed(request: Request):
    if not _local_auth_context_is_safe():
        raise HTTPException(
            status_code=500,
            detail="Local auth is not allowed for this deployment context. Use localhost or explicitly opt in to public local auth.",
        )

    request_host = request.headers.get("host")
    if not _is_local_request_host(request_host):
        raise HTTPException(status_code=403, detail="Local auth only accepts localhost requests.")

    request_method = str(request.scope.get("method") or "GET").upper()
    if request_method not in _MUTATING_METHODS:
        return

    origin = request.headers.get("origin")
    if origin and not _origin_matches_request_host(origin, request_host):
        raise HTTPException(status_code=403, detail="Cross-origin local write request rejected.")


def _auth_mode() -> str:
    mode = str(getattr(settings, "auth_mode", "local") or "local").strip().lower()
    if mode != "local":
        raise HTTPException(status_code=500, detail="Invalid AUTH_MODE. Expected 'local'.")
    return "local"


def _local_owner_user_id() -> uuid.UUID | None:
    raw_user_id = str(getattr(settings, "local_owner_user_id", "") or "").strip()
    if not raw_user_id:
        return None
    try:
        return uuid.UUID(raw_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="Invalid LOCAL_OWNER_USER_ID. Set it to an existing users.id UUID or unset it for a fresh local owner.",
        ) from exc


def _local_owner_key() -> str:
    return str(getattr(settings, "local_owner_key", "") or "local-owner").strip() or "local-owner"


def _local_owner_email() -> str:
    return str(getattr(settings, "local_owner_email", "") or "local-owner@paced.local").strip() or "local-owner@paced.local"


async def _find_single_existing_training_owner(db: AsyncSession) -> uuid.UUID | None:
    owner_ids: set[uuid.UUID] = set()
    for model in (
        ActiveAnalysis,
        ActiveSeasonPlan,
        ActiveWeeklyPlan,
        AthleteProfile,
        Competition,
        IntegrationConnection,
        StravaCredentials,
        WhoopCredentials,
    ):
        rows = await db.execute(select(model.user_id).distinct())
        owner_ids.update(owner_id for owner_id in rows.scalars().all() if owner_id is not None)

    if not owner_ids:
        return None
    if len(owner_ids) == 1:
        return next(iter(owner_ids))
    raise HTTPException(
        status_code=500,
        detail=(
            "Multiple existing users have local training data. Set LOCAL_OWNER_USER_ID to the users.id that should "
            "own this local app session."
        ),
    )


async def _get_or_create_local_owner(db: AsyncSession) -> uuid.UUID:
    configured_user_id = _local_owner_user_id()
    if configured_user_id is not None:
        result = await db.execute(select(User).where(User.id == configured_user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=500,
                detail="LOCAL_OWNER_USER_ID does not match an existing user. Fix the value or unset it for a fresh local owner.",
            )
        return user.id

    existing_training_owner_id = await _find_single_existing_training_owner(db)
    local_owner_key = _local_owner_key()
    result = await db.execute(select(User).where(User.local_owner_key == local_owner_key))
    user = result.scalar_one_or_none()
    if user is not None:
        if existing_training_owner_id is not None and user.id != existing_training_owner_id:
            return existing_training_owner_id
        return user.id
    if existing_training_owner_id is not None:
        return existing_training_owner_id

    local_email = _local_owner_email()
    email_result = await db.execute(select(User).where(User.email == local_email))
    existing_email_user = email_result.scalar_one_or_none()
    if existing_email_user is not None:
        raise HTTPException(
            status_code=500,
            detail="LOCAL_OWNER_EMAIL already belongs to another user. Set LOCAL_OWNER_USER_ID to that existing users.id.",
        )

    user = User(email=local_email, local_owner_key=local_owner_key)
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        retry_result = await db.execute(select(User).where(User.local_owner_key == local_owner_key))
        existing_user = retry_result.scalar_one_or_none()
        if existing_user is None:
            raise
        return existing_user.id
    return user.id


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    _auth_mode()
    _assert_local_auth_request_allowed(request)
    return await _get_or_create_local_owner(db)
