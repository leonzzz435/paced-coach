from api.services import local_readiness
from core.config import AIMode, Config


def test_openai_modes_require_openai_key(monkeypatch):
    monkeypatch.setattr(local_readiness, "get_config", lambda: Config(ai_mode=AIMode.COST_EFFECTIVE))

    assert local_readiness.format_llm_provider_key_names() == "OPENAI_API_KEY"
    assert local_readiness.has_llm_provider_key({"OPENAI_API_KEY": "sk-test"})
    assert not local_readiness.has_llm_provider_key({"ANTHROPIC_API_KEY": "sk-ant-api03-test"})


def test_anthropic_mode_requires_anthropic_key(monkeypatch):
    monkeypatch.setattr(local_readiness, "get_config", lambda: Config(ai_mode=AIMode.ANTHROPIC))

    assert local_readiness.format_llm_provider_key_names() == "ANTHROPIC_API_KEY"
    assert local_readiness.has_llm_provider_key({"ANTHROPIC_API_KEY": "sk-ant-api03-test"})
    assert not local_readiness.has_llm_provider_key({"OPENAI_API_KEY": "sk-test"})
