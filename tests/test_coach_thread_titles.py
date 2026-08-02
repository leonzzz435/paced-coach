from types import SimpleNamespace

import pytest

from api.services import coach_thread_titles
from services.ai.ai_settings import AgentRole


class _FakeLlm:
    async def ainvoke(self, _messages):
        return SimpleNamespace(content="Marathon taper adjustments")


@pytest.mark.asyncio
async def test_generate_thread_title_uses_model_selector(monkeypatch):
    model_calls: list[tuple[AgentRole, dict[str, object]]] = []

    def _fake_get_llm(role: AgentRole, **kwargs):
        model_calls.append((role, kwargs))
        return _FakeLlm()

    monkeypatch.setattr(coach_thread_titles.ModelSelector, "get_llm", _fake_get_llm)

    title = await coach_thread_titles.generate_thread_title_from_exchange(
        user_message="Should I reduce volume before the race?",
        coach_reply="Yes, taper this week and keep intensity controlled.",
    )

    assert model_calls == [(AgentRole.COACH_TRIAGE, {"enable_native_web_search": False})]
    assert title == "Marathon taper adjustments"


@pytest.mark.asyncio
async def test_generate_thread_title_returns_none_when_model_unavailable(monkeypatch):
    def _raise_get_llm(_role: AgentRole, **_kwargs):
        raise RuntimeError("no llm configured")

    monkeypatch.setattr(coach_thread_titles.ModelSelector, "get_llm", _raise_get_llm)

    title = await coach_thread_titles.generate_thread_title_from_exchange(
        user_message="Any update?",
        coach_reply="All good.",
    )

    assert title is None
