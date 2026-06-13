from __future__ import annotations

from typing import Any

import httpx

_DEFAULT_BASE_URL = "https://www.strava.com/api/v3"


class StravaApiClient:
    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = _DEFAULT_BASE_URL,
        client: httpx.Client | None = None,
        timeout_s: float = 20.0,
        user_agent: str = "paced-coach/1.0",
    ):
        self._owned_client = client is None
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": user_agent,
            },
            timeout=timeout_s,
        )

    def close(self) -> None:
        if self._owned_client:
            self._client.close()

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict | list[dict]:
        response = self._client.get(path, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, (dict, list)):
            raise TypeError("Strava API returned an unexpected JSON payload")
        return payload

    def get_logged_in_athlete(self) -> dict:
        payload = self._get("/athlete")
        if not isinstance(payload, dict):
            raise TypeError("Strava athlete endpoint returned a non-object payload")
        return payload

    def list_activities(self, *, page: int = 1, per_page: int = 30, before: int | None = None, after: int | None = None) -> list[dict]:
        params: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
        }
        if before is not None:
            params["before"] = before
        if after is not None:
            params["after"] = after
        payload = self._get("/athlete/activities", params=params)
        if not isinstance(payload, list):
            raise TypeError("Strava activities endpoint returned a non-list payload")
        return [item for item in payload if isinstance(item, dict)]

    def get_activity(self, activity_id: int | str) -> dict:
        payload = self._get(f"/activities/{activity_id}")
        if not isinstance(payload, dict):
            raise TypeError("Strava activity endpoint returned a non-object payload")
        return payload
