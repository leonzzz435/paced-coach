from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_DEAUTHORIZE_URL = "https://www.strava.com/oauth/deauthorize"
STRAVA_API_BASE_URL = "https://www.strava.com/api/v3"

_DEFAULT_EXPIRY_SECONDS = 21600


def compute_expires_at(*, now: datetime, expires_at: Any, expires_in: Any) -> datetime:
    try:
        epoch_seconds = int(expires_at)
    except (TypeError, ValueError):
        epoch_seconds = 0
    if epoch_seconds > 0:
        return datetime.fromtimestamp(epoch_seconds, tz=UTC)

    try:
        lifetime_seconds = int(expires_in)
    except (TypeError, ValueError):
        lifetime_seconds = _DEFAULT_EXPIRY_SECONDS
    return now + timedelta(seconds=max(0, lifetime_seconds))


def build_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    scope: str,
    approval_prompt: str = "auto",
) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "approval_prompt": approval_prompt,
            "scope": scope,
            "state": state,
        }
    )
    return f"{STRAVA_AUTHORIZE_URL}?{query}"


def exchange_code_for_tokens(
    *,
    code: str,
    client_id: str,
    client_secret: str,
) -> dict:
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(STRAVA_TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json()


def refresh_tokens(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict:
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(STRAVA_TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json()
