import logging
from datetime import datetime

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from services.ai.langgraph.config.langsmith_config import LangSmithConfig
from services.ai.langgraph.nodes.activity_expert_node import activity_expert_node
from services.ai.langgraph.nodes.activity_summarizer_node import activity_summarizer_node
from services.ai.langgraph.nodes.analysis_formatter_node import analysis_formatter_node
from services.ai.langgraph.nodes.metrics_expert_node import metrics_expert_node
from services.ai.langgraph.nodes.metrics_summarizer_node import metrics_summarizer_node
from services.ai.langgraph.nodes.orchestrator_node import master_orchestrator_node
from services.ai.langgraph.nodes.physiology_expert_node import physiology_expert_node
from services.ai.langgraph.nodes.physiology_summarizer_node import physiology_summarizer_node
from services.ai.langgraph.nodes.plot_resolution_node import plot_resolution_node
from services.ai.langgraph.nodes.synthesis_node import synthesis_node
from services.ai.langgraph.nodes.training_data_projection import training_data_compaction_node
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState, create_initial_state

logger = logging.getLogger(__name__)


def create_analysis_workflow():
    LangSmithConfig.setup_langsmith()

    workflow = StateGraph(TrainingAnalysisState)

    workflow.add_node("metrics_summarizer", metrics_summarizer_node)
    workflow.add_node("physiology_summarizer", physiology_summarizer_node)
    workflow.add_node("activity_summarizer", activity_summarizer_node)
    workflow.add_node("training_data_compaction", training_data_compaction_node)

    workflow.add_node("metrics_expert", metrics_expert_node)
    workflow.add_node("physiology_expert", physiology_expert_node)
    workflow.add_node("activity_expert", activity_expert_node)

    workflow.add_node("master_orchestrator", master_orchestrator_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("plot_resolution", plot_resolution_node)
    workflow.add_node("analysis_formatter", analysis_formatter_node)

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

    workflow.add_edge("master_orchestrator", "synthesis")
    workflow.add_edge("master_orchestrator", "metrics_expert")
    workflow.add_edge("master_orchestrator", "physiology_expert")
    workflow.add_edge("master_orchestrator", "activity_expert")

    workflow.add_edge("synthesis", "plot_resolution")
    workflow.add_edge("plot_resolution", "analysis_formatter")
    workflow.add_edge("analysis_formatter", END)

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    logger.info("Created complete LangGraph analysis workflow with 2-stage architecture (3 summarizers + 3 experts + synthesis + formatting)")

    return app


async def run_training_analysis(
    user_id: str,
    athlete_name: str,
    training_data: dict,
    analysis_context: str = "",
    competitions: list | None = None,
    current_date: dict | None = None,
    plotting_enabled: bool = False,
) -> dict:
    execution_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = {"configurable": {"thread_id": execution_id}}

    async for chunk in create_analysis_workflow().astream(
        create_initial_state(
            user_id=user_id,
            athlete_name=athlete_name,
            training_data=training_data,
            analysis_context=analysis_context,
            competitions=competitions,
            current_date=current_date,
            execution_id=execution_id,
            plotting_enabled=plotting_enabled,
        ),
        config=config,
        stream_mode="values",
    ):
        logger.info("Workflow step: %s", list(chunk.keys()) if chunk else "None")
        final_state = chunk

    return final_state


def create_simple_sequential_workflow():
    workflow = StateGraph(TrainingAnalysisState)

    workflow.add_node("metrics_summarizer", metrics_summarizer_node)
    workflow.add_node("physiology_summarizer", physiology_summarizer_node)
    workflow.add_node("activity_summarizer", activity_summarizer_node)

    workflow.add_node("metrics_expert", metrics_expert_node)
    workflow.add_node("physiology_expert", physiology_expert_node)
    workflow.add_node("activity_expert", activity_expert_node)

    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("plot_resolution", plot_resolution_node)

    workflow.add_edge(START, "metrics_summarizer")
    workflow.add_edge("metrics_summarizer", "metrics_expert")
    workflow.add_edge("metrics_expert", "physiology_summarizer")
    workflow.add_edge("physiology_summarizer", "physiology_expert")
    workflow.add_edge("physiology_expert", "activity_summarizer")
    workflow.add_edge("activity_summarizer", "activity_expert")
    workflow.add_edge("activity_expert", "synthesis")
    workflow.add_edge("synthesis", "plot_resolution")
    workflow.add_edge("plot_resolution", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)
