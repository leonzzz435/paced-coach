from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.ai.coach.schemas import AnyPlanPatchOp
from services.ai.head_coach.artifacts import SemanticBlock


class WeeklyRecapNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    this_week_blocks: list[SemanticBlock] = Field(min_length=1, max_length=20)
    looking_ahead_blocks: list[SemanticBlock] = Field(min_length=1, max_length=20)
    optional_proposal_ops: list[AnyPlanPatchOp] = Field(default_factory=list)
    follow_up_question: str = Field(
        min_length=1,
        max_length=600,
        description="Targeted question for the athlete based on what the data showed",
    )

    @model_validator(mode="after")
    def validate_unique_block_ids(self) -> WeeklyRecapNarrative:
        block_ids = [block.block_id for block in [*self.this_week_blocks, *self.looking_ahead_blocks]]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("Weekly recap block IDs must be unique")
        return self
