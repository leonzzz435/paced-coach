from pathlib import Path

import pytest

from services.ai.evals.head_coach_eval import load_eval_suite
from services.ai.langgraph.utils.langsmith_cost_extractor import (
    NodeCostSummary,
    WorkflowCostSummary,
)


class TestWorkflowCostSummary:

    def test_head_coach_baseline_preserves_distinct_measurement_sources(self):
        suite = load_eval_suite(Path("tests/fixtures/head_coach_eval_cases.json"))

        assert suite.baseline.job_api_tokens == 227937
        assert suite.baseline.trace_tokens == 259581
        assert suite.baseline.job_api_cost_usd == pytest.approx(2.7798)
        assert suite.baseline.trace_cost_usd == pytest.approx(3.3789)

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
                    "metrics_node", "run1", "gpt-5.5", 0.002, 150, 100, 50
                ),
                NodeCostSummary(
                    "physiology_node", "run2", "gpt-5.5", 0.003, 200, 140, 60
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
            model="gpt-5.5",
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
