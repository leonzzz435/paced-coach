import logging
import os
from dataclasses import dataclass
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from core.config import get_config
from services.ai.langgraph.config.langsmith_config import LangSmithConfig

from .ai_settings import AgentRole, ai_settings

logger = logging.getLogger(__name__)


@dataclass
class ModelConfiguration:
    name: str
    base_url: str


class ModelSelector:
    PROVIDER_PARAM_ALLOWLIST: dict[str, set[str]] = {
        "openai": {"model", "api_key", "base_url", "include", "use_responses_api", "reasoning", "model_kwargs"},
        "anthropic": {"model", "api_key", "max_tokens", "thinking", "output_config", "effort", "model_kwargs"},
    }
    THINKING_DISABLED_ROLES: set[AgentRole] = {
        AgentRole.ANALYSIS_FORMATTER,
        AgentRole.PLAN_FORMATTER,
    }
    XHIGH_REASONING_MODEL_ALIASES: set[str] = {
        "gpt-5.5-search",
        "gpt-5.4-search",
    }

    ROLE_DEFAULTS: dict[AgentRole, dict[str, Any]] = {
        AgentRole.SUMMARIZER: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.METRICS_EXPERT: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.PHYSIOLOGY_EXPERT: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.ACTIVITY_EXPERT: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.SYNTHESIS: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "high"}},
        },
        AgentRole.SEASON_PLANNER: {
            "output_token_limit": 64000,
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.WEEKLY_PLANNER: {
            "output_token_limit": 64000,
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.WEEKLY_RECAP: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.DAILY_UPDATE: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.ANALYSIS_FORMATTER: {
            "output_token_limit": 64000,
            "reasoning": {"effort": "xhigh"},
            "model_kwargs": {"text": {"verbosity": "low"}},
        },
        AgentRole.PLAN_FORMATTER: {
            "output_token_limit": 64000,
            "reasoning": {"effort": "xhigh"},
            "model_kwargs": {"text": {"verbosity": "low"}},
        },
        AgentRole.COACH: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.COACH_TRIAGE: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
    }

    @staticmethod
    def _detect_provider(base_url: str) -> str:
        if "anthropic" in base_url:
            return "anthropic"
        return "openai"

    CONFIGURATIONS: dict[str, ModelConfiguration] = {
        # OpenAI Models
        "gpt-4o": ModelConfiguration(
            name="gpt-4o",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-4.1": ModelConfiguration(
            name="gpt-4.1",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-4.5": ModelConfiguration(
            name="gpt-4.5-preview",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-4o-mini": ModelConfiguration(
            name="gpt-4o-mini",
            base_url="https://api.openai.com/v1",
        ),
        "o1": ModelConfiguration(
            name="o1-preview",
            base_url="https://api.openai.com/v1",
        ),
        "o1-mini": ModelConfiguration(
            name="o1-mini",
            base_url="https://api.openai.com/v1",
        ),
        "o3": ModelConfiguration(
            name="o3",
            base_url="https://api.openai.com/v1",
        ),
        "o3-mini": ModelConfiguration(
            name="o3-mini",
            base_url="https://api.openai.com/v1",
        ),
        "o4-mini": ModelConfiguration(
            name="o4-mini",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5": ModelConfiguration(
            name="gpt-5.5",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.5": ModelConfiguration(
            name="gpt-5.5",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.4": ModelConfiguration(
            name="gpt-5.4",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.2-pro": ModelConfiguration(
            name="gpt-5.2-pro",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5-mini": ModelConfiguration(
            name="gpt-5-mini",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5-search": ModelConfiguration(
            name="gpt-5.5",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.5-search": ModelConfiguration(
            name="gpt-5.5",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.4-search": ModelConfiguration(
            name="gpt-5.4",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.2-pro-search": ModelConfiguration(
            name="gpt-5.2-pro",
            base_url="https://api.openai.com/v1",
        ),
        # Anthropic Models
        "claude-4": ModelConfiguration(
            name="claude-sonnet-4-6",
            base_url="https://api.anthropic.com",
        ),
        "claude-4-thinking": ModelConfiguration(
            name="claude-sonnet-4-6",
            base_url="https://api.anthropic.com",
        ),
        "claude-opus": ModelConfiguration(
            name="claude-opus-4-8",
            base_url="https://api.anthropic.com",
        ),
        "claude-opus-thinking": ModelConfiguration(
            name="claude-opus-4-8",
            base_url="https://api.anthropic.com",
        ),
        "claude-opus-4.7-max": ModelConfiguration(
            name="claude-opus-4-8",
            base_url="https://api.anthropic.com",
        ),
        "claude-opus-4.8-max": ModelConfiguration(
            name="claude-opus-4-8",
            base_url="https://api.anthropic.com",
        ),
        "claude-haiku": ModelConfiguration(
            name="claude-haiku-4-5",
            base_url="https://api.anthropic.com",
        ),
    }

    MODEL_CONFIGS: dict[str, dict[str, Any]] = {
        "claude-opus-thinking": {
            "max_tokens": 32000,
            "thinking": {"type": "enabled", "budget_tokens": 16000},
            "log": "Using extended thinking mode for {role} (max_tokens: 32000, budget_tokens: 16000)",
        },
        "claude-4-thinking": {
            "max_tokens": 64000,
            "thinking": {"type": "enabled", "budget_tokens": 16000},
            "log": "Using extended thinking mode for {role} (max_tokens: 64000, budget_tokens: 16000)",
        },
        "claude-4": {
            "max_tokens": 64000,
            "log": "Using extended output tokens for {role} (max_tokens: 64000)",
        },
        "claude-opus": {
            "max_tokens": 32000,
            "log": "Using extended output tokens for {role} (max_tokens: 32000)",
        },
        "claude-opus-4.7-max": {
            "max_tokens": 32000,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "max"},
            "log": "Using Claude Opus 4.8 with adaptive max-effort thinking for {role} (max_tokens: 32000)",
        },
        "claude-opus-4.8-max": {
            "max_tokens": 32000,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "max"},
            "log": "Using Claude Opus 4.8 with adaptive max-effort thinking for {role} (max_tokens: 32000)",
        },
        "gpt-5": {
            "use_responses_api": True,
            "model_kwargs": {"max_output_tokens": 100000},
            "log": "Using GPT-5.5 with Responses API for {role}",
        },
        "gpt-5.5": {
            "use_responses_api": True,
            "model_kwargs": {"max_output_tokens": 100000},
            "log": "Using GPT-5.5 with Responses API for {role}",
        },
        "gpt-5.4": {
            "use_responses_api": True,
            "model_kwargs": {"max_output_tokens": 100000},
            "log": "Using GPT-5.4 with Responses API for {role}",
        },
        "gpt-5.2-pro": {
            "use_responses_api": True,
            "log": "Using GPT-5.2 Pro with Responses API for {role}",
        },
        "gpt-5-mini": {
            "use_responses_api": True,
            "log": "Using GPT-5-mini with Responses API for {role}",
        },
        "gpt-5-search": {
            "use_responses_api": True,
            "model_kwargs": {
                "tools": [{"type": "web_search"}],
            },
            "include": ["web_search_call.action.sources"],
            "log": "Using GPT-5.5 with web search + Responses API for {role}",
        },
        "gpt-5.5-search": {
            "use_responses_api": True,
            "model_kwargs": {
                "tools": [{"type": "web_search"}],
            },
            "include": ["web_search_call.action.sources"],
            "log": "Using GPT-5.5 with web search + Responses API for {role}",
        },
        "gpt-5.4-search": {
            "use_responses_api": True,
            "model_kwargs": {
                "tools": [{"type": "web_search"}],
            },
            "include": ["web_search_call.action.sources"],
            "log": "Using GPT-5.4 with web search + Responses API for {role}",
        },
        "gpt-5.2-pro-search": {
            "use_responses_api": True,
            "model_kwargs": {
                "tools": [{"type": "web_search"}],
            },
            "include": ["web_search_call.action.sources"],
            "log": "Using GPT-5.2 Pro with web search + Responses API for {role}",
        },
    }

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @classmethod
    def _filter_params_for_provider(cls, provider: str, llm_params: dict[str, Any]) -> dict[str, Any]:
        allowed = cls.PROVIDER_PARAM_ALLOWLIST.get(provider, set())
        filtered = {key: value for key, value in llm_params.items() if key in allowed}
        if provider == "openai" and "model_kwargs" in filtered:
            model_kwargs = filtered["model_kwargs"].copy()
            if "text" in model_kwargs:
                text_config = model_kwargs["text"].copy()
                if "verbosity" in text_config:
                    text_config.pop("verbosity")
                if text_config:
                    model_kwargs["text"] = text_config
                else:
                    model_kwargs.pop("text")
            if model_kwargs:
                filtered["model_kwargs"] = model_kwargs
            else:
                filtered.pop("model_kwargs")
        if provider == "anthropic" and "model_kwargs" in filtered:
            model_kwargs = filtered["model_kwargs"].copy()
            model_kwargs.pop("text", None)
            if model_kwargs:
                filtered["model_kwargs"] = model_kwargs
            else:
                filtered.pop("model_kwargs")
        return filtered

    @classmethod
    def _apply_model_config(cls, model_name: str, role: AgentRole, provider: str, llm_params: dict[str, Any]):
        if model_name not in cls.MODEL_CONFIGS:
            config_data: dict[str, Any] = {}
        else:
            config_data = cls.MODEL_CONFIGS[model_name].copy()

        role_overrides = cls.ROLE_DEFAULTS.get(role, {})
        merged = cls._deep_merge(config_data, role_overrides)
        if provider == "openai" or model_name in cls.XHIGH_REASONING_MODEL_ALIASES:
            merged["reasoning"] = {"effort": "xhigh"}

        output_token_limit = merged.pop("output_token_limit", None)
        if output_token_limit is not None:
            if provider == "anthropic":
                merged["max_tokens"] = output_token_limit
            elif provider == "openai":
                model_kwargs = merged.setdefault("model_kwargs", {})
                model_kwargs["max_output_tokens"] = output_token_limit

        if role in cls.THINKING_DISABLED_ROLES:
            removed_thinking = "thinking" in merged or "output_config" in merged or "effort" in merged
            merged.pop("thinking", None)
            merged.pop("output_config", None)
            merged.pop("effort", None)
            if removed_thinking:
                merged["log"] = (
                    "Using {model_name} without Anthropic thinking for {role} to allow forced formatter tool calls"
                )

        log_msg = merged.pop("log", None)
        llm_params.update(merged)
        if log_msg:
            logger.info(str(log_msg).format(role=role.value, model_name=model_name))

    @classmethod
    def get_llm(cls, role: AgentRole):
        model_name = ai_settings.get_model_for_role(role)
        selected_config = cls.CONFIGURATIONS.get(model_name)
        if not selected_config:
            raise RuntimeError(f"Unknown model '{model_name}' in configuration")
        config = get_config()

        # Ensure LangSmith tracing is enabled for API usage too (not only LangGraph workflows).
        # We keep this opt-in via presence of LANGSMITH_API_KEY.
        LangSmithConfig.setup_langsmith(project_name=os.getenv("LANGSMITH_PROJECT", "paced_coach"))

        base_url = selected_config.base_url
        final_model_name = selected_config.name
        provider = cls._detect_provider(base_url)

        key_map = {
            "anthropic": config.anthropic_api_key,
            "openai": config.openai_api_key,
        }

        api_key = key_map.get(provider)
        if not api_key:
            raise RuntimeError(f"{provider.title()} API key is required")

        logger.info("Configuring LLM for role %s with model %s", role.value, final_model_name)

        llm_params: dict[str, Any] = {"model": final_model_name, "api_key": api_key}

        cls._apply_model_config(model_name, role, provider, llm_params)

        llm_params = cls._filter_params_for_provider(provider, llm_params)
        if provider == "anthropic":
            return ChatAnthropic(**llm_params)

        llm_params["base_url"] = base_url
        return ChatOpenAI(**llm_params, max_retries=3)
