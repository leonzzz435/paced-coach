from pydantic import BaseModel, Field

from .agent_outputs import Question


class ReceiverPayload(BaseModel):
    signals: list[str] = Field(
        description="Bullet signals: what changed; concise, high-signal."
    )
    evidence: list[str] = Field(
        description="Bullet evidence: numbers + dates/ranges that support the signals."
    )
    implications: list[str] = Field(
        description="Bullet implications: constraints/opportunities for this receiver."
    )
    uncertainty: list[str] | None = Field(
        default=None,
        description="Optional bullets: gaps, missing data, low confidence areas."
    )


class ReceiverOutputs(BaseModel):
    for_synthesis: ReceiverPayload = Field(
        ...,
        description="Synthesis-focused physiology/metrics/activity payload (comprehensive report input)."
    )
    for_season_planner: ReceiverPayload = Field(
        ...,
        description="Season-planner payload (12-24 week macro-cycle constraints + opportunities)."
    )
    for_weekly_planner: ReceiverPayload = Field(
        ...,
        description="Weekly-planner payload (next 28 days; readiness corridors + actionable guidance)."
    )


class ExpertOutputBase(BaseModel):
    output: list[Question] | ReceiverOutputs = Field(
        ...,
        description=(
            "Either HITL questions OR the full receiver payload. "
            "If you need clarification, return questions; otherwise return receiver outputs."
        )
    )


class MetricsExpertOutputs(ExpertOutputBase):
    pass


class ActivityExpertOutputs(ExpertOutputBase):
    pass


class PhysiologyExpertOutputs(ExpertOutputBase):
    pass
