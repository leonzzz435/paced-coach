from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.ai.langgraph.nodes.season_planner_node import season_planner_node
from services.ai.langgraph.schemas.agent_outputs import SeasonPlannerDecision
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState, create_initial_state


async def _passthrough(func, *_args):
    return await func()


def _expert_outputs() -> dict[str, Any]:
    payload = {
        "signals": ["Load is stable enough for a strategic season update."],
        "evidence": ["Recent training context was included."],
        "implications": ["Keep the next phase continuous with the existing plan."],
    }
    return {"output": {"for_season_planner": payload}}


def _state(
    *,
    season_plan: str | None = "# Existing Season Plan",
    planning_context: str = "Custom planning instructions for this run:\nAdd one playful hill challenge each week.",
) -> TrainingAnalysisState:
    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={"generated_at_utc": "2026-05-03T00:00:00+00:00", "sources": {"strava": {}}},
        planning_context=planning_context,
        current_date={"date": "2026-05-03"},
        competitions=[],
        execution_id="test_exec_season",
        hitl_enabled=False,
        season_plan=season_plan,
    )
    state["metrics_outputs"] = cast("Any", _expert_outputs())
    state["activity_outputs"] = cast("Any", _expert_outputs())
    state["physiology_outputs"] = cast("Any", _expert_outputs())
    return state


def test_season_planner_decision_schema_stays_small():
    assert list(SeasonPlannerDecision.model_fields) == ["action", "rationale"]


@pytest.mark.asyncio
async def test_season_planner_generates_markdown_after_update_decision():
    mock_llm = Mock()
    mock_structured = Mock()
    mock_structured.ainvoke = AsyncMock(
        return_value=SeasonPlannerDecision(action="update", rationale="The event calendar changed.")
    )
    mock_llm.with_structured_output.return_value = mock_structured
    mock_llm.ainvoke = AsyncMock(return_value="# Updated Season Plan\n\n## Phase 1")

    with (
        patch("services.ai.langgraph.nodes.season_planner_node.ModelSelector.get_llm", return_value=mock_llm),
        patch("services.ai.langgraph.nodes.season_planner_node.configure_node_tools", return_value=[]),
        patch(
            "services.ai.langgraph.nodes.season_planner_node.retry_with_backoff",
            new=AsyncMock(side_effect=_passthrough),
        ),
    ):
        result = await season_planner_node(_state())

    assert result["season_plan"] == "# Updated Season Plan\n\n## Phase 1"
    assert result["season_plan_action"] == "update"
    assert result["season_plan_reused"] is False
    assert result["season_plan_needs_formatting"] is True
    mock_llm.with_structured_output.assert_called_once_with(SeasonPlannerDecision, method="json_schema")
    mock_structured.ainvoke.assert_awaited_once()
    mock_llm.ainvoke.assert_awaited_once()

    decision_messages = mock_structured.ainvoke.await_args.args[0]
    decision_user_prompt = decision_messages[1]["content"]
    assert "Planning Context and Custom Instructions" in decision_user_prompt
    assert "Add one playful hill challenge each week." in decision_user_prompt
    assert "valid reason to choose" in decision_user_prompt
    assert "lacks a competition-aware creative challenge thread" in decision_user_prompt

    update_messages = mock_llm.ainvoke.await_args.args[0]
    update_user_prompt = update_messages[1]["content"]
    assert "Planning Context and Custom Instructions" in update_user_prompt
    assert "Add one playful hill challenge each week." in update_user_prompt
    assert "Preserve explicit custom planning instructions" in update_user_prompt
    assert "season-long creative challenge thread" in update_user_prompt
    assert "larger signature/breakthrough challenges" in update_user_prompt
    assert "Do not hardcode stock challenges" in update_user_prompt


@pytest.mark.asyncio
async def test_season_planner_reuses_existing_plan_without_markdown_generation():
    mock_llm = Mock()
    mock_structured = Mock()
    mock_structured.ainvoke = AsyncMock(
        return_value=SeasonPlannerDecision(action="reuse", rationale="The existing plan still fits.")
    )
    mock_llm.with_structured_output.return_value = mock_structured
    mock_llm.ainvoke = AsyncMock(return_value="# Should not be generated")

    with (
        patch("services.ai.langgraph.nodes.season_planner_node.ModelSelector.get_llm", return_value=mock_llm),
        patch("services.ai.langgraph.nodes.season_planner_node.configure_node_tools", return_value=[]),
        patch(
            "services.ai.langgraph.nodes.season_planner_node.retry_with_backoff",
            new=AsyncMock(side_effect=_passthrough),
        ),
    ):
        result = await season_planner_node(_state())

    assert result["season_plan_action"] == "reuse"
    assert result["season_plan_reused"] is True
    assert result["season_plan_needs_formatting"] is False
    assert "season_plan" not in result
    mock_structured.ainvoke.assert_awaited_once()
    mock_llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_season_planner_skips_decision_when_no_existing_plan():
    mock_llm = Mock()
    mock_structured = Mock()
    mock_structured.ainvoke = AsyncMock(
        return_value=SeasonPlannerDecision(action="reuse", rationale="This should not be used.")
    )
    mock_llm.with_structured_output.return_value = mock_structured
    mock_llm.ainvoke = AsyncMock(return_value="# New Season Plan")

    with (
        patch("services.ai.langgraph.nodes.season_planner_node.ModelSelector.get_llm", return_value=mock_llm),
        patch("services.ai.langgraph.nodes.season_planner_node.configure_node_tools", return_value=[]),
        patch(
            "services.ai.langgraph.nodes.season_planner_node.retry_with_backoff",
            new=AsyncMock(side_effect=_passthrough),
        ),
    ):
        result = await season_planner_node(_state(season_plan=None))

    assert result["season_plan"] == "# New Season Plan"
    assert result["season_plan_action"] == "update"
    mock_structured.ainvoke.assert_not_awaited()
    mock_llm.ainvoke.assert_awaited_once()
