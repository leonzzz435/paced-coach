"""FastAPI routers."""

from api.routers import (
    analysis,
    athlete_profile,
    coach,
    competitions,
    dashboard,
    health,
    integrations,
    plans,
    strava_oauth,
    weekly_recap,
    whoop_oauth,
)

__all__ = [
    "analysis",
    "athlete_profile",
    "coach",
    "competitions",
    "dashboard",
    "health",
    "integrations",
    "plans",
    "strava_oauth",
    "weekly_recap",
    "whoop_oauth",
]
