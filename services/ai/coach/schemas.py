from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.ai.head_coach.artifacts import ExecutionPlanArtifactV3, SemanticBlock, TrainingIntensity
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


class V3PatchOpType(str, Enum):
    UPDATE_DAY_FIELDS = "update_day_fields_v3"
    UPDATE_SESSION_FIELDS = "update_session_fields_v3"
    REPLACE_SEMANTIC_BLOCK = "replace_semantic_block_v3"


class V3PatchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class UpdateV3DayFieldsOp(V3PatchModel):
    op: Literal[V3PatchOpType.UPDATE_DAY_FIELDS] = V3PatchOpType.UPDATE_DAY_FIELDS
    day_id: str = Field(min_length=1, max_length=200)
    label: str | None = Field(default=None, min_length=1, max_length=200)
    focus_type: str | None = Field(default=None, min_length=1, max_length=100)
    intensity: TrainingIntensity | None = None
    total_duration_min: int | None = Field(default=None, ge=0, le=1_440)


class UpdateV3SessionFieldsOp(V3PatchModel):
    op: Literal[V3PatchOpType.UPDATE_SESSION_FIELDS] = V3PatchOpType.UPDATE_SESSION_FIELDS
    session_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    objective_markdown: str | None = Field(default=None, min_length=1, max_length=20_000)
    prescription_markdown: str | None = Field(default=None, min_length=1, max_length=20_000)
    duration_min: int | None = Field(default=None, ge=1, le=1_440)
    intensity: TrainingIntensity | None = None
    distance_km: float | None = Field(default=None, ge=0.0)


class ReplaceV3SemanticBlockOp(V3PatchModel):
    op: Literal[V3PatchOpType.REPLACE_SEMANTIC_BLOCK] = V3PatchOpType.REPLACE_SEMANTIC_BLOCK
    container_id: str = Field(min_length=1, max_length=300)
    block_id: str = Field(min_length=1, max_length=200)
    block: SemanticBlock

    @model_validator(mode="after")
    def validate_block_identity(self) -> ReplaceV3SemanticBlockOp:
        if self.block.block_id != self.block_id:
            raise ValueError("Replacement block must preserve the target block ID")
        return self


V3PlanPatchOp = UpdateV3DayFieldsOp | UpdateV3SessionFieldsOp | ReplaceV3SemanticBlockOp
AnyPlanPatchOp = PlanPatchOp | V3PlanPatchOp


class CoachResponse(BaseModel):
    assistant_message: str
    ops: list[AnyPlanPatchOp] = Field(default_factory=list)


class PatchApplicationResult[PlanType: (UiWeeklyPlan, ExecutionPlanArtifactV3)](BaseModel):
    updated_plan: PlanType
    changed: bool
