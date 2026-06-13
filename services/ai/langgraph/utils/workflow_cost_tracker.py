import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .langsmith_cost_extractor import LangSmithCostExtractor, WorkflowCostSummary

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[str, WorkflowCostSummary], Awaitable[None]]
NodeCallback = Callable[[str], Awaitable[None]]
NodeTimingCallback = Callable[[str, float], Awaitable[None]]

_STATE_KEY_TO_NODE: list[tuple[str, str]] = [
    ("metrics_summary", "metrics_summarizer"),
    ("physiology_summary", "physiology_summarizer"),
    ("activity_summary", "activity_summarizer"),
    ("metrics_outputs", "metrics_expert"),
    ("physiology_outputs", "physiology_expert"),
    ("activity_outputs", "activity_expert"),
    ("synthesis_result", "synthesis"),
    ("plot_resolution_stats", "plot_resolution"),
    ("analysis_blocks", "analysis_formatter"),
    ("analysis_html", "analysis_formatter"),
    ("season_plan", "season_planner"),
    ("season_plan_complete", "data_integration"),
    ("weekly_plan", "weekly_planner"),
    ("season_plan_blocks", "season_formatter"),
    ("season_plan_html", "season_formatter"),
    ("weekly_plan_blocks", "weekly_formatter"),
    ("weekly_plan_html", "weekly_formatter"),
]

_COST_AGENT_TO_NODE: dict[str, str] = {
    "metrics_summarizer": "metrics_summarizer",
    "physiology_summarizer": "physiology_summarizer",
    "activity_summarizer": "activity_summarizer",
    "metrics": "metrics_expert",
    "physiology": "physiology_expert",
    "activity_expert": "activity_expert",
    "synthesis": "synthesis",
    "analysis_formatter": "analysis_formatter",
    "season_planner": "season_planner",
    "weekly_planner": "weekly_planner",
    "season_formatter": "season_formatter",
    "weekly_formatter": "weekly_formatter",
}


def _detect_nodes_from_state_delta(previous_state: dict[str, Any], current_state: dict[str, Any]) -> list[str]:
    changed_keys = {key for key, value in current_state.items() if previous_state.get(key) != value}
    detected_nodes: list[str] = []
    seen_nodes: set[str] = set()

    for state_key, node_name in _STATE_KEY_TO_NODE:
        if state_key in changed_keys:
            if node_name in seen_nodes:
                continue
            seen_nodes.add(node_name)
            detected_nodes.append(node_name)

    return detected_nodes


def _extract_new_node_timings_from_costs(
    previous_state: dict[str, Any],
    current_state: dict[str, Any],
) -> list[tuple[str, float]]:
    previous_costs = previous_state.get("costs")
    current_costs = current_state.get("costs")

    if not isinstance(current_costs, list):
        return []

    previous_len = len(previous_costs) if isinstance(previous_costs, list) else 0
    if len(current_costs) <= previous_len:
        return []

    new_timings: list[tuple[str, float]] = []
    for raw_entry in current_costs[previous_len:]:
        if not isinstance(raw_entry, dict):
            continue
        raw_agent = raw_entry.get("agent")
        if not isinstance(raw_agent, str):
            continue
        node_name = _COST_AGENT_TO_NODE.get(raw_agent)
        if node_name is None:
            continue
        raw_duration = raw_entry.get("execution_time")
        if not isinstance(raw_duration, int | float):
            continue
        new_timings.append((node_name, float(raw_duration)))

    return new_timings


@dataclass
class WorkflowExecution:
    trace_id: str
    root_run_id: str
    start_time: datetime
    end_time: datetime | None = None
    execution_time_seconds: float = 0.0
    cost_summary: WorkflowCostSummary | None = None
    node_timings_seconds: dict[str, float] = field(default_factory=dict)


@dataclass
class _WorkflowStreamState:
    final_state: dict[str, Any]
    previous_state: dict[str, Any]
    html_lengths: dict[str, int | None] = field(
        default_factory=lambda: {"weekly_plan_html": None, "analysis_html": None}
    )


def _workflow_config(
    *,
    root_run_id: uuid.UUID,
    thread_id: str,
    user_id: str | None,
    project_name: str,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "run_id": root_run_id,
        "run_name": "paced_coach_workflow",
        "tags": [
            f"user:{user_id}" if user_id else "user:unknown",
            "app:paced_coach",
            f"thread:{thread_id}" if thread_id else "thread:none",
        ],
        "metadata": {
            "user_id": user_id,
            "thread_id": thread_id,
            "project": project_name,
        },
    }
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}
    return config


async def _handle_task_chunk(
    chunk: object,
    *,
    node_started_callback: NodeCallback | None,
    node_completed_callback: NodeCallback | None,
) -> None:
    if not isinstance(chunk, dict):
        return
    node_name = chunk.get("name")
    if not isinstance(node_name, str):
        return
    if "triggers" in chunk:
        if node_started_callback:
            await node_started_callback(node_name)
        return
    if node_completed_callback:
        await node_completed_callback(node_name)


def _log_html_lengths(chunk: dict[str, Any], html_lengths: dict[str, int | None]) -> None:
    for key in ("analysis_html", "weekly_plan_html"):
        if not chunk.get(key):
            continue
        current_length = len(str(chunk[key]))
        if html_lengths[key] != current_length:
            logger.info("%s updated: %d chars", key, current_length)
            html_lengths[key] = current_length
        else:
            logger.debug("%s unchanged: %d chars", key, current_length)


async def _handle_value_chunk(
    chunk: object,
    *,
    stream_state: _WorkflowStreamState,
    execution: WorkflowExecution,
    node_timing_callback: NodeTimingCallback | None,
) -> None:
    logger.debug("Workflow step: %s", list(chunk.keys()) if isinstance(chunk, dict) else "None")
    if not isinstance(chunk, dict) or not chunk:
        return

    node_timings = _extract_new_node_timings_from_costs(stream_state.previous_state, chunk)
    if node_timing_callback:
        for node_name, duration_seconds in node_timings:
            await node_timing_callback(node_name, duration_seconds)

    for node_name, duration_seconds in node_timings:
        execution.node_timings_seconds[node_name] = duration_seconds

    stream_state.final_state = chunk
    stream_state.previous_state = dict(chunk)
    _log_html_lengths(chunk, stream_state.html_lengths)


def _finish_execution_timer(execution: WorkflowExecution) -> None:
    execution.end_time = datetime.now(UTC)
    execution.execution_time_seconds = (execution.end_time - execution.start_time).total_seconds()


class WorkflowCostTracker:
    def __init__(self, project_name: str = "paced_coach_analysis"):
        self.project_name = project_name
        self.cost_extractor = LangSmithCostExtractor()

    async def _populate_cost_summary(
        self,
        execution: WorkflowExecution,
        *,
        progress_callback: ProgressCallback | None,
    ) -> None:
        try:
            logger.info("Extracting costs for deterministic trace: %s", execution.trace_id)
            cost_summary = self.cost_extractor.extract_workflow_costs_by_trace(
                execution.trace_id, execution.execution_time_seconds
            )
            cost_summary.root_run_id = execution.root_run_id
            execution.cost_summary = cost_summary

            if progress_callback and cost_summary.total_cost_usd > 0:
                await progress_callback("workflow_complete", cost_summary)

            logger.info(
                "Workflow execution complete: $%.4f (%d tokens)",
                cost_summary.total_cost_usd,
                cost_summary.total_tokens,
            )
        except Exception:
            logger.exception("Error extracting costs for trace %s", execution.trace_id)
            execution.cost_summary = self.cost_extractor._zero_workflow_summary(execution.trace_id)

    def _mark_execution_failed(self, execution: WorkflowExecution) -> None:
        _finish_execution_timer(execution)
        execution.cost_summary = self.cost_extractor._zero_workflow_summary(execution.trace_id)

    async def run_workflow_with_cost_tracking(
        self,
        workflow_app,
        initial_state: dict[str, Any],
        thread_id: str,
        user_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
        node_started_callback: NodeCallback | None = None,
        node_completed_callback: NodeCallback | None = None,
        node_timing_callback: NodeTimingCallback | None = None,
    ) -> tuple[dict[str, Any], WorkflowExecution]:

        root_run_id = uuid.uuid4()

        execution = WorkflowExecution(
            trace_id=str(root_run_id),  # For root runs, trace_id equals run_id
            root_run_id=str(root_run_id),
            start_time=datetime.now(UTC),
        )

        stream_state = _WorkflowStreamState(
            final_state=dict(initial_state) if initial_state else {},
            previous_state=dict(initial_state),
        )

        try:
            logger.info("Starting workflow execution with deterministic root_run_id: %s", root_run_id)

            async for mode, chunk in workflow_app.astream(
                initial_state,
                config=_workflow_config(
                    root_run_id=root_run_id,
                    thread_id=thread_id,
                    user_id=user_id,
                    project_name=self.project_name,
                ),
                stream_mode=["values", "tasks"],
            ):
                if mode == "tasks":
                    await _handle_task_chunk(
                        chunk,
                        node_started_callback=node_started_callback,
                        node_completed_callback=node_completed_callback,
                    )
                    continue

                if mode == "values":
                    await _handle_value_chunk(
                        chunk,
                        stream_state=stream_state,
                        execution=execution,
                        node_timing_callback=node_timing_callback,
                    )

            logger.info(
                "Workflow execution complete with deterministic trace_id: %s",
                execution.trace_id,
            )
            _finish_execution_timer(execution)
            await self._populate_cost_summary(execution, progress_callback=progress_callback)

        except Exception:
            logger.exception("Error in workflow execution")
            self._mark_execution_failed(execution)
            raise

        return stream_state.final_state, execution

    def get_legacy_cost_summary(self, execution: WorkflowExecution) -> dict[str, Any]:
        if not execution.cost_summary:
            return {"total_cost_usd": 0.0, "total_tokens": 0, "agents": [], "model_breakdown": {}}

        cost_summary = execution.cost_summary

        agents = []
        model_breakdown = {}

        for node in cost_summary.node_costs:
            agents.append(
                {
                    "name": node.name,
                    "cost_usd": node.cost_usd,
                    "tokens": node.tokens,
                    "execution_time_seconds": 0.0,  # Per-node time not available yet
                    "models": [
                        {
                            "name": node.model or "unknown",
                            "cost_usd": node.cost_usd,
                            "input_tokens": node.input_tokens,
                            "output_tokens": node.output_tokens,
                            "total_tokens": node.tokens,
                            "web_search_requests": node.web_search_requests,
                        }
                    ],
                }
            )

            model_key = node.model or "unknown"
            if model_key not in model_breakdown:
                model_breakdown[model_key] = {
                    "cost_usd": 0.0,
                    "tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "web_search_requests": 0,
                }

            model_breakdown[model_key]["cost_usd"] += node.cost_usd
            model_breakdown[model_key]["tokens"] += node.tokens
            model_breakdown[model_key]["input_tokens"] += node.input_tokens
            model_breakdown[model_key]["output_tokens"] += node.output_tokens
            model_breakdown[model_key]["web_search_requests"] += node.web_search_requests

        return {
            "total_cost_usd": cost_summary.total_cost_usd,
            "total_tokens": cost_summary.total_tokens,
            "total_execution_time_seconds": cost_summary.execution_time_seconds,
            "agent_count": len(cost_summary.node_costs),
            "agents": agents,
            "model_breakdown": model_breakdown,
        }


class ProgressIntegratedCostTracker(WorkflowCostTracker):
    def __init__(self, project_name: str = "paced_coach_analysis", progress_manager=None):
        super().__init__(project_name)
        self.progress_manager = progress_manager

    async def run_workflow_with_progress(
        self,
        workflow_app,
        initial_state: dict[str, Any],
        thread_id: str,
        user_id: str | None = None,
        node_started_callback: Callable[[str], Awaitable[None]] | None = None,
        node_completed_callback: Callable[[str], Awaitable[None]] | None = None,
        node_timing_callback: Callable[[str, float], Awaitable[None]] | None = None,
    ) -> tuple[dict[str, Any], WorkflowExecution]:

        async def progress_callback(_event: str, cost_summary: WorkflowCostSummary):
            if self.progress_manager and hasattr(self.progress_manager, "analysis_stats"):
                self.progress_manager.analysis_stats["total_cost_usd"] = cost_summary.total_cost_usd
                self.progress_manager.analysis_stats["total_tokens"] = cost_summary.total_tokens

                if cost_summary.node_costs:
                    self.progress_manager.analysis_stats["agents_completed"] = len(cost_summary.node_costs)

                logger.info(
                    "Updated progress manager with cost: $%.4f",
                    cost_summary.total_cost_usd,
                )

        return await self.run_workflow_with_cost_tracking(
            workflow_app,
            initial_state,
            thread_id,
            user_id,
            progress_callback,
            node_started_callback,
            node_completed_callback,
            node_timing_callback,
        )
