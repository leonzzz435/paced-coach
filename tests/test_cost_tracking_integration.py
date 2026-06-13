from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest

from services.ai.langgraph.utils.langsmith_cost_extractor import (
    NodeCostSummary,
    WorkflowCostSummary,
)
from services.ai.langgraph.utils.workflow_cost_tracker import (
    WorkflowCostTracker,
    _detect_nodes_from_state_delta,
    _extract_new_node_timings_from_costs,
)


@pytest.fixture
def mock_progress_manager():
    manager = Mock()
    manager.analysis_stats = {
        "total_cost_usd": 0.0,
        "total_tokens": 0,
        "agents_completed": 0,
        "total_agents": 10,
    }
    return manager


class TestWorkflowCostSummary:

    def test_workflow_cost_summary_creation(self):
        summary = WorkflowCostSummary(
            trace_id="trace_123",
            root_run_id="root_123",
            total_cost_usd=0.005,
            total_tokens=350,
            total_input_tokens=240,
            total_output_tokens=110,
            total_web_searches=0,
            node_costs=[
                NodeCostSummary(
                    "metrics_node", "run1", "claude-3-5-sonnet-20241022", 0.002, 150, 100, 50
                ),
                NodeCostSummary(
                    "physiology_node", "run2", "claude-3-5-sonnet-20241022", 0.003, 200, 140, 60
                ),
            ],
            execution_time_seconds=45.0,
        )

        assert summary.trace_id == "trace_123"
        assert summary.total_cost_usd == 0.005
        assert summary.total_tokens == 350
        assert len(summary.node_costs) == 2
        assert next(node for node in summary.node_costs if node.name == "metrics_node").cost_usd == 0.002
        assert next(node for node in summary.node_costs if node.name == "metrics_node").tokens == 150

    def test_node_cost_summary_attributes(self):
        node = NodeCostSummary(
            name="test_node",
            run_id="run_123",
            model="claude-3-5-sonnet-20241022",
            cost_usd=0.001,
            tokens=100,
            input_tokens=70,
            output_tokens=30,
            web_search_requests=1,
        )

        assert node.name == "test_node"
        assert node.cost_usd == 0.001
        assert node.tokens == 100
        assert node.input_tokens == 70
        assert node.output_tokens == 30
        assert node.web_search_requests == 1


class TestWorkflowCostTracker:

    def test_get_legacy_cost_summary(self):
        tracker = WorkflowCostTracker()

        mock_execution = Mock()
        mock_execution.cost_summary = WorkflowCostSummary(
            trace_id="trace_123",
            root_run_id="root_123",
            total_cost_usd=0.005,
            total_tokens=350,
            total_input_tokens=240,
            total_output_tokens=110,
            total_web_searches=0,
            node_costs=[
                NodeCostSummary(
                    "metrics_node", "run1", "claude-3-5-sonnet-20241022", 0.002, 150, 100, 50
                ),
                NodeCostSummary(
                    "physiology_node", "run2", "claude-3-5-sonnet-20241022", 0.003, 200, 140, 60
                ),
            ],
            execution_time_seconds=45.0,
        )

        legacy_summary = tracker.get_legacy_cost_summary(mock_execution)

        assert legacy_summary["total_cost_usd"] == 0.005
        assert legacy_summary["total_tokens"] == 350
        assert legacy_summary["agent_count"] == 2
        assert len(legacy_summary["agents"]) == 2
        assert "claude-3-5-sonnet-20241022" in legacy_summary["model_breakdown"]

        model_data = legacy_summary["model_breakdown"]["claude-3-5-sonnet-20241022"]
        assert model_data["cost_usd"] == 0.005
        assert model_data["tokens"] == 350
        assert model_data["input_tokens"] == 240
        assert model_data["output_tokens"] == 110

    def test_get_legacy_cost_summary_empty(self):
        tracker = WorkflowCostTracker()

        mock_execution = Mock()
        mock_execution.cost_summary = None

        legacy_summary = tracker.get_legacy_cost_summary(mock_execution)

        assert legacy_summary["total_cost_usd"] == 0.0
        assert legacy_summary["total_tokens"] == 0
        assert legacy_summary["agents"] == []
        assert legacy_summary["model_breakdown"] == {}

    @pytest.mark.asyncio
    async def test_run_workflow_with_cost_tracking_emits_task_start_before_completion(self):
        class FakeWorkflowApp:
            async def astream(self, *_args, **_kwargs):
                yield ("tasks", {"name": "metrics_summarizer", "triggers": ("branch:to:metrics_summarizer",)})
                yield ("tasks", {"name": "metrics_summarizer", "error": None, "result": {"metrics_summary": "done"}})
                yield ("values", {"metrics_summary": "done", "costs": []})

        tracker = WorkflowCostTracker()
        cast("Any", tracker.cost_extractor).extract_workflow_costs_by_trace = Mock(
            return_value=WorkflowCostSummary(
                trace_id="trace_123",
                root_run_id="root_123",
                total_cost_usd=0.0,
                total_tokens=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_web_searches=0,
                node_costs=[],
                execution_time_seconds=0.0,
            )
        )

        started = AsyncMock()
        completed = AsyncMock()

        final_state, _execution = await tracker.run_workflow_with_cost_tracking(
            FakeWorkflowApp(),
            initial_state={},
            thread_id="thread_123",
            user_id="user_123",
            node_started_callback=started,
            node_completed_callback=completed,
        )

        assert final_state == {"metrics_summary": "done", "costs": []}
        assert started.await_args_list[0].args == ("metrics_summarizer",)
        assert completed.await_args_list[0].args == ("metrics_summarizer",)
        assert started.await_count == 1
        assert completed.await_count == 1


class TestNodeProgressDetection:

    def test_detects_all_parallel_nodes_from_single_state_delta(self):
        previous_state = {
            "metrics_summary": None,
            "physiology_summary": None,
            "activity_summary": None,
        }
        current_state = {
            "metrics_summary": {"ok": True},
            "physiology_summary": {"ok": True},
            "activity_summary": {"ok": True},
        }

        detected = _detect_nodes_from_state_delta(previous_state, current_state)

        assert detected == ["metrics_summarizer", "physiology_summarizer", "activity_summarizer"]

    def test_deduplicates_multiple_state_keys_for_same_node(self):
        previous_state = {
            "analysis_blocks": None,
            "analysis_html": None,
        }
        current_state = {
            "analysis_blocks": {"blocks": []},
            "analysis_html": "<p>done</p>",
        }

        detected = _detect_nodes_from_state_delta(previous_state, current_state)

        assert detected == ["analysis_formatter"]

    def test_returns_empty_when_state_does_not_change(self):
        previous_state = {"weekly_plan": {"workouts": 4}}
        current_state = {"weekly_plan": {"workouts": 4}}

        detected = _detect_nodes_from_state_delta(previous_state, current_state)

        assert detected == []

    def test_extracts_new_node_timings_from_cost_entries(self):
        previous_state = {
            "costs": [
                {"agent": "metrics_summarizer", "execution_time": 12.5},
            ]
        }
        current_state = {
            "costs": [
                {"agent": "metrics_summarizer", "execution_time": 12.5},
                {"agent": "metrics", "execution_time": 33.2},
                {"agent": "analysis_formatter", "execution_time": 91.4},
            ]
        }

        timings = _extract_new_node_timings_from_costs(previous_state, current_state)

        assert timings == [
            ("metrics_expert", 33.2),
            ("analysis_formatter", 91.4),
        ]


class TestLangSmithCostExtractorFallback:

    def test_extract_workflow_costs_no_client(self):
        import os

        from services.ai.langgraph.utils.langsmith_cost_extractor import LangSmithCostExtractor

        original_key = os.environ.get("LANGSMITH_API_KEY")
        if "LANGSMITH_API_KEY" in os.environ:
            del os.environ["LANGSMITH_API_KEY"]

        try:
            extractor = LangSmithCostExtractor()
            result = extractor.extract_workflow_costs_by_trace("test_trace")

            assert result.total_cost_usd == 0.0
            assert result.total_tokens == 0
            assert len(result.node_costs) == 0
            assert result.trace_id == "test_trace"
        finally:
            if original_key:
                os.environ["LANGSMITH_API_KEY"] = original_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
