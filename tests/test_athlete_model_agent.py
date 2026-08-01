import pytest

from services.ai.coach import athlete_model_agent
from services.ai.coach.athlete_model_agent import AthleteModelSummary
from services.ai.head_coach.schemas import RunProfileName


def test_athlete_model_summary_confidence_schema_is_object_array():
    schema = AthleteModelSummary.model_json_schema()
    confidence_schema = schema["properties"]["confidence_by_field"]
    assert confidence_schema["type"] == "array"
    items_schema = confidence_schema["items"]
    assert "$ref" in items_schema


@pytest.mark.asyncio
async def test_athlete_model_uses_shared_memory_profile(monkeypatch):
    expected = AthleteModelSummary(memory_summary="Prefers early easy runs.")
    fake_agent = object()
    factory_calls: list[dict] = []

    def fake_build(**kwargs):
        factory_calls.append(kwargs)
        return fake_agent

    async def fake_invoke(**kwargs):
        assert kwargs["agent"] is fake_agent
        return expected

    monkeypatch.setattr(athlete_model_agent, "build_head_coach_agent", fake_build)
    monkeypatch.setattr(athlete_model_agent, "invoke_head_coach_agent", fake_invoke)

    result = await athlete_model_agent.summarize_athlete_model(
        previous_model={},
        recent_events=[{"event_type": "athlete_message", "payload": {"text": "Mornings work best."}}],
    )

    assert result is expected
    assert factory_calls[0]["profile_name"] is RunProfileName.MEMORY_EXTRACTION
    assert factory_calls[0]["response_schema"] is AthleteModelSummary
    assert factory_calls[0]["tools"] == []
