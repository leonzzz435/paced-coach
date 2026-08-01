from __future__ import annotations

import asyncio
from collections.abc import Collection
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from time import perf_counter

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.athlete_profile import AthleteProfile
from api.models.competition import Competition
from api.models.user import User
from api.services.coach_memory_metadata import derive_memory_freshness, extract_transient_state_notes


def nearest_competition_days(competitions: list[dict], today: date) -> int | None:
    nearest: int | None = None
    for competition in competitions:
        raw_date = competition.get("date")
        if not isinstance(raw_date, str) or not raw_date:
            continue
        try:
            competition_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            continue
        delta = (competition_date - today).days
        if delta >= 0 and (nearest is None or delta < nearest):
            nearest = delta
    return nearest


class OngoingToolRegistry:
    """Read-only tools over the app's local, athlete-owned sources of truth."""

    _REGISTERED_TOOL_NAMES = frozenset(
        {
            "get_current_weekly_plan",
            "get_current_season_plan",
            "get_upcoming_competitions",
            "get_athlete_profile",
        }
    )

    def __init__(self, *, db: AsyncSession, user_id):
        self._db = db
        self._user_id = user_id
        self._request_cache: dict[str, object] = {}
        self._tool_usage: dict[str, dict[str, float | int]] = {}
        self._db_lock = asyncio.Lock()

    async def _measure(self, name: str, call):
        started_at = perf_counter()
        # One registry is request-scoped and intentionally shares its caller's
        # AsyncSession. SQLAlchemy sessions may not execute concurrently, while
        # LangChain is free to invoke independent tools in parallel.
        async with self._db_lock:
            result = await call()
        elapsed_ms = (perf_counter() - started_at) * 1000.0
        current = self._tool_usage.get(name)
        if current is None:
            self._tool_usage[name] = {"count": 1, "total_ms": elapsed_ms}
        else:
            current["count"] = int(current["count"]) + 1
            current["total_ms"] = float(current["total_ms"]) + elapsed_ms
        return result

    async def get_current_weekly_plan(self) -> dict:
        cache_key = "current_weekly_plan"
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]  # type: ignore[return-value]

        async def _load():
            result = await self._db.execute(
                select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == self._user_id)
            )
            plan = result.scalar_one_or_none()
            if plan is None:
                return {}
            payload = dict(plan.plan_data or {})
            payload["version"] = plan.version
            payload["updated_at"] = plan.updated_at.isoformat()
            return payload

        payload = await self._measure(cache_key, _load)
        self._request_cache[cache_key] = payload
        return payload

    async def get_current_season_plan(self) -> dict:
        cache_key = "current_season_plan"
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]  # type: ignore[return-value]

        async def _load():
            result = await self._db.execute(
                select(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == self._user_id)
            )
            plan = result.scalar_one_or_none()
            if plan is None:
                return {}
            payload = dict(plan.plan_data or {})
            payload["version"] = plan.version
            payload["updated_at"] = plan.updated_at.isoformat()
            return payload

        payload = await self._measure(cache_key, _load)
        self._request_cache[cache_key] = payload
        return payload

    async def get_upcoming_competitions(self) -> list[dict]:
        cache_key = "upcoming_competitions"
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]  # type: ignore[return-value]

        async def _load():
            result = await self._db.execute(
                select(Competition)
                .where(Competition.user_id == self._user_id)
                .order_by(Competition.date.asc().nullslast(), Competition.created_at.asc())
            )
            return [
                {
                    "id": str(competition.id),
                    "name": competition.name,
                    "date": competition.date.isoformat() if competition.date else None,
                    "date_text": competition.date_text,
                    "race_type": competition.race_type,
                    "priority": competition.priority,
                    "target_time": competition.target_time,
                    "notes": competition.notes,
                }
                for competition in result.scalars().all()
            ]

        payload = await self._measure(cache_key, _load)
        self._request_cache[cache_key] = payload
        return payload

    async def get_athlete_profile(self) -> dict:
        cache_key = "athlete_profile"
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]  # type: ignore[return-value]

        async def _load():
            user_result = await self._db.execute(select(User).where(User.id == self._user_id))
            profile_result = await self._db.execute(
                select(AthleteProfile.profile).where(AthleteProfile.user_id == self._user_id)
            )
            user = user_result.scalar_one_or_none()
            canonical_profile = profile_result.scalar_one_or_none() or {}
            if user is None:
                return {
                    "profile": canonical_profile,
                    "memory_summary": "",
                    "athlete_model": {},
                    "transient_state_notes": [],
                    "memory_updated_at": None,
                    "memory_age_days": None,
                }
            athlete_model = user.athlete_model or {}
            memory_updated_at, memory_age_days = derive_memory_freshness(
                athlete_model, now=datetime.now(UTC)
            )
            return {
                "profile": canonical_profile,
                "memory_summary": user.memory_summary or "",
                "athlete_model": athlete_model,
                "transient_state_notes": extract_transient_state_notes(athlete_model),
                "memory_updated_at": memory_updated_at,
                "memory_age_days": memory_age_days,
            }

        payload = await self._measure(cache_key, _load)
        self._request_cache[cache_key] = payload
        return payload

    def get_observability_snapshot(self) -> dict:
        return {
            "tool_usage": self._tool_usage,
            "cache_keys": sorted(self._request_cache),
            "source_of_truth": "local_athlete_owned",
        }

    def _tool_get_current_weekly_plan(self):
        @tool("get_current_weekly_plan")
        async def get_current_weekly_plan_tool() -> dict:
            """Get the complete active 28-day execution plan, including its version and update time."""
            return await self.get_current_weekly_plan()

        return get_current_weekly_plan_tool

    def _tool_get_current_season_plan(self):
        @tool("get_current_season_plan")
        async def get_current_season_plan_tool() -> dict:
            """Get the complete active season strategy, including its version and update time."""
            return await self.get_current_season_plan()

        return get_current_season_plan_tool

    def _tool_get_upcoming_competitions(self):
        @tool("get_upcoming_competitions")
        async def get_upcoming_competitions_tool() -> list[dict]:
            """Get the athlete's declared competitions, goals, priorities, and notes."""
            return await self.get_upcoming_competitions()

        return get_upcoming_competitions_tool

    def _tool_get_athlete_profile(self):
        @tool("get_athlete_profile")
        async def get_athlete_profile_tool() -> dict:
            """Get the athlete-owned profile, coaching memory, and current declared context."""
            return await self.get_athlete_profile()

        return get_athlete_profile_tool

    @classmethod
    def registered_tool_names(cls) -> set[str]:
        return set(cls._REGISTERED_TOOL_NAMES)

    def create_langchain_tools(self, *, allowed_tool_names: Collection[str] | None = None) -> list:
        tools = [
            self._tool_get_current_weekly_plan(),
            self._tool_get_current_season_plan(),
            self._tool_get_upcoming_competitions(),
            self._tool_get_athlete_profile(),
        ]
        if allowed_tool_names is None:
            return tools
        allowed = set(allowed_tool_names)
        unknown = allowed - self._REGISTERED_TOOL_NAMES
        if unknown:
            raise ValueError(f"Unknown ongoing tool names: {sorted(unknown)!r}")
        return [tool_instance for tool_instance in tools if tool_instance.name in allowed]


@asynccontextmanager
async def build_ongoing_tool_registry(db: AsyncSession, *, user_id):
    yield OngoingToolRegistry(db=db, user_id=user_id)
