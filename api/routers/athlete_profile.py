import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.models.athlete_profile import AthleteProfile

router = APIRouter()


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    trimmed = value.strip()
    return trimmed or None


def _normalize_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        value = [value]
    items = [str(item).strip() for item in value]
    normalized = [item for item in items if item]
    return normalized or None


class PhysiologyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ftp: float | None = Field(default=None, ge=0)
    lthr: int | None = Field(default=None, ge=0)
    max_hr: int | None = Field(default=None, ge=0)
    custom_zones: str | None = None

    @field_validator("custom_zones", mode="before")
    @classmethod
    def normalize_strings(cls, value: Any) -> str | None:
        return _normalize_optional_string(value)


class PreferencesProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sports: list[str] | None = Field(default_factory=lambda: ["run", "bike", "swim"])
    excluded_sports: list[str] | None = None
    injuries_limitations: str | None = None
    timezone: str | None = None

    @field_validator("sports", "excluded_sports", mode="before")
    @classmethod
    def normalize_lists(cls, value: Any) -> list[str] | None:
        return _normalize_string_list(value)

    @field_validator("injuries_limitations", mode="before")
    @classmethod
    def normalize_strings(cls, value: Any) -> str | None:
        return _normalize_optional_string(value)

    @field_validator("timezone", mode="before")
    @classmethod
    def normalize_timezone(cls, value: Any) -> str | None:
        timezone_name = _normalize_optional_string(value)
        if timezone_name is None:
            return None
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Invalid IANA timezone") from exc
        return timezone_name


class AvailabilityProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    days_per_week: int | None = Field(default=5, ge=1, le=14)
    time_windows: str | None = None
    upcoming_travel: str | None = None

    @field_validator("time_windows", "upcoming_travel", mode="before")
    @classmethod
    def normalize_strings(cls, value: Any) -> str | None:
        return _normalize_optional_string(value)


class GoalsProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_goal: str | None = None
    notes: str | None = None

    @field_validator("primary_goal", "notes", mode="before")
    @classmethod
    def normalize_strings(cls, value: Any) -> str | None:
        return _normalize_optional_string(value)


class AthleteProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    physiology: PhysiologyProfile = Field(default_factory=PhysiologyProfile)
    preferences: PreferencesProfile = Field(default_factory=PreferencesProfile)
    availability: AvailabilityProfile = Field(default_factory=AvailabilityProfile)
    goals: GoalsProfile = Field(default_factory=GoalsProfile)


class AthleteProfileUpsertRequest(BaseModel):
    profile: AthleteProfilePayload = Field(default_factory=AthleteProfilePayload)


class AthleteProfileResponse(BaseModel):
    user_id: uuid.UUID
    profile: AthleteProfilePayload
    updated_at: datetime | None = None


def _read_profile_from_storage(profile: Any) -> AthleteProfilePayload:
    # Staging may still contain legacy keys from older profile shapes.
    return AthleteProfilePayload.model_validate(profile or {}, extra="ignore")


@router.get("", response_model=AthleteProfileResponse)
async def get_athlete_profile(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> AthleteProfileResponse:
    result = await db.execute(select(AthleteProfile).where(AthleteProfile.user_id == user_id))
    row = result.scalar_one_or_none()
    if not row:
        return AthleteProfileResponse(user_id=user_id, profile=AthleteProfilePayload(), updated_at=None)

    typed_profile = _read_profile_from_storage(row.profile)
    return AthleteProfileResponse(user_id=row.user_id, profile=typed_profile, updated_at=row.updated_at)


@router.put("", response_model=AthleteProfileResponse)
async def upsert_athlete_profile(
    payload: AthleteProfileUpsertRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> AthleteProfileResponse:
    result = await db.execute(select(AthleteProfile).where(AthleteProfile.user_id == user_id))
    row = result.scalar_one_or_none()
    profile_payload = payload.profile.model_dump(mode="python")

    if row:
        row.profile = profile_payload
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return AthleteProfileResponse(
            user_id=row.user_id,
            profile=_read_profile_from_storage(row.profile),
            updated_at=row.updated_at,
        )

    row = AthleteProfile(user_id=user_id, profile=profile_payload)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return AthleteProfileResponse(
        user_id=row.user_id,
        profile=_read_profile_from_storage(row.profile),
        updated_at=row.updated_at,
    )
