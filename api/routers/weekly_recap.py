import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.services.recap import get_latest_weekly_recap_report

router = APIRouter()


@router.get("/latest")
async def get_latest_recap(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await get_latest_weekly_recap_report(db, user_id=user_id)
