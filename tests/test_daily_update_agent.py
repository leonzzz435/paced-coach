from __future__ import annotations

from dataclasses import dataclass

import pytest

from services.ai.daily import daily_update_agent
from services.ai.daily.schemas import DailyUpdateNarrative
from services.ai.head_coach.artifacts import NarrativeBlock
from services.ai.head_coach.schemas import RunProfileName
from services.ai.langgraph.schemas.ui_blocks import UiKpi


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


@pytest.mark.asyncio
async def test_daily_adaptation_uses_shared_head_coach_and_subjective_context_without_provider(monkeypatch):
    registry = _ProviderFreeRegistry()
    fake_agent = object()
    factory_calls: list[dict] = []
    invoke_calls: list[dict] = []
    expected = DailyUpdateNarrative(
        dashboard_kpis=[UiKpi(kpi_id="evidence", label="Evidence", value="Check-in", status="neutral")],
        today_focus_blocks=[
            NarrativeBlock(block_id="today", markdown="Keep today's run easy.")
        ],
    )

    def fake_build(**kwargs):
        factory_calls.append(kwargs)
        return fake_agent

    async def fake_invoke(**kwargs):
        invoke_calls.append(kwargs)
        return expected

    monkeypatch.setattr(daily_update_agent, "build_head_coach_agent", fake_build)
    monkeypatch.setattr(daily_update_agent, "invoke_head_coach_agent", fake_invoke)

    result = await daily_update_agent.generate_daily_update_narrative(
        tool_registry=registry,
        target_date_iso="2026-07-19",
        trigger_source="manual",
        athlete_check_in="Slept badly but legs feel fine.",
        prefetched_weekly_plan={"schema_version": 3, "weeks": []},
    )

    assert result is expected
    assert factory_calls[0]["profile_name"] is RunProfileName.DAILY_ADAPTATION
    assert factory_calls[0]["response_schema"] is DailyUpdateNarrative
    assert registry.allowed_tool_names == {"get_athlete_profile", "get_current_weekly_plan"}
    assert "Slept badly but legs feel fine." in invoke_calls[0]["user_prompt"]
