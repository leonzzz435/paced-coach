from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.ai.langgraph.nodes.activity_summarizer_node import extract_activity_data
from services.ai.langgraph.nodes.metrics_summarizer_node import extract_metrics_data, metrics_summarizer_node
from services.ai.langgraph.nodes.physiology_summarizer_node import extract_physiology_data, physiology_summarizer_node
from services.ai.langgraph.state.training_analysis_state import create_initial_state


@pytest.mark.asyncio
async def test_metrics_summarizer_node_basic():
    test_data = {
        "training_load_history": [
            {"date": "2024-01-01", "load": 100},
            {"date": "2024-01-02", "load": 120},
        ],
        "vo2_max_history": {"running": 55, "cycling": 60},
        "training_status": {"status": "productive", "load_focus": "maintaining"},
    }

    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={"generated_at_utc": "2024-01-02T00:00:00+00:00", "sources": {"strava": test_data}},
        execution_id="test_exec_123",
    )

    mock_response = Mock()
    mock_response.content = "Mocked metrics summary: Training load shows progression from 100 to 120."

    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("services.ai.model_config.ModelSelector.get_llm", return_value=mock_llm):
        result = await metrics_summarizer_node(state)

    assert "metrics_summary" in result
    assert isinstance(result["metrics_summary"], str)
    assert len(result["metrics_summary"]) > 0
    assert "costs" in result
    assert len(result["costs"]) == 1
    assert result["costs"][0]["agent"] == "metrics_summarizer"


@pytest.mark.asyncio
async def test_physiology_summarizer_node_basic():
    test_data = {
        "physiological_markers": {
            "hrv": {"average": 60, "baseline": 58}
        },
        "body_metrics": {"weight": 70, "body_fat": 12},
        "recovery_indicators": [
            {"date": "2024-01-01", "sleep": {"duration": 8, "quality": 85}, "stress": 30},
            {"date": "2024-01-02", "sleep": {"duration": 7.5, "quality": 80}, "stress": 35},
        ],
    }

    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={"generated_at_utc": "2024-01-02T00:00:00+00:00", "sources": {"strava": test_data}},
        execution_id="test_exec_124",
    )

    mock_response = Mock()
    mock_response.content = "Mocked physiology summary: HRV average 60, sleep quality good."

    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("services.ai.model_config.ModelSelector.get_llm", return_value=mock_llm):
        result = await physiology_summarizer_node(state)

    assert "physiology_summary" in result
    assert isinstance(result["physiology_summary"], str)
    assert len(result["physiology_summary"]) > 0
    assert "costs" in result
    assert len(result["costs"]) == 1
    assert result["costs"][0]["agent"] == "physiology_summarizer"


@pytest.mark.asyncio
async def test_metrics_summarizer_with_empty_data():
    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={"generated_at_utc": "2024-01-02T00:00:00+00:00", "sources": {"strava": {}}},
        execution_id="test_exec_125",
    )

    mock_response = Mock()
    mock_response.content = "No metrics data available."

    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("services.ai.model_config.ModelSelector.get_llm", return_value=mock_llm):
        result = await metrics_summarizer_node(state)

    assert "metrics_summary" in result or "errors" in result


@pytest.mark.asyncio
async def test_physiology_summarizer_with_empty_data():
    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={"generated_at_utc": "2024-01-02T00:00:00+00:00", "sources": {"strava": {}}},
        execution_id="test_exec_126",
    )

    mock_response = Mock()
    mock_response.content = "No physiology data available."

    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("services.ai.model_config.ModelSelector.get_llm", return_value=mock_llm):
        result = await physiology_summarizer_node(state)

        assert "physiology_summary" in result or "errors" in result


def test_extractors_include_evidence_profile_and_source_gaps():
    state = create_initial_state(
        user_id="test_user",
        athlete_name="Test Athlete",
        training_data={
            "generated_at_utc": "2024-01-02T00:00:00+00:00",
            "source_gaps": ["whoop"],
            "evidence_profile": {
                "connected_mode": "strava_only",
                "claims_policy": {"can_make_readiness_claims": False},
            },
            "sources": {
                "strava": {
                    "recent_activities": [{"id": 1}],
                    "training_load_history": [{"date": "2024-01-02", "load_value": 42}],
                    "activity_summary": {"activity_count": 1},
                }
            },
        },
        execution_id="test_exec_extractors",
    )

    activity_payload = extract_activity_data(state)
    metrics_payload = extract_metrics_data(state)
    physiology_payload = extract_physiology_data(state)

    assert activity_payload["source_gaps"] == ["whoop"]
    assert metrics_payload["evidence_profile"]["connected_mode"] == "strava_only"
    assert physiology_payload["evidence_profile"]["claims_policy"]["can_make_readiness_claims"] is False
