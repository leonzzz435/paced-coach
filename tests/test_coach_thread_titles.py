from types import SimpleNamespace

import pytest

from api.services import coach_thread_titles
from services.ai.ai_settings import AgentRole


class _FakeLlm:
    async def ainvoke(self, _messages):
        return SimpleNamespace(content="Marathon taper adjustments")


@pytest.mark.asyncio
async def test_generate_thread_title_uses_model_selector(monkeypatch):
    called_roles: list[AgentRole] = []

    def _fake_get_llm(role: AgentRole):
        called_roles.append(role)
        return _FakeLlm()

    monkeypatch.setattr(coach_thread_titles.ModelSelector, "get_llm", _fake_get_llm)

    title = await coach_thread_titles.generate_thread_title_from_exchange(
        user_message="Should I reduce volume before the race?",
        coach_reply="Yes, taper this week and keep intensity controlled.",
    )

    assert called_roles == [AgentRole.COACH_TRIAGE]
    assert title == "Marathon taper adjustments"


@pytest.mark.asyncio
async def test_generate_thread_title_returns_none_when_model_unavailable(monkeypatch):
    def _raise_get_llm(_role: AgentRole):
        raise RuntimeError("no llm configured")

    monkeypatch.setattr(coach_thread_titles.ModelSelector, "get_llm", _raise_get_llm)

    title = await coach_thread_titles.generate_thread_title_from_exchange(
        user_message="Any update?",
        coach_reply="All good.",
    )

    assert title is None
