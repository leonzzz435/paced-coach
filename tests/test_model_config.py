import types

import pytest

from core.config import AIMode, Config
from services.ai import model_config
from services.ai.ai_settings import AgentRole, AISettings
from services.ai.model_config import ModelSelector


class _StubSettings:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def get_model_for_role(self, _: AgentRole) -> str:
        return self.model_name


GPT_5_5_SEARCH_ROLES = {
    AgentRole.METRICS_EXPERT,
    AgentRole.PHYSIOLOGY_EXPERT,
    AgentRole.ACTIVITY_EXPERT,
    AgentRole.WEEKLY_PLANNER,
    AgentRole.SEASON_PLANNER,
    AgentRole.WEEKLY_RECAP,
    AgentRole.DAILY_UPDATE,
}


@pytest.mark.parametrize(
    ("model_name", "api_key_field", "expected_client"),
    [
        ("claude-4", "anthropic_api_key", "ChatAnthropic"),
        ("gpt-4o", "openai_api_key", "ChatOpenAI"),
    ],
)
def test_prefers_direct_api_when_key_available(monkeypatch, model_name, api_key_field, expected_client):
    api_key_values = {
        "anthropic_api_key": "sk-ant-api03-test",
        "openai_api_key": "sk-test",
    }
    config_dict = {
        api_key_field: api_key_values[api_key_field],
        "ai_mode": AIMode.STANDARD,
    }
    from typing import Any, cast

    config = Config(**cast("dict[str, Any]", config_dict))
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings(model_name))

    captured = {}

    def fake_chat_anthropic(**kwargs):
        captured.update(kwargs)
        captured["client"] = "ChatAnthropic"
        return types.SimpleNamespace(**kwargs)

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        captured["client"] = "ChatOpenAI"
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatAnthropic", fake_chat_anthropic)
    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)

    ModelSelector.get_llm(AgentRole.SUMMARIZER)

    assert captured["api_key"] == api_key_values[api_key_field]
    assert captured["client"] == expected_client
    if expected_client == "ChatOpenAI":
        assert captured["base_url"] == "https://api.openai.com/v1"
    else:
        assert captured["model"] == "claude-sonnet-4-6"


def test_missing_both_direct_and_openrouter_keys_raises(monkeypatch):
    config = Config(ai_mode=AIMode.STANDARD)
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("claude-4"))

    monkeypatch.setattr(model_config, "ChatOpenAI", lambda **_kwargs: None)
    monkeypatch.setattr(model_config, "ChatAnthropic", lambda **_kwargs: None)

    with pytest.raises(RuntimeError, match="API key"):
        ModelSelector.get_llm(AgentRole.SUMMARIZER)


@pytest.mark.parametrize("role", AISettings(mode=AIMode.STANDARD).model_assignments[AIMode.STANDARD])
def test_gpt_5_5_search_roles_use_xhigh_reasoning_effort(monkeypatch, role: AgentRole):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-5.5-search"))

    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)
    monkeypatch.setattr(model_config, "ChatAnthropic", lambda **_kwargs: None)

    ModelSelector.get_llm(role)

    assert captured["reasoning"]["effort"] == "xhigh"


def test_standard_role_mappings_use_gpt_5_5_search_for_all_roles():
    settings = AISettings(mode=AIMode.STANDARD)

    for role in settings.model_assignments[AIMode.STANDARD]:
        assert settings.get_model_for_role(role) == "gpt-5.5-search"


@pytest.mark.parametrize("mode", [AIMode.COST_EFFECTIVE, AIMode.DEVELOPMENT, AIMode.PRO])
def test_non_standard_role_mappings_keep_gpt_5_5_family(mode: AIMode):
    settings = AISettings(mode=mode)

    for role in settings.model_assignments[mode]:
        expected_model = "gpt-5.5-search" if role in GPT_5_5_SEARCH_ROLES else "gpt-5.5"
        assert settings.get_model_for_role(role) == expected_model


def test_anthropic_role_mappings_use_claude_family():
    settings = AISettings(mode=AIMode.ANTHROPIC)

    for role in settings.model_assignments[AIMode.ANTHROPIC]:
        assert settings.get_model_for_role(role) == "claude-4"


@pytest.mark.parametrize("role", [AgentRole.ANALYSIS_FORMATTER, AgentRole.PLAN_FORMATTER])
def test_standard_formatter_model_mapping_uses_gpt_5_5_search(role: AgentRole):
    settings = AISettings(mode=AIMode.STANDARD)

    assert settings.get_model_for_role(role) == "gpt-5.5-search"


@pytest.mark.parametrize(
    ("alias_name", "expected_model_name"),
    [
        ("gpt-5", "gpt-5.5"),
        ("gpt-5-search", "gpt-5.5"),
        ("gpt-5.5", "gpt-5.5"),
        ("gpt-5.5-search", "gpt-5.5"),
        ("gpt-5.4", "gpt-5.4"),
        ("gpt-5.4-search", "gpt-5.4"),
    ],
)
def test_gpt_5_aliases_resolve_to_configured_model_name(monkeypatch, alias_name: str, expected_model_name: str):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings(alias_name))

    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)
    monkeypatch.setattr(model_config, "ChatAnthropic", lambda **_kwargs: None)

    ModelSelector.get_llm(AgentRole.COACH_TRIAGE)

    assert captured["model"] == expected_model_name
    assert captured["base_url"] == "https://api.openai.com/v1"
    assert captured["reasoning"]["effort"] == "xhigh"


def test_claude_opus_4_8_max_configures_thinking(monkeypatch):
    config = Config(ai_mode=AIMode.STANDARD, anthropic_api_key="sk-ant-api03-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("claude-opus-4.8-max"))

    captured = {}

    def fake_chat_anthropic(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatAnthropic", fake_chat_anthropic)
    monkeypatch.setattr(model_config, "ChatOpenAI", lambda **_kwargs: None)

    ModelSelector.get_llm(AgentRole.COACH)

    assert captured["model"] == "claude-opus-4-8"
    assert captured["max_tokens"] == 32000
    assert captured["thinking"] == {"type": "adaptive"}
    assert captured["output_config"] == {"effort": "max"}
    assert "reasoning" not in captured
    assert "model_kwargs" not in captured


@pytest.mark.parametrize("role", [AgentRole.SEASON_PLANNER, AgentRole.WEEKLY_PLANNER])
def test_planner_roles_use_64k_output_tokens_for_claude(monkeypatch, role: AgentRole):
    config = Config(ai_mode=AIMode.STANDARD, anthropic_api_key="sk-ant-api03-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("claude-opus-4.8-max"))

    captured = {}

    def fake_chat_anthropic(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatAnthropic", fake_chat_anthropic)
    monkeypatch.setattr(model_config, "ChatOpenAI", lambda **_kwargs: None)

    ModelSelector.get_llm(role)

    assert captured["model"] == "claude-opus-4-8"
    assert captured["max_tokens"] == 64000
    assert captured["thinking"] == {"type": "adaptive"}
    assert captured["output_config"] == {"effort": "max"}


@pytest.mark.parametrize("role", [AgentRole.ANALYSIS_FORMATTER, AgentRole.PLAN_FORMATTER])
def test_claude_formatter_roles_disable_thinking(monkeypatch, role: AgentRole):
    config = Config(ai_mode=AIMode.STANDARD, anthropic_api_key="sk-ant-api03-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("claude-opus-4.8-max"))

    captured = {}

    def fake_chat_anthropic(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatAnthropic", fake_chat_anthropic)
    monkeypatch.setattr(model_config, "ChatOpenAI", lambda **_kwargs: None)

    ModelSelector.get_llm(role)

    assert captured["model"] == "claude-opus-4-8"
    assert captured["max_tokens"] == 64000
    assert "thinking" not in captured
    assert "output_config" not in captured
    assert "reasoning" not in captured
    assert "model_kwargs" not in captured


@pytest.mark.parametrize("role", [AgentRole.ANALYSIS_FORMATTER, AgentRole.PLAN_FORMATTER])
def test_gpt_formatter_roles_use_64k_output_tokens(monkeypatch, role: AgentRole):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-5.5"))

    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)
    monkeypatch.setattr(model_config, "ChatAnthropic", lambda **_kwargs: None)

    ModelSelector.get_llm(role)

    assert captured["model"] == "gpt-5.5"
    assert captured["reasoning"]["effort"] == "xhigh"
    assert captured["model_kwargs"]["max_output_tokens"] == 64000


def test_weekly_planner_openai_search_uses_64k_and_preserves_tools(monkeypatch):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-5.5-search"))

    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)
    monkeypatch.setattr(model_config, "ChatAnthropic", lambda **_kwargs: None)

    ModelSelector.get_llm(AgentRole.WEEKLY_PLANNER)

    assert captured["model_kwargs"]["max_output_tokens"] == 64000
    assert captured["model_kwargs"]["tools"] == [{"type": "web_search"}]


def test_search_models_pass_include_explicitly(monkeypatch):
    config = Config(ai_mode=AIMode.STANDARD, openai_api_key="sk-test")
    monkeypatch.setattr(model_config, "get_config", lambda: config)
    monkeypatch.setattr(model_config, "ai_settings", _StubSettings("gpt-5.5-search"))

    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(model_config, "ChatOpenAI", fake_chat_openai)
    monkeypatch.setattr(model_config, "ChatAnthropic", lambda **_kwargs: None)

    ModelSelector.get_llm(AgentRole.METRICS_EXPERT)

    assert captured["include"] == ["web_search_call.action.sources"]
    assert captured["model_kwargs"]["tools"] == [{"type": "web_search"}]
    assert "include" not in captured["model_kwargs"]
