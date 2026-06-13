from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.ai.langgraph.nodes.analysis_formatter_node import analysis_formatter_node
from services.ai.langgraph.nodes.season_formatter_node import season_formatter_node
from services.ai.langgraph.nodes.weekly_formatter_node import weekly_formatter_node
from services.ai.langgraph.schemas.ui_blocks import (
    LlmAnalysis,
    LlmSeasonPlan,
    LlmWeeklyPlan,
    UiDayPlan,
    UiDisclosureNode,
    UiHtmlBlock,
    UiSeasonPhase,
    UiWeekPlan,
)
from services.ai.langgraph.state.training_analysis_state import create_initial_state


async def _passthrough(func, *_args):
    return await func()


@pytest.mark.asyncio
async def test_analysis_formatter_builds_ui_blocks():
    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={"generated_at_utc": "2024-01-02T00:00:00+00:00", "sources": {"strava": {}}},
        execution_id="test_exec_001",
    )
    state["synthesis_result"] = "# Report\n\nKPI: 42"

    mock_llm = Mock()
    mock_structured = Mock()
    mock_structured.ainvoke = AsyncMock(
        return_value=LlmAnalysis(coach_action="Protect sleep tonight.", kpis=[], sections=[])
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("services.ai.model_config.ModelSelector.get_llm", return_value=mock_llm):
        with patch(
            "services.ai.langgraph.nodes.analysis_formatter_node.retry_with_backoff",
            new=AsyncMock(side_effect=_passthrough),
        ):
            result = await analysis_formatter_node(state)

    assert "analysis_blocks" in result
    assert result["analysis_blocks"].athlete_name == "Test Athlete"
    assert result["analysis_blocks"].analysis_id
    assert result["analysis_blocks"].coach_action == "Protect sleep tonight."
    assert "costs" in result
    assert result["costs"][0]["agent"] == "analysis_formatter"
    mock_llm.with_structured_output.assert_called_once_with(LlmAnalysis, method="function_calling")


@pytest.mark.asyncio
async def test_analysis_formatter_skips_without_synthesis():
    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={"generated_at_utc": "2024-01-02T00:00:00+00:00", "sources": {"strava": {}}},
        execution_id="test_exec_002",
    )

    result = await analysis_formatter_node(state)

    assert result == {}


@pytest.mark.asyncio
async def test_season_formatter_builds_ui_blocks():
    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={"generated_at_utc": "2024-01-02T00:00:00+00:00", "sources": {"strava": {}}},
        execution_id="test_exec_003",
    )
    state["season_plan"] = "# Season Plan\n\nPhase 1"

    mock_llm = Mock()
    mock_structured = Mock()
    mock_structured.ainvoke = AsyncMock(
        return_value=LlmSeasonPlan(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            phases=[
                UiSeasonPhase(
                    phase_id="phase-base-1",
                    title="Base",
                    start_date=date(2026, 2, 1),
                    end_date=date(2026, 2, 28),
                    blocks=[UiHtmlBlock(key="base", variant="notes", content_html="<div>Base</div>")],
                )
            ],
        )
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("services.ai.model_config.ModelSelector.get_llm", return_value=mock_llm):
        with patch(
            "services.ai.langgraph.nodes.season_formatter_node.retry_with_backoff",
            new=AsyncMock(side_effect=_passthrough),
        ):
            result = await season_formatter_node(state)

    assert "season_plan_blocks" in result
    assert result["season_plan_blocks"].athlete_name == "Test Athlete"
    assert result["season_plan_blocks"].plan_id
    assert "costs" in result
    assert result["costs"][0]["agent"] == "season_formatter"
    mock_llm.with_structured_output.assert_called_once_with(LlmSeasonPlan, method="function_calling")


@pytest.mark.asyncio
async def test_weekly_formatter_builds_ui_blocks():
    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={"generated_at_utc": "2024-01-02T00:00:00+00:00", "sources": {"strava": {}}},
        execution_id="test_exec_004",
    )
    state["weekly_plan"] = "# Weekly Plan\n\nDay 1"

    mock_llm = Mock()
    mock_structured = Mock()
    mock_structured.ainvoke = AsyncMock(
        return_value=LlmWeeklyPlan(
            global_nodes=[
                UiDisclosureNode(
                    node_id="global-intent",
                    title="Intent",
                    summary="Keep consistency high.",
                    blocks=[UiHtmlBlock(key="intent-note", variant="support", content_html="<div>Intent</div>")],
                    children=[],
                )
            ],
            weeks=[
                UiWeekPlan(
                    week_id="wk-2026-02-16",
                    week_label="Week 1",
                    start_date=date(2026, 2, 16),
                    end_date=date(2026, 2, 22),
                    days=[
                        UiDayPlan(
                            day_id="2026-02-16",
                            date=date(2026, 2, 16),
                            day_label="Monday",
                            blocks=[UiHtmlBlock(key="run", variant="workout", content_html="<div>Run</div>")],
                        )
                    ],
                )
            ]
        )
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("services.ai.model_config.ModelSelector.get_llm", return_value=mock_llm):
        with patch(
            "services.ai.langgraph.nodes.weekly_formatter_node.retry_with_backoff",
            new=AsyncMock(side_effect=_passthrough),
        ):
            result = await weekly_formatter_node(state)

    assert "weekly_plan_blocks" in result
    assert result["weekly_plan_blocks"].athlete_name == "Test Athlete"
    assert result["weekly_plan_blocks"].plan_id
    assert result["weekly_plan_blocks"].created_at
    assert len(result["weekly_plan_blocks"].global_nodes) == 1
    assert result["weekly_plan_blocks"].global_nodes[0].node_id == "global-intent"
    assert "costs" in result
    assert result["costs"][0]["agent"] == "weekly_formatter"
    mock_llm.with_structured_output.assert_called_once_with(LlmWeeklyPlan, method="function_calling")
