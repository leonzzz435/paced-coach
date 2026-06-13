from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

_DEFAULT_BASE_URL = "https://api.prod.whoop.com/developer"


def _iso_datetime(value: datetime) -> str:
    # WHOOP uses RFC3339/ISO8601 timestamps (e.g. "...Z").
    return value.isoformat()


class WhoopApiClient:
    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = _DEFAULT_BASE_URL,
        client: httpx.Client | None = None,
        timeout_s: float = 20.0,
        user_agent: str = "paced-coach/1.0",
    ):
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._owned_client = client is None
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": user_agent,
        }
        self._client = client or httpx.Client(base_url=self._base_url, headers=headers, timeout=timeout_s)

    def close(self) -> None:
        if self._owned_client:
            self._client.close()

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict:
        res = self._client.get(path, params=params)
        res.raise_for_status()
        payload = res.json()
        if not isinstance(payload, dict):
            raise TypeError("WHOOP API returned a non-object JSON payload")
        return payload

    def _paginate(self, path: str, *, params: dict[str, Any] | None = None) -> list[dict]:
        collected: list[dict] = []
        next_token: str | None = None
        base_params = dict(params or {})
        base_params.setdefault("limit", 25)

        while True:
            request_params = dict(base_params)
            if next_token:
                # WHOOP APIs vary between `nextToken` and `next_token` in the wild.
                # Send both to be tolerant; the server will ignore the unknown key.
                request_params["nextToken"] = next_token
                request_params["next_token"] = next_token
            page = self._get(path, params=request_params)
            records = page.get("records")
            if isinstance(records, list):
                collected.extend([item for item in records if isinstance(item, dict)])
            token = page.get("next_token") or page.get("nextToken")
            next_token = token if isinstance(token, str) and token else None
            if not next_token:
                return collected

    def get_basic_profile(self) -> dict:
        return self._get("/v2/user/profile/basic")

    def get_body_measurement(self) -> dict:
        return self._get("/v2/user/measurement/body")

    def list_workouts(self, *, start: datetime | None = None, end: datetime | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = _iso_datetime(start)
        if end is not None:
            params["end"] = _iso_datetime(end)
        return self._paginate("/v2/activity/workout", params=params)

    def get_workout(self, workout_id: str) -> dict:
        return self._get(f"/v2/activity/workout/{workout_id}")

    def list_sleeps(self, *, start: datetime | None = None, end: datetime | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = _iso_datetime(start)
        if end is not None:
            params["end"] = _iso_datetime(end)
        return self._paginate("/v2/activity/sleep", params=params)

    def get_sleep(self, sleep_id: str) -> dict:
        return self._get(f"/v2/activity/sleep/{sleep_id}")

    def list_cycles(self, *, start: datetime | None = None, end: datetime | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = _iso_datetime(start)
        if end is not None:
            params["end"] = _iso_datetime(end)
        return self._paginate("/v2/cycle", params=params)

    def get_cycle(self, cycle_id: int | str) -> dict:
        return self._get(f"/v2/cycle/{cycle_id}")

    def list_recoveries(self, *, start: datetime | None = None, end: datetime | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = _iso_datetime(start)
        if end is not None:
            params["end"] = _iso_datetime(end)
        return self._paginate("/v2/recovery", params=params)
