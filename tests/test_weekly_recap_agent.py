from __future__ import annotations

from dataclasses import dataclass

import pytest

from services.ai.head_coach.artifacts import NarrativeBlock
from services.ai.head_coach.schemas import RunProfileName
from services.ai.recap import weekly_recap_agent
from services.ai.recap.schemas import WeeklyRecapNarrative


@dataclass
class _FakeTool:
    name: str


class _ProviderFreeRegistry:
    def __init__(self):
        self.allowed_tool_names: set[str] | None = None

    @classmethod
    def registered_tool_names(cls) -> set[str]:
        return {"get_athlete_profile", "get_current_weekly_plan"}

    def get_observability_snapshot(self) -> dict:
        return {"source_of_truth": "local_athlete_owned"}

    def create_langchain_tools(self, *, allowed_tool_names=None) -> list:
        self.allowed_tool_names = set(allowed_tool_names or set())
        return [_FakeTool(name=name) for name in sorted(self.allowed_tool_names)]


def _block(key: str, content: str) -> NarrativeBlock:
    return NarrativeBlock(block_id=key, markdown=content)


@pytest.mark.asyncio
async def test_weekly_recap_uses_shared_head_coach_without_provider_tools(monkeypatch):
    registry = _ProviderFreeRegistry()
    fake_agent = object()
    factory_calls: list[dict] = []
    invoke_calls: list[dict] = []
    expected = WeeklyRecapNarrative(
        this_week_blocks=[_block("week", "Two planned sessions completed")],
        looking_ahead_blocks=[_block("ahead", "Keep the next quality day protected")],
        follow_up_question="How controlled did the final tempo block feel?",
    )

    def fake_build(**kwargs):
        factory_calls.append(kwargs)
        return fake_agent

    async def fake_invoke(**kwargs):
        invoke_calls.append(kwargs)
        return expected

    monkeypatch.setattr(weekly_recap_agent, "build_head_coach_agent", fake_build)
    monkeypatch.setattr(weekly_recap_agent, "invoke_head_coach_agent", fake_invoke)

    result = await weekly_recap_agent.generate_weekly_recap_narrative(
        tool_registry=registry,
        week_start_iso="2026-07-13T00:00:00Z",
        week_end_iso="2026-07-19T23:59:59Z",
        trigger_source="manual",
    )

    assert result is expected
    assert factory_calls[0]["profile_name"] is RunProfileName.WEEKLY_RECAP
    assert factory_calls[0]["response_schema"] is WeeklyRecapNarrative
    assert registry.allowed_tool_names == {"get_athlete_profile", "get_current_weekly_plan"}
    assert "athlete profile" in invoke_calls[0]["user_prompt"]
