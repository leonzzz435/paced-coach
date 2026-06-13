from __future__ import annotations

from pydantic import BaseModel, Field

from services.ai.coach.schemas import PlanPatchOp
from services.ai.langgraph.schemas.ui_blocks import UiHtmlBlock


class WeeklyRecapNarrative(BaseModel):
    this_week_blocks: list[UiHtmlBlock] = Field(default_factory=list)
    looking_ahead_blocks: list[UiHtmlBlock] = Field(default_factory=list)
    optional_proposal_ops: list[PlanPatchOp] = Field(default_factory=list)
    follow_up_question: str = Field(
        default="",
        description="Targeted question for the athlete based on what the data showed",
    )
