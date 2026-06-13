from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from statistics import mean
from time import perf_counter
from typing import Literal, cast

from fastapi import HTTPException
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.active_analysis import ActiveAnalysis
from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.competition import Competition
from api.models.user import User
from api.services.coach_memory_metadata import derive_memory_freshness, extract_transient_state_notes
from api.services.evidence_profile import build_evidence_profile, build_evidence_sources
from api.services.ongoing_providers import (
    OngoingTrainingProvider,
    build_ongoing_strava_provider,
    build_ongoing_whoop_provider,
)


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _extract_load(entry: dict) -> float | None:
    candidates = (
        entry.get("load"),
        entry.get("training_load"),
        entry.get("trainingLoad"),
        entry.get("daily_training_load"),
        entry.get("dailyTrainingLoad"),
        entry.get("load_value"),
    )
    for candidate in candidates:
        parsed = _safe_float(candidate)
        if parsed is not None:
            return parsed
    return None


def _normalize_activity_id(activity_id: object) -> str | None:
    if activity_id is None:
        return None
    value = str(activity_id).strip()
    return value if value else None


def _activity_date(activity: dict) -> date | None:
    raw_start = activity.get("start_time") or activity.get("startTime")
    if not isinstance(raw_start, str):
        return None
    trimmed = raw_start.strip()
    if not trimmed:
        return None
    try:
        return date.fromisoformat(trimmed[:10])
    except ValueError:
        return None


def nearest_competition_days(competitions: list[dict], today: date) -> int | None:
    nearest: int | None = None
    for competition in competitions:
        raw_date = competition.get("date")
        if not isinstance(raw_date, str) or not raw_date:
            continue
        try:
            comp_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            continue
        delta = (comp_date - today).days
        if delta >= 0 and (nearest is None or delta < nearest):
            nearest = delta
    return nearest


def _staleness_label(age_days: int | None) -> str:
    if age_days is None:
        return "unknown"
    if age_days <= 7:
        return "fresh"
    if age_days <= 14:
        return "moderate"
    return "stale"


class OngoingToolRegistry:
    def __init__(
        self,
        *,
        db: AsyncSession,
        user_id,
        providers: dict[str, OngoingTrainingProvider],
    ):
        self._db = db
        self._user_id = user_id
        self._providers = providers
        self._request_cache: dict[str, object] = {}
        self._tool_usage: dict[str, dict[str, float | int]] = {}
        self._activity_index: dict[str, dict] = {}
        self._provider_runtime_status: dict[str, dict[str, object]] = {
            name: {
                "kind": type(provider).__name__,
                "available": True,
                "last_error": None,
                "status_code": None,
            }
            for name, provider in providers.items()
        }

    def _provider_observability(self) -> dict:
        snapshot: dict[str, dict[str, object]] = dict(self._provider_runtime_status)
        # Include known providers even when disconnected so the agent can reason about gaps.
        for name in ("strava", "whoop"):
            snapshot.setdefault(
                name,
                {
                    "kind": None,
                    "available": False,
                    "last_error": None,
                    "status_code": None,
                },
            )
        evidence_sources = build_evidence_sources(provider_status=snapshot)
        for name, evidence_source in evidence_sources.items():
            entry = snapshot.setdefault(
                name,
                {
                    "kind": None,
                    "available": False,
                    "last_error": None,
                    "status_code": None,
                },
            )
            entry["operational"] = evidence_source["operational"]
            entry["capabilities"] = evidence_source["capabilities"]
        return {"training_providers": snapshot}

    def _current_evidence_profile(self) -> dict[str, object]:
        provider_status = self._provider_observability()["training_providers"]
        return build_evidence_profile(provider_status=provider_status)

    @staticmethod
    def _degraded_provider_error(exc: BaseException) -> HTTPException | None:
        if isinstance(exc, HTTPException) and exc.status_code in {401, 404, 409, 502, 503}:
            return exc
        return None

    def _mark_provider_unavailable(self, *, source_name: str, exc: HTTPException):
        provider = self._providers.get(source_name)
        self._provider_runtime_status[source_name] = {
            "kind": type(provider).__name__ if provider is not None else None,
            "available": False,
            "last_error": str(exc.detail),
            "status_code": exc.status_code,
        }

    async def _measure(self, name: str, call):
        start = perf_counter()
        result = await call()
        elapsed_ms = (perf_counter() - start) * 1000.0

        current = self._tool_usage.get(name)
        if current:
            current["count"] = int(current["count"]) + 1
            current["total_ms"] = float(current["total_ms"]) + elapsed_ms
        else:
            self._tool_usage[name] = {"count": 1, "total_ms": elapsed_ms}
        return result

    def _get_cached(self, cache_key: str) -> object | None:
        return self._request_cache.get(cache_key)

    def _set_cached(self, cache_key: str, value: object):
        self._request_cache[cache_key] = value

    def _index_activities(self, activities: list[dict]):
        for activity in activities:
            key = _normalize_activity_id(activity.get("activity_id"))
            if key is not None:
                self._activity_index[key] = activity

    def _activity_source_id(self, *, source_name: str, item: dict) -> object | None:
        if source_name == "strava":
            return item.get("id") or item.get("activity_id") or item.get("activityId")
        if source_name == "whoop":
            return item.get("id") or item.get("activity_id") or item.get("activityId")
        return item.get("id") or item.get("activity_id") or item.get("activityId")

    def _apply_strava_activity_defaults(self, payload: dict) -> None:
        payload.setdefault("start_time", payload.get("start_date_local") or payload.get("start_date"))
        payload.setdefault("activity_type", payload.get("sport_type") or payload.get("type"))
        payload.setdefault("activity_name", payload.get("name"))

    def _apply_whoop_activity_defaults(self, payload: dict) -> None:
        payload.setdefault("start_time", payload.get("start"))
        payload.setdefault("activity_type", payload.get("sport_name"))
        payload.setdefault("activity_name", payload.get("sport_name"))

    def _enrich_recent_activity_item(self, *, source_name: str, item: dict) -> dict | None:
        raw_id = self._activity_source_id(source_name=source_name, item=item)
        if raw_id is None:
            return None
        composite_id = f"{source_name}:{raw_id}"
        payload = dict(item)
        payload["source"] = source_name
        payload["source_activity_id"] = raw_id
        payload["activity_id"] = composite_id
        if source_name == "strava":
            self._apply_strava_activity_defaults(payload)
        if source_name == "whoop":
            self._apply_whoop_activity_defaults(payload)
        return payload

    async def _load_recent_activities_one(
        self,
        *,
        source_name: str,
        provider: OngoingTrainingProvider,
        date_from: date,
        date_to: date,
        sport_filters: list[str] | None,
    ) -> list[dict]:
        raw_items = await provider.get_recent_activities(date_from, date_to, sport_filters)
        enriched: list[dict] = []
        for item in raw_items:
            payload = self._enrich_recent_activity_item(source_name=source_name, item=item)
            if payload is not None:
                enriched.append(payload)
        return enriched

    async def _load_recent_activities_merged(
        self,
        *,
        date_from: date,
        date_to: date,
        sport_filters: list[str] | None,
    ) -> list[dict]:
        if not self._providers:
            return []
        provider_entries = list(self._providers.items())
        tasks = [
            self._load_recent_activities_one(
                source_name=source_name,
                provider=provider,
                date_from=date_from,
                date_to=date_to,
                sport_filters=sport_filters,
            )
            for source_name, provider in provider_entries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: list[dict] = []
        for (source_name, _provider), batch in zip(provider_entries, results, strict=True):
            if isinstance(batch, BaseException):
                degraded_error = self._degraded_provider_error(batch)
                if degraded_error is not None:
                    self._mark_provider_unavailable(source_name=source_name, exc=degraded_error)
                    continue
                raise batch
            merged.extend(batch)
        return merged

    def _parse_activity_id(self, activity_id: int | str) -> tuple[str, str, str] | None:
        raw_value = _normalize_activity_id(activity_id)
        if raw_value is None:
            return None

        if ":" not in raw_value:
            return None
        source_name, _, raw_id = raw_value.partition(":")
        source_name = source_name.strip().lower()
        raw_id = raw_id.strip()

        if not raw_id:
            return None

        composite_id = f"{source_name}:{raw_id}"
        return source_name, raw_id, composite_id

    def _enrich_activity_detail_payload(self, *, source_name: str, raw_id: str, payload: dict) -> dict:
        enriched = dict(payload)
        enriched["source"] = source_name
        enriched["source_activity_id"] = raw_id
        enriched["activity_id"] = f"{source_name}:{raw_id}"
        if source_name == "strava":
            self._apply_strava_activity_defaults(enriched)
        if source_name == "whoop":
            self._apply_whoop_activity_defaults(enriched)
        return enriched

    def _whoop_cycle_day(self, payload: dict) -> str | None:
        start = payload.get("start")
        if not isinstance(start, str) or not start.strip():
            return None
        return start[:10]

    def _enrich_training_load_item(self, *, source_name: str, item: dict) -> dict:
        payload = dict(item)
        payload["source"] = source_name

        if source_name == "strava":
            payload["load_type"] = str(payload.get("load_type") or "strava_relative_effort")
            payload["load_value"] = (
                _safe_float(payload.get("load_value"))
                or _safe_float(payload.get("relative_effort_total"))
                or _safe_float(payload.get("suffer_score_total"))
            )
            return payload

        if source_name == "whoop":
            score = payload.get("score") if isinstance(payload.get("score"), dict) else {}
            strain = _safe_float(score.get("strain")) if isinstance(score, dict) else None
            payload["date"] = payload.get("date") or self._whoop_cycle_day(payload)
            payload["load_type"] = "whoop_strain_0_21"
            payload["load_value"] = strain
            return payload

        return payload

    async def _load_training_load_history_one(
        self,
        *,
        source_name: str,
        provider: OngoingTrainingProvider,
        days: int,
    ) -> list[dict]:
        raw_items = await provider.get_training_load_history(days)
        enriched: list[dict] = []
        for item in raw_items:
            payload = self._enrich_training_load_item(source_name=source_name, item=item)
            enriched.append(payload)
        enriched.sort(key=lambda row: str(row.get("date") or ""))
        return enriched

    async def _load_training_load_history_merged(self, *, days: int) -> list[dict]:
        if not self._providers:
            return []
        provider_entries = list(self._providers.items())
        tasks = [
            self._load_training_load_history_one(source_name=source_name, provider=provider, days=days)
            for source_name, provider in provider_entries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: list[dict] = []
        for (source_name, _provider), batch in zip(provider_entries, results, strict=True):
            if isinstance(batch, BaseException):
                degraded_error = self._degraded_provider_error(batch)
                if degraded_error is not None:
                    self._mark_provider_unavailable(source_name=source_name, exc=degraded_error)
                    continue
                raise batch
            merged.extend(batch)
        merged.sort(key=lambda row: (str(row.get("date") or ""), str(row.get("source") or "")))
        return merged

    def _to_strava_activity_summary(self, activity: dict) -> dict:
        raw_duration = _safe_float(activity.get("moving_time")) or _safe_float(activity.get("elapsed_time"))
        raw_distance = _safe_float(activity.get("distance"))
        activity_date = _activity_date(activity)
        average_power = (
            activity.get("average_watts")
            or activity.get("weighted_average_watts")
            or activity.get("average_speed")
        )

        return {
            "source": "strava",
            "activity_id": activity.get("activity_id"),
            "source_activity_id": activity.get("source_activity_id"),
            "date": activity_date.isoformat() if activity_date else None,
            "activity_type": activity.get("activity_type") or activity.get("activityType"),
            "activity_name": activity.get("activity_name") or activity.get("activityName"),
            "duration_min": round(raw_duration / 60.0, 1) if raw_duration is not None else None,
            "distance_km": round(raw_distance / 1000.0, 2) if raw_distance is not None else None,
            "elevation_gain_m": _safe_float(activity.get("total_elevation_gain")),
            "average_hr": activity.get("average_heartrate"),
            "average_pace_or_power": average_power,
            "relative_effort": activity.get("relative_effort"),
            "suffer_score": activity.get("suffer_score"),
        }

    def _to_whoop_workout_summary(self, workout: dict) -> dict:
        start = workout.get("start")
        end = workout.get("end")
        workout_date = None
        if isinstance(start, str) and start.strip():
            try:
                workout_date = date.fromisoformat(start[:10])
            except ValueError:
                workout_date = None

        duration_min = None
        if isinstance(start, str) and isinstance(end, str) and start and end:
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                duration_min = round((end_dt - start_dt).total_seconds() / 60.0, 1)
            except ValueError:
                duration_min = None

        score_raw = workout.get("score")
        score: dict = score_raw if isinstance(score_raw, dict) else {}
        distance_m = _safe_float(score.get("distance_meter"))
        distance_km = round(distance_m / 1000.0, 2) if distance_m is not None else None

        return {
            "source": "whoop",
            "activity_id": workout.get("activity_id"),
            "source_activity_id": workout.get("source_activity_id"),
            "date": workout_date.isoformat() if workout_date else None,
            "activity_type": workout.get("sport_name"),
            "activity_name": workout.get("sport_name"),
            "duration_min": duration_min,
            "distance_km": distance_km,
            "average_hr": score.get("average_heart_rate"),
            "whoop_strain": score.get("strain"),
        }

    async def _load_active_analysis(self) -> ActiveAnalysis | None:
        cache_key = "active_analysis_row"
        cached = self._request_cache.get(cache_key)
        if isinstance(cached, ActiveAnalysis) or cached is None:
            if cache_key in self._request_cache:
                return cached

        async def _load():
            row = await self._db.execute(select(ActiveAnalysis).where(ActiveAnalysis.user_id == self._user_id))
            return row.scalar_one_or_none()

        result = await self._measure("get_active_analysis", _load)
        self._request_cache[cache_key] = result
        return result

    async def get_current_weekly_plan(self) -> dict:
        cache_key = "current_weekly_plan"
        cached = self._request_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        async def _load():
            row = await self._db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == self._user_id))
            plan = row.scalar_one_or_none()
            if not plan:
                return {}
            payload = dict(plan.plan_data or {})
            payload["version"] = plan.version
            payload["updated_at"] = plan.updated_at.isoformat()
            return payload

        result = await self._measure("get_current_weekly_plan", _load)
        self._request_cache[cache_key] = result
        return result

    async def get_current_season_plan(self) -> dict:
        cache_key = "current_season_plan"
        cached = self._request_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        async def _load():
            row = await self._db.execute(select(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == self._user_id))
            plan = row.scalar_one_or_none()
            if not plan:
                return {}
            payload = dict(plan.plan_data or {})
            payload["version"] = plan.version
            payload["updated_at"] = plan.updated_at.isoformat()
            return payload

        result = await self._measure("get_current_season_plan", _load)
        self._request_cache[cache_key] = result
        return result

    async def get_current_analysis(self) -> dict:
        cache_key = "current_analysis"
        cached = self._request_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        cached_row = self._request_cache.get("active_analysis_row")
        if isinstance(cached_row, ActiveAnalysis):
            payload = dict(cached_row.analysis_data or {})
            payload["version"] = cached_row.version
            payload["updated_at"] = cached_row.updated_at.isoformat()
            self._request_cache[cache_key] = payload
            return payload
        if "active_analysis_row" in self._request_cache and cached_row is None:
            self._request_cache[cache_key] = {}
            return {}

        async def _load():
            row = await self._db.execute(select(ActiveAnalysis).where(ActiveAnalysis.user_id == self._user_id))
            analysis = row.scalar_one_or_none()
            self._request_cache["active_analysis_row"] = analysis
            if not analysis:
                return {}
            payload = dict(analysis.analysis_data or {})
            payload["version"] = analysis.version
            payload["updated_at"] = analysis.updated_at.isoformat()
            return payload

        result = await self._measure("get_current_analysis", _load)
        self._request_cache[cache_key] = result
        return result

    async def get_upcoming_competitions(self) -> list[dict]:
        cache_key = "upcoming_competitions"
        cached = self._request_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        async def _load():
            row = await self._db.execute(
                select(Competition)
                .where(Competition.user_id == self._user_id)
                .order_by(Competition.date.asc().nullslast(), Competition.created_at.asc())
            )
            competitions = row.scalars().all()
            return [
                {
                    "id": str(comp.id),
                    "name": comp.name,
                    "date": comp.date.isoformat() if comp.date else None,
                    "date_text": comp.date_text,
                    "race_type": comp.race_type,
                    "priority": comp.priority,
                    "target_time": comp.target_time,
                    "notes": comp.notes,
                }
                for comp in competitions
            ]

        result = await self._measure("get_upcoming_competitions", _load)
        self._request_cache[cache_key] = result
        return result

    async def get_athlete_profile(self) -> dict:
        cache_key = "athlete_profile"
        cached = self._request_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        async def _load():
            row = await self._db.execute(select(User).where(User.id == self._user_id))
            user = row.scalar_one_or_none()
            if user is None:
                return {
                    "memory_summary": "",
                    "athlete_model": {},
                    "transient_state_notes": [],
                    "memory_updated_at": None,
                    "memory_age_days": None,
                }
            athlete_model = user.athlete_model or {}
            memory_updated_at, memory_age_days = derive_memory_freshness(athlete_model, now=datetime.now(UTC))
            transient_state_notes = extract_transient_state_notes(athlete_model)
            return {
                "memory_summary": user.memory_summary or "",
                "athlete_model": athlete_model,
                "transient_state_notes": transient_state_notes,
                "memory_updated_at": memory_updated_at,
                "memory_age_days": memory_age_days,
            }

        result = await self._measure("get_athlete_profile", _load)
        self._request_cache[cache_key] = result
        return result

    async def _get_raw_recent_activities(
        self,
        *,
        date_from: date,
        date_to: date,
        sport_filters: list[str] | None = None,
    ) -> list[dict]:
        filter_part = ",".join(sorted(sport_filters or []))
        cache_key = f"recent_activities:{date_from.isoformat()}:{date_to.isoformat()}:{filter_part}"
        cached = self._get_cached(cache_key)
        if isinstance(cached, list):
            activities = cast("list[dict]", cached)
            self._index_activities(activities)
            return activities

        result = await self._measure(
            "get_recent_activities",
            lambda: self._load_recent_activities_merged(
                date_from=date_from,
                date_to=date_to,
                sport_filters=sport_filters,
            ),
        )
        self._set_cached(cache_key, result)
        if isinstance(result, list):
            self._index_activities([item for item in result if isinstance(item, dict)])
        return result

    async def get_recent_activities(
        self,
        *,
        date_from: date,
        date_to: date,
        sport_filters: list[str] | None = None,
        detail_level: Literal["summary", "full"] = "full",
    ) -> list[dict]:
        activities = await self._get_raw_recent_activities(
            date_from=date_from,
            date_to=date_to,
            sport_filters=sport_filters,
        )
        if detail_level == "summary":
            summaries: list[dict] = []
            for activity in activities:
                source = activity.get("source")
                if source == "whoop":
                    summaries.append(self._to_whoop_workout_summary(activity))
                else:
                    summaries.append(self._to_strava_activity_summary(activity))
            return summaries
        return activities

    async def get_activity_detail(self, *, activity_id: int | str) -> dict | None:
        parsed = self._parse_activity_id(activity_id)
        if parsed is None:
            return None
        source_name, raw_id, composite_id = parsed

        indexed = self._activity_index.get(composite_id)
        if isinstance(indexed, dict):
            return indexed

        cache_key = f"activity_detail:{composite_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            if isinstance(cached, dict):
                self._activity_index[composite_id] = cached
            return cached  # type: ignore[return-value]

        provider = self._providers.get(source_name)
        if provider is None:
            return None

        result = await self._measure(
            "get_activity_detail",
            lambda: provider.get_activity_detail(raw_id),
        )
        if result is not None:
            if isinstance(result, dict):
                result = self._enrich_activity_detail_payload(source_name=source_name, raw_id=raw_id, payload=result)
            self._set_cached(cache_key, result)
            if isinstance(result, dict):
                self._activity_index[composite_id] = result
        return result

    async def get_training_load_history(self, *, days: int) -> list[dict]:
        safe_days = max(1, min(days, 180))
        cache_key = f"training_load_history:{safe_days}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        result = await self._measure(
            "get_training_load_history",
            lambda: self._load_training_load_history_merged(days=safe_days),
        )
        self._set_cached(cache_key, result)
        return result

    async def get_recovery_readiness_signals(self, *, days: int) -> dict:
        safe_days = max(1, min(days, 30))
        cache_key = f"recovery_readiness_signals:{safe_days}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        async def _load_one(source_name: str, provider: OngoingTrainingProvider) -> dict:
            payload = await provider.get_recovery_readiness_signals(safe_days)
            return payload if isinstance(payload, dict) else {}

        async def _load():
            if not self._providers:
                return {
                    "window_days": safe_days,
                    "as_of_utc": datetime.now(UTC).isoformat(),
                    "sources": {},
                    "provider_status": self._provider_observability()["training_providers"],
                    "evidence_profile": self._current_evidence_profile(),
                }
            provider_entries = list(self._providers.items())
            tasks = [
                _load_one(source_name, provider) for source_name, provider in self._providers.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            sources: dict[str, dict] = {}
            for (source_name, _provider), payload in zip(provider_entries, results, strict=True):
                if isinstance(payload, BaseException):
                    degraded_error = self._degraded_provider_error(payload)
                    if degraded_error is not None:
                        self._mark_provider_unavailable(source_name=source_name, exc=degraded_error)
                        continue
                    raise payload
                sources[source_name] = payload
            return {
                "window_days": safe_days,
                "as_of_utc": datetime.now(UTC).isoformat(),
                "sources": sources,
                "provider_status": self._provider_observability()["training_providers"],
                "evidence_profile": self._current_evidence_profile(),
            }

        result = await self._measure("get_recovery_readiness_signals", _load)
        self._set_cached(cache_key, result)
        return result

    async def _load_snapshot_inputs(self, *, today: date) -> tuple[list[dict], list[dict], dict, dict, list[dict]]:
        return await asyncio.gather(
            self.get_recent_activities(date_from=today - timedelta(days=6), date_to=today, detail_level="summary"),
            self.get_training_load_history(days=28),
            self.get_recovery_readiness_signals(days=7),
            self.get_current_weekly_plan(),
            self.get_upcoming_competitions(),
        )

    @staticmethod
    def _derive_load_trend(load_28: list[dict]) -> tuple[str, float | None, float | None]:
        loads = [value for entry in load_28 if isinstance(entry, dict) and (value := _extract_load(entry)) is not None]
        recent_mean = mean(loads[-7:]) if len(loads) >= 7 else (mean(loads) if loads else None)
        prior_window = loads[-28:-7] if len(loads) > 7 else []
        prior_mean = mean(prior_window) if prior_window else None
        if recent_mean is None or prior_mean is None:
            return "insufficient_data", recent_mean, prior_mean
        if recent_mean > prior_mean * 1.05:
            return "rising", recent_mean, prior_mean
        if recent_mean < prior_mean * 0.95:
            return "falling", recent_mean, prior_mean
        return "stable", recent_mean, prior_mean

    @staticmethod
    def _find_next_planned_session(weekly_plan: dict, *, today: date) -> dict | None:
        weeks = weekly_plan.get("weeks", [])
        if not weeks or not isinstance(weeks[0], dict):
            return None

        week_days = weeks[0].get("days", [])
        if not isinstance(week_days, list):
            return None

        for day_row in week_days:
            if not isinstance(day_row, dict):
                continue
            blocks = day_row.get("blocks", [])
            if not isinstance(blocks, list) or not blocks:
                continue
            day_raw = day_row.get("date")
            if not isinstance(day_raw, str) or not day_raw:
                continue
            try:
                day_date = date.fromisoformat(day_raw[:10])
            except ValueError:
                continue
            if day_date >= today:
                return {
                    "date": day_date.isoformat(),
                    "day_id": day_row.get("day_id"),
                    "block_count": len(blocks),
                }
        return None

    async def get_training_snapshot(self) -> dict:
        today = datetime.now(UTC).date()
        activities_7, load_28, recovery_7, weekly_plan, competitions = await self._load_snapshot_inputs(today=today)
        sessions_by_source: dict[str, int] = {}
        for activity in activities_7:
            source = activity.get("source")
            if isinstance(source, str) and source:
                sessions_by_source[source] = sessions_by_source.get(source, 0) + 1

        load_trends_by_source: dict[str, dict] = {}
        for source_name in sorted(self._providers.keys()):
            subset = [
                entry
                for entry in load_28
                if isinstance(entry, dict) and entry.get("source") == source_name
            ]
            trend, recent_mean, prior_mean = self._derive_load_trend(subset)
            load_trends_by_source[source_name] = {
                "load_trend": trend,
                "recent_mean_7d": recent_mean,
                "prior_mean_21d": prior_mean,
            }

        next_planned_session = self._find_next_planned_session(weekly_plan, today=today)

        payload: dict[str, object] = {
            "as_of_date": today.isoformat(),
            "sessions_7d": len(activities_7),
            "sessions_7d_by_source": sessions_by_source,
            "load_trends_by_source": load_trends_by_source,
            "recovery_sources": recovery_7.get("sources") if isinstance(recovery_7, dict) else {},
            "provider_status": self._provider_observability()["training_providers"],
            "evidence_profile": self._current_evidence_profile(),
            "competition_proximity_days": nearest_competition_days(competitions, today),
            "next_planned_session": next_planned_session,
        }
        # Backwards-friendly keys for single-provider environments.
        if len(load_trends_by_source) == 1:
            only = next(iter(load_trends_by_source.values()))
            payload["load_trend"] = only.get("load_trend")
            payload["recent_mean_7d"] = only.get("recent_mean_7d")
            payload["prior_mean_21d"] = only.get("prior_mean_21d")
        return payload

    async def get_expert_analysis_summary(self) -> dict:
        active_analysis = await self._load_active_analysis()
        if active_analysis is None:
            return {
                "run_date": None,
                "age_days": None,
                "staleness": "unknown",
                "domains": {},
            }

        updated_at = active_analysis.updated_at.astimezone(UTC)
        age_days = (datetime.now(UTC) - updated_at).days
        expert_context = active_analysis.expert_context or {}

        def _domain_summary(domain_key: str) -> dict:
            domain_payload = expert_context.get(domain_key, {})
            if not isinstance(domain_payload, dict):
                return {"key_finding": None, "confidence": "unknown"}
            output = domain_payload.get("output")
            if isinstance(output, dict):
                synthesis = output.get("for_synthesis")
                if isinstance(synthesis, dict):
                    signals = synthesis.get("signals")
                    if isinstance(signals, list) and signals:
                        return {"key_finding": str(signals[0]), "confidence": "medium"}
            return {"key_finding": None, "confidence": "unknown"}

        return {
            "run_date": updated_at.date().isoformat(),
            "age_days": age_days,
            "staleness": _staleness_label(age_days),
            "analysis_version": active_analysis.version,
            "domains": {
                "metrics": _domain_summary("metrics_outputs"),
                "activity": _domain_summary("activity_outputs"),
                "physiology": _domain_summary("physiology_outputs"),
            },
        }

    async def get_expert_output(
        self,
        *,
        domain: Literal["metrics", "activity", "physiology"],
        target: Literal["for_synthesis", "for_season_planner", "for_weekly_planner"],
    ) -> dict:
        active_analysis = await self._load_active_analysis()
        if active_analysis is None:
            return {"status": "missing", "domain": domain, "target": target, "payload": None}

        domain_key = {
            "metrics": "metrics_outputs",
            "activity": "activity_outputs",
            "physiology": "physiology_outputs",
        }[domain]

        expert_context = active_analysis.expert_context or {}
        domain_payload = expert_context.get(domain_key, {})
        updated_at = active_analysis.updated_at.astimezone(UTC)
        age_days = (datetime.now(UTC) - updated_at).days

        if not isinstance(domain_payload, dict):
            return {
                "status": "missing",
                "domain": domain,
                "target": target,
                "age_days": age_days,
                "created_at": updated_at.isoformat(),
                "payload": None,
            }

        output = domain_payload.get("output")
        if isinstance(output, list):
            return {
                "status": "needs_clarification",
                "domain": domain,
                "target": target,
                "age_days": age_days,
                "created_at": updated_at.isoformat(),
                "questions": output,
            }

        if not isinstance(output, dict):
            return {
                "status": "missing",
                "domain": domain,
                "target": target,
                "age_days": age_days,
                "created_at": updated_at.isoformat(),
                "payload": None,
            }

        return {
            "status": "ok",
            "domain": domain,
            "target": target,
            "age_days": age_days,
            "created_at": updated_at.isoformat(),
            "payload": output.get(target),
        }

    def get_observability_snapshot(self) -> dict:
        return {
            "tool_usage": self._tool_usage,
            "cache_keys": sorted(self._request_cache.keys()),
            "provider": self._provider_observability(),
            "evidence_profile": self._current_evidence_profile(),
        }

    def _tool_get_training_snapshot(self):
        @tool("get_training_snapshot")
        async def get_training_snapshot_tool() -> dict:
            """Get a compact overview: 7-day session count, 28-day load trend (rising/falling/stable), recovery status, next race proximity, and next planned session. Start here before drilling into details."""
            return await self.get_training_snapshot()

        return get_training_snapshot_tool

    def _tool_get_expert_analysis_summary(self):
        @tool("get_expert_analysis_summary")
        async def get_expert_analysis_summary_tool() -> dict:
            """Get a compact summary of the latest full analysis run with staleness metadata."""
            return await self.get_expert_analysis_summary()

        return get_expert_analysis_summary_tool

    def _tool_get_expert_output(self):
        @tool("get_expert_output")
        async def get_expert_output_tool(
            domain: Literal["metrics", "activity", "physiology"],
            target: Literal["for_synthesis", "for_season_planner", "for_weekly_planner"],
        ) -> dict:
            """Get deep expert analysis for a specific domain and target. domain: 'metrics' (pace/HR/power zones), 'activity' (training pattern analysis), 'physiology' (recovery/adaptation). target: 'for_synthesis' (narrative summary), 'for_season_planner' (periodization data), 'for_weekly_planner' (session-level detail). Returns {status, domain, target, age_days, created_at, payload}."""
            return await self.get_expert_output(domain=domain, target=target)

        return get_expert_output_tool

    def _tool_get_current_analysis(self):
        @tool("get_current_analysis")
        async def get_current_analysis_tool() -> dict:
            """Get rendered dashboard analysis: exact athlete-visible KPIs/sections + {version, updated_at}."""
            return await self.get_current_analysis()

        return get_current_analysis_tool

    def _tool_get_current_weekly_plan(self):
        @tool("get_current_weekly_plan")
        async def get_current_weekly_plan_tool() -> dict:
            """Get full active weekly plan JSON + {version, updated_at}."""
            return await self.get_current_weekly_plan()

        return get_current_weekly_plan_tool

    def _tool_get_current_season_plan(self):
        @tool("get_current_season_plan")
        async def get_current_season_plan_tool() -> dict:
            """Get full active season plan JSON + {version, updated_at}."""
            return await self.get_current_season_plan()

        return get_current_season_plan_tool

    def _tool_get_upcoming_competitions(self):
        @tool("get_upcoming_competitions")
        async def get_upcoming_competitions_tool() -> list[dict]:
            """Get upcoming competitions and priorities."""
            return await self.get_upcoming_competitions()

        return get_upcoming_competitions_tool

    def _tool_get_athlete_profile(self):
        @tool("get_athlete_profile")
        async def get_athlete_profile_tool() -> dict:
            """Get long-term athlete profile context (memory summary, athlete model, transient states, and memory freshness metadata)."""
            return await self.get_athlete_profile()

        return get_athlete_profile_tool

    def _tool_get_recent_activities(self):
        @tool("get_recent_activities")
        async def get_recent_activities_tool(
            date_from: str,
            date_to: str,
            sport_filters: list[str] | None = None,
            detail_level: Literal["summary", "full"] = "summary",
        ) -> list[dict]:
            """Get activities in a date range from all connected providers (Strava and/or WHOOP).

            date_from/date_to must be YYYY-MM-DD (ISO 8601). detail_level 'summary' returns compact cards;
            'full' returns provider-native payloads. activity_id values are composite IDs: '{source}:{id}'.
            """
            return await self.get_recent_activities(
                date_from=date.fromisoformat(date_from),
                date_to=date.fromisoformat(date_to),
                sport_filters=sport_filters,
                detail_level=detail_level,
            )

        return get_recent_activities_tool

    def _tool_get_activity_detail(self):
        @tool("get_activity_detail")
        async def get_activity_detail_tool(activity_id: str) -> dict | None:
            """Get one full activity by composite activity_id (from get_recent_activities).

            activity_id is '{source}:{id}' where source is 'strava' or 'whoop'.
            Returns provider-native data for that activity.
            """
            return await self.get_activity_detail(activity_id=activity_id)

        return get_activity_detail_tool

    def _tool_get_training_load_history(self):
        @tool("get_training_load_history")
        async def get_training_load_history_tool(days: int = 28) -> list[dict]:
            """Get training load history for N days (clamped to 1..180) from all connected providers.

            Each entry includes {source, load_type, load_value} and preserves provider-native fields.
            """
            return await self.get_training_load_history(days=days)

        return get_training_load_history_tool

    def _tool_get_recovery_readiness_signals(self):
        @tool("get_recovery_readiness_signals")
        async def get_recovery_readiness_signals_tool(days: int = 7) -> dict:
            """Get recovery/readiness signals for N days (clamped to 1..30) from all connected providers."""
            return await self.get_recovery_readiness_signals(days=days)

        return get_recovery_readiness_signals_tool

    def create_langchain_tools(self) -> list:
        return [
            self._tool_get_training_snapshot(),
            self._tool_get_expert_analysis_summary(),
            self._tool_get_expert_output(),
            self._tool_get_current_analysis(),
            self._tool_get_current_weekly_plan(),
            self._tool_get_current_season_plan(),
            self._tool_get_upcoming_competitions(),
            self._tool_get_athlete_profile(),
            self._tool_get_recent_activities(),
            self._tool_get_activity_detail(),
            self._tool_get_training_load_history(),
            self._tool_get_recovery_readiness_signals(),
        ]


@asynccontextmanager
async def build_ongoing_tool_registry(
    db: AsyncSession,
    *,
    user_id,
    require_training_provider: bool = True,
):
    providers: dict[str, OngoingTrainingProvider] = {}
    for name, builder in (
        ("strava", build_ongoing_strava_provider),
        ("whoop", build_ongoing_whoop_provider),
    ):
        try:
            providers[name] = await builder(db, user_id=user_id)
        except HTTPException:
            continue

    if require_training_provider and not providers:
        raise HTTPException(status_code=404, detail="No training data source connected")

    registry = OngoingToolRegistry(db=db, user_id=user_id, providers=providers)
    try:
        yield registry
    finally:
        pass
