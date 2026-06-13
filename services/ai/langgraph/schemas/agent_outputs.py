from typing import Literal

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str = Field(..., description="Unique identifier (e.g., 'metrics_q1')")
    message: str = Field(..., description="Question text")
    context: str | None = Field(None, description="Additional context")
    message_type: str = Field("question", description="Type of message")


class AgentOutput(BaseModel):
    """Agent produces EITHER questions for HITL OR content for downstream consumers."""

    output: list[Question] | str = Field(
        ...,
        description="EITHER questions for HITL OR complete output for downstream consumers"
    )


class SeasonPlannerDecision(BaseModel):
    """Season planner can choose to reuse an existing plan to save cost."""

    action: Literal["reuse", "update"] = Field(
        ...,
        description=(
            "Decision for this run. "
            "'reuse' means keep the existing season plan as-is. "
            "'update' means a fully updated season plan markdown must be generated in a separate step."
        ),
    )
    rationale: str = Field(
        ...,
        description="Short, concrete explanation of why the plan is reused vs updated.",
    )
