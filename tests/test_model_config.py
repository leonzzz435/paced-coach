import types

import pytest

from core.config import AIMode, Config
from services.ai import model_config
from services.ai.ai_settings import AgentRole, AISettings
from services.ai.head_coach.run_profiles import RunProfileName, get_run_profile
from services.ai.model_config import ModelSelector


class _StubSettings:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def get_model_for_role(self, _: AgentRole) -> str:
        return self.model_name


GPT_5_5_SEARCH_ROLES = {
    AgentRole.SPECIALIST,
}


def test_uses_openai_client_when_key_available(monkeypatch):
    config = Config(openai_api_key="sk-test", ai_mode=AIMode.STANDARD)
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-4o"))

    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        captured["client"] = "ChatOpenAI"
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)

    ModelSelector.get_llm(AgentRole.HEAD_COACH)

    assert captured["api_key"] == "sk-test"
    assert captured["client"] == "ChatOpenAI"
    assert captured["base_url"] == "https://api.openai.com/v1"


def test_missing_openai_key_raises(monkeypatch):
    config = Config(ai_mode=AIMode.STANDARD)
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-4o"))

    monkeypatch.setattr(model_config, "ChatOpenAI", lambda **_kwargs: None)

    with pytest.raises(RuntimeError, match="API key"):
        ModelSelector.get_llm(AgentRole.HEAD_COACH)


@pytest.mark.parametrize("role", AISettings(mode=AIMode.STANDARD).model_assignments[AIMode.STANDARD])
def test_gpt_5_6_sol_search_roles_use_xhigh_reasoning_effort(monkeypatch, role: AgentRole):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-5.6-sol-search"))

    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)

    ModelSelector.get_llm(role)

    assert captured["reasoning"]["effort"] == "xhigh"


def test_standard_role_mappings_use_gpt_5_6_sol_search_for_all_roles():
    settings = AISettings(mode=AIMode.STANDARD)

    for role in settings.model_assignments[AIMode.STANDARD]:
        assert settings.get_model_for_role(role) == "gpt-5.6-sol-search"


@pytest.mark.parametrize("mode", [AIMode.COST_EFFECTIVE, AIMode.DEVELOPMENT, AIMode.PRO])
def test_non_standard_role_mappings_keep_gpt_5_5_family(mode: AIMode):
    settings = AISettings(mode=mode)

    for role in settings.model_assignments[mode]:
        expected_model = "gpt-5.5-search" if role in GPT_5_5_SEARCH_ROLES else "gpt-5.5"
        assert settings.get_model_for_role(role) == expected_model


@pytest.mark.parametrize(
    ("alias_name", "expected_model_name", "expected_effort"),
    [
        ("gpt-5", "gpt-5.5", "high"),
        ("gpt-5.6-sol", "gpt-5.6-sol", "high"),
        ("gpt-5.6-sol-search", "gpt-5.6-sol", "xhigh"),
        ("gpt-5-search", "gpt-5.5", "high"),
        ("gpt-5.5", "gpt-5.5", "high"),
        ("gpt-5.5-search", "gpt-5.5", "xhigh"),
        ("gpt-5.4", "gpt-5.4", "high"),
        ("gpt-5.4-search", "gpt-5.4", "xhigh"),
    ],
)
def test_gpt_5_aliases_resolve_to_configured_model_name(
    monkeypatch, alias_name: str, expected_model_name: str, expected_effort: str
):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings(alias_name))

    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)

    ModelSelector.get_llm(AgentRole.COACH_TRIAGE)

    assert captured["model"] == expected_model_name
    assert captured["base_url"] == "https://api.openai.com/v1"
    assert captured["reasoning"]["effort"] == expected_effort
    assert "tools" not in captured.get("model_kwargs", {})
    assert "include" not in captured


def test_search_models_pass_include_explicitly(monkeypatch):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-5.6-sol-search"))

    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)

    ModelSelector.get_llm(AgentRole.SPECIALIST)

    assert captured["include"] == ["web_search_call.action.sources"]
    assert captured["model_kwargs"]["tools"] == [{"type": "web_search"}]
    assert "include" not in captured["model_kwargs"]


@pytest.mark.parametrize(
    ("profile_name", "expected_effort"),
    [
        (RunProfileName.INITIAL_PLANNING, "medium"),
        (RunProfileName.MATERIAL_REPLANNING, "xhigh"),
        (RunProfileName.COACH_TURN, "medium"),
        (RunProfileName.WEEKLY_RECAP, "high"),
        (RunProfileName.DAILY_ADAPTATION, "high"),
        (RunProfileName.MEMORY_EXTRACTION, "low"),
        (RunProfileName.UI_COMPOSER, "low"),
    ],
)
def test_head_coach_profile_overrides_global_xhigh_default(
    monkeypatch,
    profile_name: RunProfileName,
    expected_effort: str,
):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-5.6-sol-search"))
    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)
    profile = get_run_profile(profile_name)

    ModelSelector.get_llm(
        profile.model_role,
        reasoning_effort=profile.reasoning_effort,
        enable_native_web_search=profile.enable_native_web_search,
    )

    assert captured["reasoning"]["effort"] == expected_effort
    assert "tools" not in captured.get("model_kwargs", {})
    assert "include" not in captured


def test_research_specialist_explicitly_keeps_native_web_search(monkeypatch):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-5.6-sol-search"))
    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)
    profile = get_run_profile(RunProfileName.RESEARCH_SPECIALIST)

    ModelSelector.get_llm(
        profile.model_role,
        reasoning_effort=profile.reasoning_effort,
        enable_native_web_search=profile.enable_native_web_search,
    )

    assert captured["reasoning"]["effort"] == "xhigh"
    assert captured["model_kwargs"]["tools"] == [{"type": "web_search"}]
    assert captured["include"] == ["web_search_call.action.sources"]
