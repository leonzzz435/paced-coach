from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol, cast

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.credentials import StravaCredentials, WhoopCredentials
from api.services.strava_tokens import ensure_valid_access_token as ensure_valid_strava_access_token
from api.services.whoop_tokens import ensure_valid_access_token
from services.strava import StravaApiClient
from services.whoop import WhoopApiClient


def _utc_today() -> date:
    return datetime.now(UTC).date()


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _whoop_window_datetimes(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(date_from, time.min, tzinfo=UTC)
    end_dt = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
    return start_dt, end_dt


def _strava_window_timestamps(date_from: date, date_to: date) -> tuple[int, int]:
    start_dt = datetime.combine(date_from, time.min, tzinfo=UTC)
    end_dt = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
    return int(start_dt.timestamp()), int(end_dt.timestamp())


def _strava_activity_date_key(activity: dict) -> str | None:
    raw_start = activity.get("start_date_local") or activity.get("start_date")
    if not isinstance(raw_start, str) or not raw_start.strip():
        return None
    return raw_start[:10]


def _strava_activity_load_value(activity: dict) -> float | None:
    for candidate in (activity.get("relative_effort"), activity.get("suffer_score")):
        parsed = _safe_float(candidate)
        if parsed is not None:
            return parsed
    return None


def _strava_sport_name(activity: dict) -> str:
    return str(activity.get("sport_type") or activity.get("type") or "").strip()


class OngoingTrainingProvider(Protocol):
    async def get_recent_activities(
        self,
        date_from: date,
        date_to: date,
        sport_filters: list[str] | None = None,
    ) -> list[dict]:
        ...

    async def get_training_load_history(self, days: int) -> list[dict]:
        ...

    async def get_recovery_readiness_signals(self, days: int) -> dict:
        ...

    async def get_activity_detail(self, activity_id: int | str) -> dict | None:
        ...


class StravaProvider:
    def __init__(self, *, db: AsyncSession, user_id):
        self._db = db
        self._user_id = user_id
        self._access_token: str | None = None
        self._access_token_error: tuple[int, str] | None = None
        self._access_token_lock = asyncio.Lock()

    async def _get_access_token(self) -> str:
        cached_access_token = self._access_token
        if cached_access_token is not None:
            return cached_access_token
        cached_error = self._access_token_error
        if cached_error is not None:
            status_code, detail = cached_error
            raise HTTPException(status_code=status_code, detail=detail)

        async with self._access_token_lock:
            access_token = self._access_token
            cached_error = self._access_token_error
            if access_token is None and cached_error is None:
                try:
                    access_token = await ensure_valid_strava_access_token(self._db, user_id=self._user_id)
                except HTTPException as exc:
                    detail = str(exc.detail)
                    cached_error = (exc.status_code, detail)
                    self._access_token_error = cached_error
                    raise HTTPException(status_code=exc.status_code, detail=detail) from exc

                self._access_token = access_token

            if access_token is not None:
                return access_token

            status_code, detail = cached_error or (500, "Strava access token could not be resolved.")
            raise HTTPException(status_code=status_code, detail=detail)

    def _list_activities_sync(self, *, access_token: str, after: int, before: int) -> list[dict]:
        client = StravaApiClient(access_token=access_token)
        try:
            activities: list[dict] = []
            page = 1
            per_page = 100
            while True:
                batch = client.list_activities(page=page, per_page=per_page, after=after, before=before)
                if not batch:
                    break
                activities.extend(batch)
                if len(batch) < per_page:
                    break
                page += 1
            return activities
        finally:
            client.close()

    def _get_activity_sync(self, *, access_token: str, activity_id: str) -> dict:
        client = StravaApiClient(access_token=access_token)
        try:
            return client.get_activity(activity_id)
        finally:
            client.close()

    async def get_recent_activities(
        self,
        date_from: date,
        date_to: date,
        sport_filters: list[str] | None = None,
    ) -> list[dict]:
        after, before = _strava_window_timestamps(date_from, date_to)
        access_token = await self._get_access_token()
        activities = await asyncio.to_thread(
            self._list_activities_sync,
            access_token=access_token,
            after=after,
            before=before,
        )

        if not sport_filters:
            return activities

        allowed = {sport.strip().lower() for sport in sport_filters if sport.strip()}
        return [
            activity
            for activity in activities
            if _strava_sport_name(activity).lower() in allowed
        ]

    async def get_training_load_history(self, days: int) -> list[dict]:
        safe_days = max(1, min(days, 180))
        end_date = _utc_today()
        start_date = end_date - timedelta(days=safe_days - 1)
        activities = await self.get_recent_activities(start_date, end_date)

        daily_totals: dict[str, dict[str, object]] = {}
        for activity in activities:
            date_key = _strava_activity_date_key(activity)
            if not date_key:
                continue
            bucket = daily_totals.setdefault(
                date_key,
                {
                    "date": date_key,
                    "activity_count": 0,
                    "relative_effort_total": 0.0,
                    "suffer_score_total": 0.0,
                    "moving_time_minutes_total": 0.0,
                    "distance_m_total": 0.0,
                    "_has_relative_effort": False,
                    "_has_suffer_score": False,
                },
            )
            bucket["activity_count"] = cast("int", bucket["activity_count"]) + 1

            relative_effort = _safe_float(activity.get("relative_effort"))
            if relative_effort is not None:
                bucket["relative_effort_total"] = cast("float", bucket["relative_effort_total"]) + relative_effort
                bucket["_has_relative_effort"] = True

            suffer_score = _safe_float(activity.get("suffer_score"))
            if suffer_score is not None:
                bucket["suffer_score_total"] = cast("float", bucket["suffer_score_total"]) + suffer_score
                bucket["_has_suffer_score"] = True

            moving_time = _safe_float(activity.get("moving_time"))
            if moving_time is not None:
                bucket["moving_time_minutes_total"] = (
                    cast("float", bucket["moving_time_minutes_total"]) + (moving_time / 60.0)
                )

            distance_m = _safe_float(activity.get("distance"))
            if distance_m is not None:
                bucket["distance_m_total"] = cast("float", bucket["distance_m_total"]) + distance_m

        payload: list[dict] = []
        for date_key in sorted(daily_totals.keys()):
            bucket = dict(daily_totals[date_key])
            has_relative_effort = bool(bucket.pop("_has_relative_effort", False))
            has_suffer_score = bool(bucket.pop("_has_suffer_score", False))
            load_value = None
            load_type = "strava_activity_count"
            if has_relative_effort:
                load_value = bucket.get("relative_effort_total")
                load_type = "strava_relative_effort"
            elif has_suffer_score:
                load_value = bucket.get("suffer_score_total")
                load_type = "strava_suffer_score"
            bucket["load_type"] = load_type
            bucket["load_value"] = load_value
            payload.append(bucket)
        return payload

    async def get_recovery_readiness_signals(self, days: int) -> dict:
        safe_days = max(1, min(days, 30))
        end_date = _utc_today()
        start_date = end_date - timedelta(days=safe_days - 1)
        activities = await self.get_recent_activities(start_date, end_date)

        total_distance_m = 0.0
        total_moving_time_seconds = 0.0
        total_relative_effort = 0.0
        total_suffer_score = 0.0
        has_relative_effort = False
        has_suffer_score = False
        for activity in activities:
            distance_m = _safe_float(activity.get("distance"))
            if distance_m is not None:
                total_distance_m += distance_m
            moving_time = _safe_float(activity.get("moving_time"))
            if moving_time is not None:
                total_moving_time_seconds += moving_time
            relative_effort = _safe_float(activity.get("relative_effort"))
            if relative_effort is not None:
                total_relative_effort += relative_effort
                has_relative_effort = True
            suffer_score = _safe_float(activity.get("suffer_score"))
            if suffer_score is not None:
                total_suffer_score += suffer_score
                has_suffer_score = True

        return {
            "window_days": safe_days,
            "as_of_utc": datetime.now(UTC).isoformat(),
            "recent_activities": activities,
            "activity_summary": {
                "activity_count": len(activities),
                "distance_km_total": round(total_distance_m / 1000.0, 2) if total_distance_m else 0.0,
                "moving_time_minutes_total": round(total_moving_time_seconds / 60.0, 1)
                if total_moving_time_seconds
                else 0.0,
                "relative_effort_total": total_relative_effort if has_relative_effort else None,
                "suffer_score_total": total_suffer_score if has_suffer_score else None,
            },
        }

    async def get_activity_detail(self, activity_id: int | str) -> dict | None:
        raw_activity_id = str(activity_id).strip()
        if not raw_activity_id:
            return None
        access_token = await self._get_access_token()
        return await asyncio.to_thread(
            self._get_activity_sync,
            access_token=access_token,
            activity_id=raw_activity_id,
        )


class WhoopProvider:
    def __init__(self, *, db: AsyncSession, user_id):
        self._db = db
        self._user_id = user_id
        self._access_token: str | None = None
        self._access_token_error: tuple[int, str] | None = None
        self._access_token_lock = asyncio.Lock()

    async def _get_access_token(self) -> str:
        cached_access_token = self._access_token
        if cached_access_token is not None:
            return cached_access_token
        cached_error = self._access_token_error
        if cached_error is not None:
            status_code, detail = cached_error
            raise HTTPException(status_code=status_code, detail=detail)

        async with self._access_token_lock:
            access_token = self._access_token
            cached_error = self._access_token_error
            if access_token is None and cached_error is None:
                try:
                    access_token = await ensure_valid_access_token(self._db, user_id=self._user_id)
                except HTTPException as exc:
                    detail = str(exc.detail)
                    cached_error = (exc.status_code, detail)
                    self._access_token_error = cached_error
                    raise HTTPException(status_code=exc.status_code, detail=detail) from exc

                self._access_token = access_token

            if access_token is not None:
                return access_token

            status_code, detail = cached_error or (500, "WHOOP access token could not be resolved.")
            raise HTTPException(status_code=status_code, detail=detail)

    def _list_workouts_sync(self, *, access_token: str, start: datetime, end: datetime) -> list[dict]:
        client = WhoopApiClient(access_token=access_token)
        try:
            return client.list_workouts(start=start, end=end)
        finally:
            client.close()

    def _list_cycles_sync(self, *, access_token: str, start: datetime, end: datetime) -> list[dict]:
        client = WhoopApiClient(access_token=access_token)
        try:
            return client.list_cycles(start=start, end=end)
        finally:
            client.close()

    def _list_recoveries_sync(self, *, access_token: str, start: datetime, end: datetime) -> list[dict]:
        client = WhoopApiClient(access_token=access_token)
        try:
            return client.list_recoveries(start=start, end=end)
        finally:
            client.close()

    def _list_sleeps_sync(self, *, access_token: str, start: datetime, end: datetime) -> list[dict]:
        client = WhoopApiClient(access_token=access_token)
        try:
            return client.list_sleeps(start=start, end=end)
        finally:
            client.close()

    def _get_workout_sync(self, *, access_token: str, workout_id: str) -> dict:
        client = WhoopApiClient(access_token=access_token)
        try:
            return client.get_workout(workout_id)
        finally:
            client.close()

    async def get_recent_activities(
        self,
        date_from: date,
        date_to: date,
        sport_filters: list[str] | None = None,
    ) -> list[dict]:
        start_dt, end_dt = _whoop_window_datetimes(date_from, date_to)
        access_token = await self._get_access_token()
        workouts = await asyncio.to_thread(
            self._list_workouts_sync,
            access_token=access_token,
            start=start_dt,
            end=end_dt,
        )

        if not sport_filters:
            return workouts

        allowed = {sport.strip().lower() for sport in sport_filters if sport.strip()}
        return [
            workout
            for workout in workouts
            if str(workout.get("sport_name", "")).strip().lower() in allowed
        ]

    async def get_training_load_history(self, days: int) -> list[dict]:
        safe_days = max(1, min(days, 180))
        end_date = _utc_today()
        start_date = end_date - timedelta(days=safe_days - 1)
        start_dt, end_dt = _whoop_window_datetimes(start_date, end_date)
        access_token = await self._get_access_token()
        return await asyncio.to_thread(
            self._list_cycles_sync,
            access_token=access_token,
            start=start_dt,
            end=end_dt,
        )

    async def get_recovery_readiness_signals(self, days: int) -> dict:
        safe_days = max(1, min(days, 30))
        end_date = _utc_today()
        start_date = end_date - timedelta(days=safe_days - 1)
        start_dt, end_dt = _whoop_window_datetimes(start_date, end_date)
        access_token = await self._get_access_token()

        recoveries, sleeps, cycles = await asyncio.gather(
            asyncio.to_thread(self._list_recoveries_sync, access_token=access_token, start=start_dt, end=end_dt),
            asyncio.to_thread(self._list_sleeps_sync, access_token=access_token, start=start_dt, end=end_dt),
            asyncio.to_thread(self._list_cycles_sync, access_token=access_token, start=start_dt, end=end_dt),
        )

        return {
            "window_days": safe_days,
            "as_of_utc": datetime.now(UTC).isoformat(),
            "recoveries": recoveries,
            "sleeps": sleeps,
            "cycles": cycles,
        }

    async def get_activity_detail(self, activity_id: int | str) -> dict | None:
        workout_id = str(activity_id).strip()
        if not workout_id:
            return None
        access_token = await self._get_access_token()
        return await asyncio.to_thread(self._get_workout_sync, access_token=access_token, workout_id=workout_id)


async def build_ongoing_strava_provider(db: AsyncSession, *, user_id) -> OngoingTrainingProvider:
    creds_row = await db.execute(select(StravaCredentials).where(StravaCredentials.user_id == user_id))
    creds = creds_row.scalar_one_or_none()
    if not creds:
        raise HTTPException(status_code=404, detail="Strava credentials not configured")
    return StravaProvider(db=db, user_id=user_id)


async def build_ongoing_whoop_provider(db: AsyncSession, *, user_id) -> OngoingTrainingProvider:
    creds_row = await db.execute(select(WhoopCredentials).where(WhoopCredentials.user_id == user_id))
    creds = creds_row.scalar_one_or_none()
    if not creds:
        raise HTTPException(status_code=404, detail="WHOOP credentials not configured")
    return WhoopProvider(db=db, user_id=user_id)
