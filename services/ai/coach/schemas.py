from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from services.ai.langgraph.schemas.ui_blocks import UiHtmlBlock, UiWeeklyPlan


class PatchOpType(str, Enum):
    UPSERT_DAY_BLOCK = "upsert_day_block"
    DELETE_DAY_BLOCK = "delete_day_block"
    REPLACE_DAY_BLOCKS = "replace_day_blocks"
    UPSERT_WEEK_NOTES_BLOCK = "upsert_week_notes_block"
    DELETE_WEEK_NOTES_BLOCK = "delete_week_notes_block"
    UPDATE_DAY_FIELDS = "update_day_fields"


class UpsertDayBlockOp(BaseModel):
    op: PatchOpType = PatchOpType.UPSERT_DAY_BLOCK
    day_id: str
    block: UiHtmlBlock


class DeleteDayBlockOp(BaseModel):
    op: PatchOpType = PatchOpType.DELETE_DAY_BLOCK
    day_id: str
    key: str


class ReplaceDayBlocksOp(BaseModel):
    op: PatchOpType = PatchOpType.REPLACE_DAY_BLOCKS
    day_id: str
    blocks: list[UiHtmlBlock]


class UpsertWeekNotesBlockOp(BaseModel):
    op: PatchOpType = PatchOpType.UPSERT_WEEK_NOTES_BLOCK
    week_id: str
    block: UiHtmlBlock


class DeleteWeekNotesBlockOp(BaseModel):
    op: PatchOpType = PatchOpType.DELETE_WEEK_NOTES_BLOCK
    week_id: str
    key: str


class UpdateDayFieldsOp(BaseModel):
    op: PatchOpType = PatchOpType.UPDATE_DAY_FIELDS
    day_id: str
    day_label: str | None = Field(
        default=None,
        description="Optional day label update. Omit if unchanged.",
    )
    workout_title: str | None = Field(
        default=None,
        description="Optional short session title shown on calendar cards. Omit if unchanged.",
    )
    focus_type: str | None = Field(
        default=None,
        description="Optional focus_type update (kebab-case). Omit if unchanged.",
    )
    focus_color: str | None = Field(
        default=None,
        description="Optional focus_color update (hex/rgb/hsl). Omit if unchanged.",
    )
    estimated_duration_min: int | None = Field(
        default=None,
        description="Optional estimated session duration in minutes. Omit if unchanged.",
    )
    estimated_intensity: Literal["rest", "low", "moderate", "high", "very_high"] | None = Field(
        default=None,
        description="Optional overall session intensity. Omit if unchanged.",
    )
    readiness_note: str | None = Field(
        default=None,
        description="Optional day readiness note update (1-2 sentences). Omit if unchanged.",
    )


PlanPatchOp = (
    UpsertDayBlockOp
    | DeleteDayBlockOp
    | ReplaceDayBlocksOp
    | UpsertWeekNotesBlockOp
    | DeleteWeekNotesBlockOp
    | UpdateDayFieldsOp
)


class CoachResponse(BaseModel):
    assistant_message: str
    ops: list[PlanPatchOp] = Field(default_factory=list)


class PatchApplicationResult(BaseModel):
    updated_plan: UiWeeklyPlan
    changed: bool
