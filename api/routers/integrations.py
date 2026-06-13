import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.deps import get_current_user, get_db
from api.services.integration_status import IntegrationsStatus, load_integrations_status

router = APIRouter()


@router.get("/status")
async def get_integrations_status(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> IntegrationsStatus:
    return await load_integrations_status(
        db,
        user_id=user_id,
        settings=get_settings(),
    )
