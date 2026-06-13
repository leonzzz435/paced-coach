import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.services.dashboard_state import build_dashboard_state

router = APIRouter()


@router.get("/state")
async def get_dashboard_state(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await build_dashboard_state(db, user_id=user_id)
