from typing import Annotated, Any

from langgraph.graph import MessagesState
from services.ai.langgraph.schemas import (
    ActivityExpertOutputs,
    MetricsExpertOutputs,
    PhysiologyExpertOutputs,
    UiAnalysis,
    UiSeasonPlan,
    UiWeeklyPlan,
)


class TrainingAnalysisState(MessagesState):
    user_id: str
    athlete_name: str
    training_data: dict[str, Any]
    analysis_context: str
    planning_context: str
    transition_context: str

    competitions: list[dict[str, Any]]
    current_date: dict[str, str]
    week_dates: list[dict[str, str]]
    style_guide: str
    plotting_enabled: bool
    hitl_enabled: bool
    skip_synthesis: bool

    metrics_summary: str | None
    physiology_summary: str | None
    activity_summary: str | None

    metrics_outputs: MetricsExpertOutputs | None
    activity_outputs: ActivityExpertOutputs | None
    physiology_outputs: PhysiologyExpertOutputs | None

    synthesis_result: str | None

    analysis_blocks: UiAnalysis | None

    season_plan: str | None
    weekly_plan: str | None

    # Season plan persistence / reuse control.
    season_plan_action: str | None
    season_plan_reused: bool
    season_plan_needs_formatting: bool

    season_plan_blocks: UiSeasonPlan | None
    weekly_plan_blocks: UiWeeklyPlan | None

    weekly_plan_html: str | None
    season_plan_html: str | None

    analysis_html: str | None

    synthesis_complete: Annotated[bool, lambda x, y: x or y]
    season_plan_complete: Annotated[bool, lambda x, y: x or y]

    plot_resolution_stats: dict[str, Any] | None

    plots: Annotated[list[dict], lambda x, y: x + y]
    plot_storage_data: Annotated[dict[str, dict], lambda x, y: {**x, **y}]
    costs: Annotated[list[dict], lambda x, y: x + y]
    errors: Annotated[list[str], lambda x, y: x + y]
    tool_usage: Annotated[dict[str, int], lambda x, y: {**x, **y}]

    available_plots: Annotated[list[str], lambda x, y: x + y]
    execution_id: str

    # Agent-specific HITL message storage (with append reducer)
    metrics_expert_messages: Annotated[list, lambda x, y: (x or []) + y]
    activity_expert_messages: Annotated[list, lambda x, y: (x or []) + y]
    physiology_expert_messages: Annotated[list, lambda x, y: (x or []) + y]
    season_planner_messages: Annotated[list, lambda x, y: (x or []) + y]
    weekly_planner_messages: Annotated[list, lambda x, y: (x or []) + y]


def create_initial_state(
    user_id: str,
    athlete_name: str,
    training_data: dict[str, Any],
    analysis_context: str = "",
    planning_context: str = "",
    transition_context: str = "",
    competitions: list[dict[str, Any]] | None = None,
    current_date: dict[str, str] | None = None,
    week_dates: list[dict[str, str]] | None = None,
    style_guide: str = "",
    execution_id: str = "",
    plotting_enabled: bool = False,
    hitl_enabled: bool = True,
    skip_synthesis: bool = False,
    season_plan: str | None = None,
    season_plan_blocks: UiSeasonPlan | None = None,
) -> TrainingAnalysisState:
    return TrainingAnalysisState(
        user_id=user_id,
        athlete_name=athlete_name,
        training_data=training_data,
        analysis_context=analysis_context,
        planning_context=planning_context,
        transition_context=transition_context,
        competitions=competitions or [],
        current_date=current_date or {},
        week_dates=week_dates or [],
        style_guide=style_guide,
        plotting_enabled=plotting_enabled,
        hitl_enabled=hitl_enabled,
        skip_synthesis=skip_synthesis,
        execution_id=execution_id,
        metrics_summary=None,
        physiology_summary=None,
        activity_summary=None,
        metrics_outputs=None,
        activity_outputs=None,
        physiology_outputs=None,
        synthesis_result=None,
        analysis_blocks=None,
        season_plan=season_plan,
        weekly_plan=None,
        season_plan_action=None,
        season_plan_reused=False,
        season_plan_needs_formatting=True,
        season_plan_blocks=season_plan_blocks,
        weekly_plan_blocks=None,
        weekly_plan_html=None,
        season_plan_html=None,
        analysis_html=None,
        synthesis_complete=False,
        season_plan_complete=False,
        plot_resolution_stats=None,
        plots=[],
        plot_storage_data={},
        costs=[],
        errors=[],
        tool_usage={},
        available_plots=[],
        metrics_expert_messages=[],
        activity_expert_messages=[],
        physiology_expert_messages=[],
        season_planner_messages=[],
        weekly_planner_messages=[],
        messages=[],
    )
