from pydantic import BaseModel, Field

from services.ai.coach.schemas import PlanPatchOp
from services.ai.langgraph.schemas.ui_blocks import UiHtmlBlock, UiKpi


class DailyUpdateNarrative(BaseModel):
    dashboard_kpis: list[UiKpi] = Field(
        min_length=1,
        max_length=6,
        description=(
            "Curated KPI strip for the above-the-fold dashboard today. "
            "Always return the KPI set that should be visible immediately after this daily sync. "
            "If the baseline strip still fits, restate that strip explicitly instead of leaving this empty."
        ),
    )
    today_focus_blocks: list[UiHtmlBlock] = Field(
        ...,
        description="HTML blocks for the 'Today Hero' widget. Should contain concrete guidance "
        "on today's physical readiness, interpreting recent sleep/HRV trends, and "
        "how to approach today's planned sessions.",
    )
    optional_proposal_ops: list[PlanPatchOp] = Field(
        default_factory=list,
        description="Proposed adjustments to the upcoming training plan if readiness levels dictate a change. "
        "Keep empty if the user is ready to execute the plan as originally scheduled.",
    )
