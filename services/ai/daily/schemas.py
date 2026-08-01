from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.ai.coach.schemas import AnyPlanPatchOp
from services.ai.head_coach.artifacts import SemanticBlock
from services.ai.langgraph.schemas.ui_blocks import UiKpi


class DailyUpdateNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dashboard_kpis: list[UiKpi] = Field(
        min_length=1,
        max_length=6,
        description=(
            "Curated KPI strip for the above-the-fold dashboard today. "
            "Always return the KPI set that should be visible immediately after this daily sync. "
            "If the baseline strip still fits, restate that strip explicitly instead of leaving this empty."
        ),
    )
    today_focus_blocks: list[SemanticBlock] = Field(
        ...,
        min_length=1,
        max_length=20,
        description=(
            "Semantic coaching blocks for the Today Hero widget. Use only evidence available for this run, "
            "state uncertainty when recovery signals are absent, and give concrete guidance for today's plan."
        ),
    )
    optional_proposal_ops: list[AnyPlanPatchOp] = Field(
        default_factory=list,
        description="Proposed adjustments to the upcoming training plan if readiness levels dictate a change. "
        "Keep empty if the user is ready to execute the plan as originally scheduled.",
    )

    @model_validator(mode="after")
    def validate_unique_block_ids(self) -> DailyUpdateNarrative:
        block_ids = [block.block_id for block in self.today_focus_blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("Daily update block IDs must be unique")
        return self
