import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.routers import (
    account,
    analysis,
    athlete_profile,
    coach,
    competitions,
    dashboard,
    health,
    plans,
    uploads,
)
from core.version_manifest import get_release_version

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info("Starting paced.coach API")
    yield
    logger.info("Shutting down paced.coach API")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Local-first AI endurance coaching from athlete-declared context",
        version=get_release_version(),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["Health"])
    app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
    app.include_router(athlete_profile.router, prefix="/api/athlete-profile", tags=["AthleteProfile"])
    app.include_router(competitions.router, prefix="/api/competitions", tags=["Competitions"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
    app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
    app.include_router(account.router, prefix="/api/account", tags=["Account"])
    app.include_router(plans.router, prefix="/api/plans", tags=["Plans"])
    app.include_router(coach.router, prefix="/api/coach", tags=["Coach"])

    return app


app = create_app()
