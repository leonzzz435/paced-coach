from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError

from api.models.integration_connection import IntegrationConnection

_SUPPORTED_PROVIDERS = {"strava", "whoop"}
_MISSING_HISTORY_TABLE_SQLSTATE = "42P01"

logger = logging.getLogger(__name__)

_missing_history_table_warning_state = {"emitted": False}


def _normalize_provider(provider: str) -> str:
    normalized = str(provider or "").strip().lower()
    if normalized not in _SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    return normalized


def _is_missing_history_table_error(error: ProgrammingError) -> bool:
    original_error = getattr(error, "orig", None)
    sqlstate = getattr(original_error, "sqlstate", None) or getattr(original_error, "pgcode", None)
    if sqlstate == _MISSING_HISTORY_TABLE_SQLSTATE:
        return True
    return 'relation "integration_connections" does not exist' in str(original_error or error).lower()


def _warn_missing_history_table_once():
    if _missing_history_table_warning_state["emitted"]:
        return
    logger.warning(
        "Integration connection history table is unavailable; falling back to empty history until migrations are applied."
    )
    _missing_history_table_warning_state["emitted"] = True


async def get_connection_history_map(db, *, user_id: uuid.UUID) -> dict[str, IntegrationConnection]:
    try:
        rows = await db.execute(select(IntegrationConnection).where(IntegrationConnection.user_id == user_id))
    except ProgrammingError as error:
        if not _is_missing_history_table_error(error):
            raise
        _warn_missing_history_table_once()
        return {}
    return {row.provider: row for row in rows.scalars().all()}


async def mark_integration_connected(
    db,
    *,
    user_id: uuid.UUID,
    provider: str,
    connected_at: datetime | None = None,
):
    normalized_provider = _normalize_provider(provider)
    resolved_connected_at = connected_at.astimezone(UTC) if connected_at is not None else datetime.now(UTC)
    try:
        row = await db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.user_id == user_id,
                IntegrationConnection.provider == normalized_provider,
            )
        )
    except ProgrammingError as error:
        if not _is_missing_history_table_error(error):
            raise
        _warn_missing_history_table_once()
        return
    history = row.scalar_one_or_none()
    if history is None:
        db.add(
            IntegrationConnection(
                user_id=user_id,
                provider=normalized_provider,
                first_connected_at=resolved_connected_at,
                last_connected_at=resolved_connected_at,
                last_disconnected_at=None,
                last_disconnect_reason=None,
            )
        )
        await db.flush()
        return

    history.last_connected_at = resolved_connected_at
    history.last_disconnected_at = None
    history.last_disconnect_reason = None
    db.add(history)
    await db.flush()


async def mark_integration_disconnected(
    db,
    *,
    user_id: uuid.UUID,
    provider: str,
    reason: str,
    disconnected_at: datetime | None = None,
):
    normalized_provider = _normalize_provider(provider)
    resolved_disconnected_at = (
        disconnected_at.astimezone(UTC) if disconnected_at is not None else datetime.now(UTC)
    )
    try:
        row = await db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.user_id == user_id,
                IntegrationConnection.provider == normalized_provider,
            )
        )
    except ProgrammingError as error:
        if not _is_missing_history_table_error(error):
            raise
        _warn_missing_history_table_once()
        return
    history = row.scalar_one_or_none()
    if history is None:
        db.add(
            IntegrationConnection(
                user_id=user_id,
                provider=normalized_provider,
                first_connected_at=resolved_disconnected_at,
                last_connected_at=resolved_disconnected_at,
                last_disconnected_at=resolved_disconnected_at,
                last_disconnect_reason=reason,
            )
        )
        await db.flush()
        return

    history.last_disconnected_at = resolved_disconnected_at
    history.last_disconnect_reason = str(reason or "").strip() or None
    db.add(history)
    await db.flush()
