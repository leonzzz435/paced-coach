import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db

router = APIRouter()


class UploadInitIn(BaseModel):
    filenames: list[str]


@router.post("/init", status_code=201)
async def init_upload(
    payload: UploadInitIn,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> dict[str, int]:
    # Public interim MVP: accept "upload intent" without handling multipart uploads yet.
    # This keeps the public onboarding OAuth-clean while we build proper object storage uploads.
    _ = (db, user_id)
    if not payload.filenames:
        raise HTTPException(status_code=400, detail="No filenames provided")
    return {"accepted_files": len(payload.filenames)}

