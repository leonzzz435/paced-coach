from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_provider_shaped_legacy_runtime_is_absent() -> None:
    removed_paths = [
        ROOT / "services/ai/langgraph/workflows/analysis_workflow.py",
        ROOT / "services/ai/langgraph/workflows/planning_workflow.py",
        ROOT / "services/ai/langgraph/nodes/orchestrator_node.py",
        ROOT / "services/ai/langgraph/nodes/analysis_formatter_node.py",
        ROOT / "services/ai/langgraph/nodes/season_formatter_node.py",
        ROOT / "services/ai/langgraph/nodes/weekly_formatter_node.py",
        ROOT / "services/ai/langgraph/nodes/tool_calling_helper.py",
        ROOT / "services/ai/coach/plan_modifier_agent.py",
    ]

    assert all(not path.exists() for path in removed_paths)


def test_plan_generation_has_one_runtime_owner() -> None:
    api_source = (ROOT / "api/routers/analysis.py").read_text(encoding="utf-8")
    worker_source = (ROOT / "worker/tasks.py").read_text(encoding="utf-8")
    factory_source = (ROOT / "services/ai/head_coach/agent.py").read_text(encoding="utf-8")

    assert '"_workflow_version": "head_coach_v1"' in api_source
    assert "legacy_v1" not in api_source
    assert "run_complete_analysis_and_planning" not in worker_source
    assert "handle_tool_calling_in_node" not in worker_source
    assert "create_agent(" in factory_source
    assert "create_react_agent" not in factory_source
