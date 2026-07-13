import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.services.account_deletion import delete_account_and_data as perform_account_delete

router = APIRouter()


@router.delete("")
async def delete_account_and_data(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> dict[str, str]:
    return await perform_account_delete(db, user_id=user_id)
