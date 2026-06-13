import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.models.competition import Competition

router = APIRouter()


class CompetitionIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    date: date_type | None = None
    date_text: str | None = None
    race_type: str | None = None
    priority: str | None = None
    target_time: str | None = None
    notes: str | None = None

    @field_validator("name", "date_text", "race_type", "priority", "target_time", "notes", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class CompetitionOut(CompetitionIn):
    id: str


def _competition_out(competition: Competition) -> CompetitionOut:
    return CompetitionOut(
        id=str(competition.id),
        name=competition.name,
        date=competition.date,
        date_text=competition.date_text,
        race_type=competition.race_type,
        priority=competition.priority,
        target_time=competition.target_time,
        notes=competition.notes,
    )


@router.get("", response_model=list[CompetitionOut])
async def list_competitions(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> list[CompetitionOut]:
    result = await db.execute(
        select(Competition)
        .where(Competition.user_id == user_id)
        .order_by(
            Competition.date.is_(None),
            Competition.date.asc(),
            Competition.created_at.asc(),
        )
    )
    competitions = result.scalars().all()
    return [_competition_out(competition) for competition in competitions]


@router.post("", response_model=CompetitionOut, status_code=201)
async def create_competition(
    body: CompetitionIn,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> CompetitionOut:
    comp = Competition(
        user_id=user_id,
        name=body.name,
        date=body.date,
        date_text=body.date_text,
        race_type=body.race_type,
        priority=body.priority,
        target_time=body.target_time,
        notes=body.notes,
    )
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return _competition_out(comp)


@router.patch("/{competition_id}", response_model=CompetitionOut)
async def update_competition(
    competition_id: uuid.UUID,
    body: CompetitionIn,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> CompetitionOut:
    result = await db.execute(
        select(Competition).where(
            Competition.id == competition_id,
            Competition.user_id == user_id,
        )
    )
    comp = result.scalar_one_or_none()
    if comp is None:
        raise HTTPException(status_code=404, detail="Competition not found")

    comp.name = body.name
    comp.date = body.date
    comp.date_text = body.date_text
    comp.race_type = body.race_type
    comp.priority = body.priority
    comp.target_time = body.target_time
    comp.notes = body.notes

    await db.commit()
    await db.refresh(comp)
    return _competition_out(comp)


@router.delete("/{competition_id}", status_code=204)
async def delete_competition(
    competition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> None:
    result = await db.execute(
        delete(Competition).where(
            Competition.id == competition_id,
            Competition.user_id == user_id,
        )
    )
    await db.commit()
    rows = getattr(result, "rowcount", None)
    if rows is not None and rows == 0:
        raise HTTPException(status_code=404, detail="Competition not found")
