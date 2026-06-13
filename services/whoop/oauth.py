from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

WHOOP_BASE_URL = "https://api.prod.whoop.com"
WHOOP_AUTHORIZE_URL = f"{WHOOP_BASE_URL}/oauth/oauth2/auth"
WHOOP_TOKEN_URL = f"{WHOOP_BASE_URL}/oauth/oauth2/token"
WHOOP_PROFILE_URL = f"{WHOOP_BASE_URL}/developer/v2/user/profile/basic"
WHOOP_REVOKE_URL = f"{WHOOP_BASE_URL}/developer/v2/user/access"

_TOKEN_EXPIRY_BUFFER_SECONDS = 30
_DEFAULT_EXPIRY_SECONDS = 1800


def compute_expires_at(*, now: datetime, expires_in: Any) -> datetime:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        seconds = _DEFAULT_EXPIRY_SECONDS
    safe_seconds = max(0, seconds - _TOKEN_EXPIRY_BUFFER_SECONDS)
    return now + timedelta(seconds=safe_seconds)


def build_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    scope: str,
) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": scope,
        }
    )
    return f"{WHOOP_AUTHORIZE_URL}?{query}"


def exchange_code_for_tokens(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    with httpx.Client(timeout=20.0) as client:
        res = client.post(WHOOP_TOKEN_URL, data=payload)
        res.raise_for_status()
        return res.json()


def refresh_tokens(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    scope: str = "offline",
) -> dict:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
    }
    with httpx.Client(timeout=20.0) as client:
        res = client.post(WHOOP_TOKEN_URL, data=payload)
        res.raise_for_status()
        return res.json()

