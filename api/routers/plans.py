import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.services.active_plans import (
    get_active_analysis,
    get_active_plans_bundle,
    get_active_season_plan,
    get_active_weekly_plan,
    toggle_day_completion,
)

router = APIRouter()


@router.get("/active")
async def get_active_plans(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    bundle = await get_active_plans_bundle(db, user_id=user_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="No active plans found")
    return bundle


@router.get("/active/weekly")
async def get_active_weekly(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    weekly = await get_active_weekly_plan(db, user_id=user_id)
    if not weekly:
        raise HTTPException(status_code=404, detail="No active weekly plan found")
    return weekly


@router.get("/active/season")
async def get_active_season(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    season = await get_active_season_plan(db, user_id=user_id)
    if not season:
        raise HTTPException(status_code=404, detail="No active season plan found")
    return season


@router.get("/active/analysis")
async def get_active_analysis_endpoint(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    analysis = await get_active_analysis(db, user_id=user_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="No active analysis found")
    return analysis


class DayCompletionRequest(BaseModel):
    is_completed: bool


@router.post("/active/weekly/days/{day_id}/completion")
async def update_day_completion_status(
    day_id: str,
    payload: DayCompletionRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    try:
        updated_bundle = await toggle_day_completion(
            db, user_id=user_id, day_id=day_id, is_completed=payload.is_completed
        )
        return updated_bundle
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
