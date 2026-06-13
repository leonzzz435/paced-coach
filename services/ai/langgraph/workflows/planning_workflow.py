import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, cast

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from services.ai.langgraph.config.langsmith_config import LangSmithConfig
from services.ai.langgraph.nodes.activity_expert_node import activity_expert_node
from services.ai.langgraph.nodes.activity_summarizer_node import activity_summarizer_node
from services.ai.langgraph.nodes.analysis_formatter_node import analysis_formatter_node
from services.ai.langgraph.nodes.data_integration_node import data_integration_node
from services.ai.langgraph.nodes.metrics_expert_node import metrics_expert_node
from services.ai.langgraph.nodes.metrics_summarizer_node import metrics_summarizer_node
from services.ai.langgraph.nodes.orchestrator_node import master_orchestrator_node
from services.ai.langgraph.nodes.physiology_expert_node import physiology_expert_node
from services.ai.langgraph.nodes.physiology_summarizer_node import physiology_summarizer_node
from services.ai.langgraph.nodes.plot_resolution_node import plot_resolution_node
from services.ai.langgraph.nodes.season_formatter_node import season_formatter_node
from services.ai.langgraph.nodes.season_planner_node import season_planner_node
from services.ai.langgraph.nodes.synthesis_node import synthesis_node
from services.ai.langgraph.nodes.training_data_projection import (
    build_training_transition_context,
    compact_training_data_for_state,
    training_data_compaction_node,
)
from services.ai.langgraph.nodes.weekly_formatter_node import weekly_formatter_node
from services.ai.langgraph.nodes.weekly_planner_node import weekly_planner_node
from services.ai.langgraph.schemas.ui_blocks import UiSeasonPlan
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState, create_initial_state
from services.ai.langgraph.utils.workflow_cost_tracker import ProgressIntegratedCostTracker

logger = logging.getLogger(__name__)


def create_planning_workflow():
    LangSmithConfig.setup_langsmith()

    workflow = StateGraph(TrainingAnalysisState)

    workflow.add_node("season_planner", season_planner_node)
    workflow.add_node("master_orchestrator", master_orchestrator_node)
    workflow.add_node("data_integration", data_integration_node)
    workflow.add_node("weekly_planner", weekly_planner_node)

    workflow.add_edge(START, "season_planner")
    workflow.add_edge("season_planner", "master_orchestrator")

    workflow.add_edge("master_orchestrator", "data_integration")
    workflow.add_edge("master_orchestrator", "season_planner")
    workflow.add_edge("master_orchestrator", "weekly_planner")

    workflow.add_edge("data_integration", "weekly_planner")
    workflow.add_edge("weekly_planner", "master_orchestrator")
    workflow.add_edge("master_orchestrator", END)

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    logger.info("Created complete LangGraph planning workflow with 4 agents")
    return app


async def run_weekly_planning(
    user_id: str,
    athlete_name: str,
    training_data: dict,
    planning_context: str = "",
    competitions: list | None = None,
    current_date: dict | None = None,
    week_dates: list | None = None,
    existing_season_plan: str | None = None,
    existing_season_plan_blocks: UiSeasonPlan | None = None,
    existing_weekly_plan: str | None = None,
    transition_context: str = "",
    metrics_outputs=None,
    activity_outputs=None,
    physiology_outputs=None,
    plots: list | None = None,
    available_plots: list | None = None,
) -> dict:
    execution_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_planning"
    config = {"configurable": {"thread_id": execution_id}}

    initial_state = create_initial_state(
        user_id=user_id,
        athlete_name=athlete_name,
        training_data=compact_training_data_for_state(training_data),
        planning_context=planning_context,
        transition_context=transition_context
        or build_training_transition_context(
            training_data,
            current_date=current_date,
            existing_weekly_plan=existing_weekly_plan,
        ),
        competitions=competitions,
        current_date=current_date,
        week_dates=week_dates,
        execution_id=execution_id,
        season_plan=existing_season_plan,
        season_plan_blocks=existing_season_plan_blocks,
    )
    initial_state.update(
        {
            "metrics_outputs": metrics_outputs,
            "activity_outputs": activity_outputs,
            "physiology_outputs": physiology_outputs,
            "plots": plots or [],
            "available_plots": available_plots or [],
        }
    )

    async for chunk in create_planning_workflow().astream(
        initial_state,
        config=config,
        stream_mode="values",
    ):
        logger.info("Planning workflow step: %s", list(chunk.keys()) if chunk else "None")
        final_state = chunk

    return final_state


def create_integrated_analysis_and_planning_workflow():
    LangSmithConfig.setup_langsmith()

    workflow = StateGraph(TrainingAnalysisState)

    workflow.add_node("metrics_summarizer", metrics_summarizer_node)
    workflow.add_node("physiology_summarizer", physiology_summarizer_node)
    workflow.add_node("activity_summarizer", activity_summarizer_node)
    workflow.add_node("training_data_compaction", training_data_compaction_node)

    workflow.add_node("metrics_expert", metrics_expert_node)
    workflow.add_node("physiology_expert", physiology_expert_node)
    workflow.add_node("activity_expert", activity_expert_node)

    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("plot_resolution", plot_resolution_node)
    workflow.add_node("analysis_formatter", analysis_formatter_node)

    workflow.add_node("season_planner", season_planner_node)
    workflow.add_node("master_orchestrator", master_orchestrator_node)
    workflow.add_node("data_integration", data_integration_node)
    workflow.add_node("weekly_planner", weekly_planner_node)
    workflow.add_node("season_formatter", season_formatter_node)
    workflow.add_node("weekly_formatter", weekly_formatter_node)

    workflow.add_node("finalize", lambda state: state, defer=True)

    workflow.add_edge(START, "metrics_summarizer")
    workflow.add_edge(START, "physiology_summarizer")
    workflow.add_edge(START, "activity_summarizer")

    workflow.add_edge(
        ["metrics_summarizer", "physiology_summarizer", "activity_summarizer"],
        "training_data_compaction",
    )
    workflow.add_edge("training_data_compaction", "metrics_expert")
    workflow.add_edge("training_data_compaction", "physiology_expert")
    workflow.add_edge("training_data_compaction", "activity_expert")

    workflow.add_edge(["metrics_expert", "physiology_expert", "activity_expert"], "master_orchestrator")

    # Master orchestrator uses ONLY Command(goto=...) for dynamic routing

    workflow.add_edge("synthesis", "plot_resolution")
    workflow.add_edge("plot_resolution", "analysis_formatter")

    # Season planner routes back to orchestrator for HITL handling
    workflow.add_edge("season_planner", "master_orchestrator")

    # Data integration → weekly planner → orchestrator
    workflow.add_edge("data_integration", "weekly_planner")
    workflow.add_edge("weekly_planner", "master_orchestrator")

    # Formatters → finalize
    workflow.add_edge("analysis_formatter", "finalize")
    workflow.add_edge("season_formatter", "finalize")
    workflow.add_edge("weekly_formatter", "finalize")
    workflow.add_edge("finalize", END)

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    logger.info(
        "Created integrated analysis + planning workflow: "
        "3 summarizers → 3 experts → [analysis (synthesis/plots/analysis_formatter) || planning (season/weekly + season_formatter/weekly_formatter)] → finalize"
    )

    return app


async def run_complete_analysis_and_planning(
    user_id: str,
    athlete_name: str,
    training_data: dict,
    analysis_context: str = "",
    planning_context: str = "",
    competitions: list | None = None,
    current_date: dict | None = None,
    week_dates: list | None = None,
    progress_manager=None,
    plotting_enabled: bool = False,
    hitl_enabled: bool = True,
    skip_synthesis: bool = False,
    existing_season_plan: str | None = None,
    existing_season_plan_blocks: UiSeasonPlan | None = None,
    existing_weekly_plan: str | None = None,
    transition_context: str = "",
    node_started_callback: Callable[[str], Awaitable[None]] | None = None,
    node_completed_callback: Callable[[str], Awaitable[None]] | None = None,
    node_timing_callback: Callable[[str, float], Awaitable[None]] | None = None,
) -> dict:
    execution_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_complete"
    cost_tracker = ProgressIntegratedCostTracker(f"paced_coach_{user_id}", progress_manager)

    final_state, execution = await cost_tracker.run_workflow_with_progress(
        create_integrated_analysis_and_planning_workflow(),
        cast(
            "dict[str, Any]",
            create_initial_state(
                user_id=user_id,
                athlete_name=athlete_name,
                training_data=training_data,
                analysis_context=analysis_context,
                planning_context=planning_context,
                transition_context=transition_context
                or build_training_transition_context(
                    training_data,
                    current_date=current_date,
                    existing_weekly_plan=existing_weekly_plan,
                ),
                competitions=competitions,
                current_date=current_date,
                week_dates=week_dates,
                execution_id=execution_id,
                plotting_enabled=plotting_enabled,
                hitl_enabled=hitl_enabled,
                skip_synthesis=skip_synthesis,
                season_plan=existing_season_plan,
                season_plan_blocks=existing_season_plan_blocks,
            ),
        ),
        execution_id,
        user_id,
        node_started_callback=node_started_callback,
        node_completed_callback=node_completed_callback,
        node_timing_callback=node_timing_callback,
    )

    if execution.cost_summary:
        final_state["cost_summary"] = cost_tracker.get_legacy_cost_summary(execution)
        final_state["execution_metadata"] = {
            "trace_id": execution.trace_id,
            "root_run_id": execution.root_run_id,
            "execution_time_seconds": execution.execution_time_seconds,
            "total_cost_usd": execution.cost_summary.total_cost_usd,
            "total_tokens": execution.cost_summary.total_tokens,
            "node_timings_seconds": execution.node_timings_seconds,
        }
        logger.info(
            "Workflow complete for user %s: $%.4f (%d tokens)",
            user_id,
            execution.cost_summary.total_cost_usd,
            execution.cost_summary.total_tokens,
        )
    else:
        logger.warning("No cost data available for user %s workflow", user_id)
        final_state["cost_summary"] = {"total_cost_usd": 0.0, "total_tokens": 0}
        final_state["execution_metadata"] = {
            "node_timings_seconds": execution.node_timings_seconds,
        }

    return final_state
