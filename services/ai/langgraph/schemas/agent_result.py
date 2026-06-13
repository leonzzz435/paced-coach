from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from .agent_outputs import Question
from .ui_blocks import UiSeasonPlan, UiWeeklyPlan


class AgentQuestions(BaseModel):
    kind: Literal["questions"] = "questions"
    questions: list[Question] = Field(default_factory=list)


class AgentWeeklyPlanContent(BaseModel):
    kind: Literal["weekly_plan"] = "weekly_plan"
    weekly_plan: UiWeeklyPlan


class AgentSeasonPlanContent(BaseModel):
    kind: Literal["season_plan"] = "season_plan"
    season_plan: UiSeasonPlan


AgentResult = Annotated[
    Union[AgentQuestions, AgentWeeklyPlanContent, AgentSeasonPlanContent],
    Field(discriminator="kind"),
]
